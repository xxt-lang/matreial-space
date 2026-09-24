<script setup>
/**
 * 像素画画布（PixelEditor 的私有子组件）
 *
 * 只干两件事：把像素缓冲画出来、把指针位置换算成像素坐标上报。
 * 它不认识「画笔 / 油漆桶」这些概念，工具语义全部由父组件决定。
 *
 * 渲染分两层，都是为了「像素硬边」和「细网格」：
 * - 底图 canvas：画布尺寸就是 size×size（1 个数据点 = 1 个画布像素），
 *   再用 CSS 放大 + image-rendering: pixelated 做最近邻放大，不会被插值糊掉
 * - 网格 canvas：画布尺寸是「显示尺寸」，1px 细线，放大后依然是细线
 *   （画在底图上会被一起放大成粗条）
 *
 * 契约：buffer 由父组件持有并就地修改，改完把 version +1 触发重绘
 * （TypedArray 就地改不会触发 Vue 响应，所以用 version 显式通知）
 */
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  /** 像素缓冲：Uint8ClampedArray，长度 size×size×4 */
  buffer: { type: Object, default: null },
  /** 像素画边长 */
  size: { type: Number, required: true },
  /** 每个像素放大多少倍 */
  zoom: { type: Number, required: true },
  /** 是否显示网格 */
  grid: { type: Boolean, default: true },
  /** 缓冲版本号：就地修改后由父组件 +1，用来触发重绘 */
  version: { type: Number, default: 0 },
})

const emit = defineEmits(['stroke-start', 'stroke-move', 'stroke-end', 'hover', 'leave'])

const baseRef = ref(null)
const gridRef = ref(null)

/** 显示尺寸（px）= 像素数 × 放大倍数 */
const displaySize = computed(() => props.size * props.zoom)

/** 透明棋盘格：2 像素一格，跟着缩放一起变 */
const checkerSize = computed(() => props.zoom * 2)

/** 底图：缓冲原样贴上去（1 个数据点 = 1 个画布像素） */
function renderBase() {
  const canvas = baseRef.value
  if (!canvas || !props.buffer) return
  // 缓冲长度和边长对不上时不画：ImageData 构造会直接抛错
  if (props.buffer.length !== props.size * props.size * 4) return

  canvas.width = props.size
  canvas.height = props.size

  const context = canvas.getContext('2d')
  if (!context) return
  context.clearRect(0, 0, props.size, props.size)
  context.putImageData(new ImageData(props.buffer, props.size, props.size), 0, 0)
}

/** 网格：按显示尺寸画，线宽固定 1px */
function renderGrid() {
  const canvas = gridRef.value
  if (!canvas) return

  canvas.width = displaySize.value
  canvas.height = displaySize.value

  const context = canvas.getContext('2d')
  if (!context) return
  context.clearRect(0, 0, canvas.width, canvas.height)
  if (!props.grid) return

  context.strokeStyle = 'rgba(255, 255, 255, 0.16)'
  context.lineWidth = 1

  for (let index = 0; index <= props.size; index += 1) {
    // +0.5：让 1px 的线落在像素中心，不然会被摊成两条半透明灰线
    const offset = index * props.zoom + 0.5
    context.beginPath()
    context.moveTo(offset, 0)
    context.lineTo(offset, canvas.height)
    context.stroke()

    context.beginPath()
    context.moveTo(0, offset)
    context.lineTo(canvas.width, offset)
    context.stroke()
  }
}

/* ---------------- 指针 → 像素坐标 ---------------- */

/** 用元素的实际显示尺寸换算，缩放多少都准；落在画布外返回 null */
function toPixel(event) {
  const canvas = baseRef.value
  if (!canvas) return null

  const rect = canvas.getBoundingClientRect()
  if (!rect.width || !rect.height) return null

  const x = Math.floor(((event.clientX - rect.left) / rect.width) * props.size)
  const y = Math.floor(((event.clientY - rect.top) / rect.height) * props.size)
  if (x < 0 || y < 0 || x >= props.size || y >= props.size) return null

  return { x, y }
}

/** 是否正处在一次「按下 → 拖动 → 抬起」中 */
const stroking = ref(false)

function onPointerDown(event) {
  const point = toPixel(event)
  if (!point) return

  event.preventDefault()
  stroking.value = true
  // 捕获指针：拖到画布外面也能继续收到 move / up，松手自动释放
  baseRef.value?.setPointerCapture?.(event.pointerId)
  emit('stroke-start', point)
}

function onPointerMove(event) {
  const point = toPixel(event)
  if (!point) {
    emit('leave')
    return
  }

  emit('hover', point)
  if (stroking.value) emit('stroke-move', point)
}

function onPointerUp(event) {
  if (!stroking.value) return
  stroking.value = false
  baseRef.value?.releasePointerCapture?.(event.pointerId)
  emit('stroke-end')
}

function onPointerLeave() {
  // 拖动中不移除坐标提示，避免笔迹经过边缘时状态栏闪烁
  if (!stroking.value) emit('leave')
}

onMounted(() => {
  renderBase()
  renderGrid()
})

watch([() => props.buffer, () => props.version, () => props.size], renderBase)
watch([() => props.size, () => props.zoom, () => props.grid], renderGrid)
</script>

<template>
  <div
    class="pixel-canvas"
    :style="{
      width: `${displaySize}px`,
      height: `${displaySize}px`,
      '--pixel-checker': `${checkerSize}px`,
    }"
  >
    <canvas
      ref="baseRef"
      class="pixel-canvas__base"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @pointerleave="onPointerLeave"
      @contextmenu.prevent
    />

    <!-- 网格叠在底图之上，只做展示，不吃指针事件 -->
    <canvas ref="gridRef" class="pixel-canvas__grid" aria-hidden="true" />
  </div>
</template>

<style scoped>
.pixel-canvas {
  position: relative;
  flex: none;
  /* 透明像素用棋盘格表示，格子大小跟着缩放走 */
  --pixel-checker: 16px;
  background-color: #171b22;
  background-image:
    linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.07) 25%,
      transparent 25%,
      transparent 75%,
      rgba(255, 255, 255, 0.07) 75%
    ),
    linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.07) 25%,
      transparent 25%,
      transparent 75%,
      rgba(255, 255, 255, 0.07) 75%
    );
  background-size: var(--pixel-checker) var(--pixel-checker);
  background-position:
    0 0,
    calc(var(--pixel-checker) / 2) calc(var(--pixel-checker) / 2);
  box-shadow: 0 0 0 1px var(--border2, #343c4c);
}

.pixel-canvas__base,
.pixel-canvas__grid {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

/* 最近邻放大：像素画的硬边全靠它，否则会被浏览器插值成模糊色块 */
.pixel-canvas__base {
  image-rendering: pixelated;
  cursor: crosshair;
  /* 触摸 / 手写笔拖动时禁掉浏览器手势，否则会被当成页面滚动 */
  touch-action: none;
  user-select: none;
}

.pixel-canvas__grid {
  pointer-events: none;
}
</style>
