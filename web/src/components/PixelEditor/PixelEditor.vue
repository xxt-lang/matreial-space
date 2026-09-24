<script setup>
/**
 * 像素画编辑器（独立组件，不掺任何业务）
 *
 * 能力：画笔 / 橡皮 / 取色 / 油漆桶 + 调色板 + 网格 + 缩放 + 撤销重做 + 导出 PNG
 *
 * 用法：
 *   <PixelEditor :image="data.image" :size="data.size" @apply="onApply" />
 * - image：可选。传入时作为初始内容加载（dataURL 或同源 URL），加载后成为撤销栈的起点
 * - size：像素画边长。编辑器内只读 —— 尺寸的唯一来源是节点工具栏，避免两处都能改
 * - apply：点「应用到节点」时抛出 1:1 的 PNG dataURL
 *
 * 状态全在这里：像素缓冲、撤销栈、当前工具与颜色。
 * 画布组件（PixelCanvas）只负责渲染和上报像素坐标，不认识工具语义。
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

import AppIcon from '../AppIcon/AppIcon.vue'
import PixelCanvas from './PixelCanvas.vue'
import {
  TRANSPARENT,
  cloneBuffer,
  createBuffer,
  fill,
  floodFill,
  getPixel,
  hexToRgba,
  isEqualBuffer,
  line,
  rgbaToHex,
  setPixel,
} from './pixel.js'

const props = defineProps({
  /** 初始内容（dataURL 或同源 URL），为空表示从空白画布开始 */
  image: { type: String, default: '' },
  /** 像素画边长 */
  size: { type: Number, default: 64 },
})

const emit = defineEmits(['apply'])

/* ---------------- 工具与颜色 ---------------- */

const TOOLS = [
  { value: 'pencil', label: '画笔', icon: 'pencil' },
  { value: 'eraser', label: '橡皮', icon: 'eraser' },
  { value: 'picker', label: '取色', icon: 'picker' },
  { value: 'bucket', label: '油漆桶', icon: 'bucket' },
]

/** 预置调色板：PICO-8 十六色，像素画常见的起步配色 */
const PALETTE = [
  '#000000', '#1d2b53', '#7e2553', '#008751',
  '#ab5236', '#5f574f', '#c2c3c7', '#fff1e8',
  '#ff004d', '#ffa300', '#ffec27', '#00e436',
  '#29adff', '#83769c', '#ff77a8', '#ffccaa',
]

const tool = ref('pencil')
const color = ref('#fff1e8')
const gridVisible = ref(true)

/** 当前颜色的 RGBA；输入框里出现非法值时退回白色，保证画笔始终能用 */
const colorRgba = computed(() => hexToRgba(color.value) ?? [255, 255, 255, 255])

/* ---------------- 像素缓冲与撤销栈 ---------------- */

const buffer = ref(createBuffer(props.size))
/** 缓冲版本号：就地修改后 +1，通知画布重绘 */
const version = ref(0)

/**
 * 撤销栈：存整块缓冲的快照（64×64 只有 16KB，简单可靠，不用记差量）
 * 记的是「状态」而不是「操作」，所以撤销 / 重做就是指针前后移动
 */
const HISTORY_LIMIT = 40
const history = shallowRef([cloneBuffer(buffer.value)])
const historyIndex = ref(0)

const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < history.value.length - 1)

/** 重置撤销栈：把当前缓冲作为新的起点（首次加载图片后调用） */
function resetHistory() {
  history.value = [cloneBuffer(buffer.value)]
  historyIndex.value = 0
}

/** 记一次撤销点；内容没变化就不记，避免撤销栈里塞进无效步骤 */
function commit() {
  if (isEqualBuffer(buffer.value, history.value[historyIndex.value])) return

  const next = history.value.slice(0, historyIndex.value + 1)
  next.push(cloneBuffer(buffer.value))

  // 超上限就丢掉最早的（指针同步前移）
  const overflow = Math.max(0, next.length - HISTORY_LIMIT)
  history.value = overflow ? next.slice(overflow) : next
  historyIndex.value = history.value.length - 1
  version.value += 1
}

/** 把某个快照恢复成当前缓冲（拷贝一份：栈里的快照必须保持只读） */
function restore(state) {
  buffer.value = cloneBuffer(state)
  version.value += 1
}

function undo() {
  if (!canUndo.value) return
  historyIndex.value -= 1
  restore(history.value[historyIndex.value])
}

function redo() {
  if (!canRedo.value) return
  historyIndex.value += 1
  restore(history.value[historyIndex.value])
}

function clearAll() {
  fill(buffer.value, props.size, TRANSPARENT)
  commit()
}

/* ---------------- 工具行为 ---------------- */

/** 上一次落笔的像素点：拖动时靠它把两个事件之间的空隙连成直线 */
let lastPoint = null

/** 画一个点（画笔 / 橡皮） */
function paintAt(x, y) {
  if (tool.value === 'pencil') setPixel(buffer.value, props.size, x, y, colorRgba.value)
  else if (tool.value === 'eraser') setPixel(buffer.value, props.size, x, y, TRANSPARENT)
  else return

  version.value += 1
}

function onStrokeStart(point) {
  // 油漆桶：一次点击就完成，不参与拖动
  if (tool.value === 'bucket') {
    floodFill(buffer.value, props.size, point.x, point.y, colorRgba.value)
    commit()
    return
  }

  // 取色：只改当前颜色，不改像素
  if (tool.value === 'picker') {
    const picked = getPixel(buffer.value, props.size, point.x, point.y)
    // 透明像素不覆盖当前颜色，否则一取色就没法画了
    if (picked && picked[3] > 0) color.value = rgbaToHex(picked)
    return
  }

  lastPoint = { ...point }
  paintAt(point.x, point.y)
}

function onStrokeMove(point) {
  if (tool.value !== 'pencil' && tool.value !== 'eraser') return

  if (!lastPoint) {
    lastPoint = { ...point }
    paintAt(point.x, point.y)
    return
  }

  // 补上两次 move 之间的像素，快速拖动才不会画成虚线
  line(lastPoint.x, lastPoint.y, point.x, point.y, paintAt)
  lastPoint = { ...point }
}

function onStrokeEnd() {
  // 一次「按下 → 拖动 → 抬起」记一个撤销点
  if (tool.value === 'pencil' || tool.value === 'eraser') commit()
  lastPoint = null
}

/* ---------------- 缩放 ---------------- */

const ZOOM_STEPS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32]

const stageRef = ref(null)
const stageSize = ref({ width: 0, height: 0 })
/** 手动缩放倍数；0 表示跟随「适应窗口」 */
const zoomOverride = ref(0)

/** 适应窗口：按可用空间算最大整数倍 */
const fitZoom = computed(() => {
  const { width, height } = stageSize.value
  if (!width || !height) return 8
  return Math.max(1, Math.floor(Math.min(width, height) / props.size))
})

const zoom = computed(() => zoomOverride.value || fitZoom.value)
const zoomText = computed(() => `${zoom.value * 100}%`)

function zoomIn() {
  const current = zoom.value
  zoomOverride.value = ZOOM_STEPS.find((step) => step > current) ?? current
}

function zoomOut() {
  const current = zoom.value
  const smaller = [...ZOOM_STEPS].reverse().find((step) => step < current)
  zoomOverride.value = smaller ?? current
}

function fitToStage() {
  zoomOverride.value = 0
}

let stageObserver = null

/* ---------------- 初始内容 ---------------- */

const hoverPoint = ref(null)
const loadError = ref('')

function loadImageElement(src) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('图片加载失败，无法作为初始内容'))
    image.src = src
  })
}

/** 把 props.image 画进 size×size 的离屏画布后取像素，作为编辑起点 */
async function loadImage() {
  loadError.value = ''
  if (!props.image) return

  try {
    const image = await loadImageElement(props.image)
    const canvas = document.createElement('canvas')
    canvas.width = props.size
    canvas.height = props.size

    const context = canvas.getContext('2d')
    if (!context) return

    // 缩小时也用最近邻采样：导入像素画要的是硬边，不是被平滑糊掉
    context.imageSmoothingEnabled = false
    context.drawImage(image, 0, 0, props.size, props.size)

    // 跨域图片会让画布被污染，这里读像素会抛错，交给 catch 提示
    const data = context.getImageData(0, 0, props.size, props.size)
    buffer.value = new Uint8ClampedArray(data.data)
    version.value += 1
    resetHistory()
  } catch (error) {
    loadError.value = error?.message || '初始图片加载失败'
  }
}

/* ---------------- 导出 / 应用 ---------------- */

/** 导出 1:1 的 PNG dataURL（节点图片区用最近邻放大展示，不会糊） */
function toPngDataUrl() {
  const canvas = document.createElement('canvas')
  canvas.width = props.size
  canvas.height = props.size

  const context = canvas.getContext('2d')
  // 传副本而不是原缓冲：ImageData 只做浅引用，避免以后被就地改到
  context.putImageData(new ImageData(cloneBuffer(buffer.value), props.size, props.size), 0, 0)

  return canvas.toDataURL('image/png')
}

function apply() {
  emit('apply', toPngDataUrl())
}

function downloadPng() {
  const link = document.createElement('a')
  link.href = toPngDataUrl()
  link.download = `pixel-${props.size}x${props.size}.png`
  link.click()
}

/* ---------------- 状态栏 / 生命周期 ---------------- */

const statusText = computed(() => {
  const coords = hoverPoint.value ? `坐标 (${hoverPoint.value.x}, ${hoverPoint.value.y})` : '坐标 —'
  return `${props.size}×${props.size} · ${coords} · 缩放 ${zoomText.value}`
})

onMounted(() => {
  loadImage()

  if (stageRef.value) {
    stageObserver = new ResizeObserver(([entry]) => {
      stageSize.value = { width: entry.contentRect.width, height: entry.contentRect.height }
    })
    stageObserver.observe(stageRef.value)
  }
})

onBeforeUnmount(() => {
  stageObserver?.disconnect()
})

// 弹窗每次打开都是新实例，正常不会变；留个兜底，避免外部换了图不刷新
watch(() => props.image, loadImage)
</script>

<template>
  <div class="pixel-editor">
    <!-- 工具条 -->
    <div class="pixel-editor__bar">
      <div class="pixel-editor__group">
        <button
          v-for="item in TOOLS"
          :key="item.value"
          class="pixel-editor__tool"
          :class="{ 'is-active': tool === item.value }"
          type="button"
          :title="item.label"
          :aria-label="item.label"
          @click="tool = item.value"
        >
          <AppIcon :type="item.icon" :size="16" />
        </button>
      </div>

      <span class="pixel-editor__divider" />

      <div class="pixel-editor__group">
        <button
          class="pixel-editor__tool"
          :class="{ 'is-active': gridVisible }"
          type="button"
          title="显示 / 隐藏网格"
          aria-label="显示 / 隐藏网格"
          @click="gridVisible = !gridVisible"
        >
          <AppIcon type="grid" :size="16" />
        </button>

        <button
          class="pixel-editor__tool"
          type="button"
          title="撤销"
          aria-label="撤销"
          :disabled="!canUndo"
          @click="undo"
        >
          <AppIcon type="undo" :size="16" />
        </button>

        <button
          class="pixel-editor__tool"
          type="button"
          title="重做"
          aria-label="重做"
          :disabled="!canRedo"
          @click="redo"
        >
          <AppIcon type="redo" :size="16" />
        </button>

        <button
          class="pixel-editor__tool"
          type="button"
          title="清空画布"
          aria-label="清空画布"
          @click="clearAll"
        >
          <AppIcon type="trash" :size="16" />
        </button>
      </div>

      <span class="pixel-editor__divider" />

      <div class="pixel-editor__group">
        <button class="pixel-editor__zoom" type="button" title="缩小" @click="zoomOut">−</button>
        <span class="pixel-editor__zoom-value">{{ zoomText }}</span>
        <button class="pixel-editor__zoom" type="button" title="放大" @click="zoomIn">+</button>
        <button class="pixel-editor__zoom" type="button" title="适应窗口" @click="fitToStage">
          适应
        </button>
      </div>
    </div>

    <p v-if="loadError" class="pixel-editor__error">{{ loadError }}</p>

    <!-- 画布 + 调色板 -->
    <div class="pixel-editor__main">
      <div ref="stageRef" class="pixel-editor__stage">
        <PixelCanvas
          :buffer="buffer"
          :size="size"
          :zoom="zoom"
          :grid="gridVisible"
          :version="version"
          @stroke-start="onStrokeStart"
          @stroke-move="onStrokeMove"
          @stroke-end="onStrokeEnd"
          @hover="hoverPoint = $event"
          @leave="hoverPoint = null"
        />
      </div>

      <aside class="pixel-editor__side">
        <div class="pixel-editor__current" title="当前颜色（点右侧方块可自选）">
          <span class="pixel-editor__swatch" :style="{ background: color }" />
          <input v-model="color" class="pixel-editor__color-input" type="color" aria-label="自选颜色" />
        </div>

        <div class="pixel-editor__palette">
          <button
            v-for="item in PALETTE"
            :key="item"
            class="pixel-editor__chip"
            :class="{ 'is-active': item.toLowerCase() === color.toLowerCase() }"
            type="button"
            :title="item"
            :aria-label="`颜色 ${item}`"
            :style="{ background: item }"
            @click="color = item"
          />
        </div>
      </aside>
    </div>

    <!-- 状态 + 操作 -->
    <div class="pixel-editor__foot">
      <p class="pixel-editor__status">{{ statusText }}</p>

      <div class="pixel-editor__actions">
        <button class="pixel-editor__btn" type="button" @click="downloadPng">下载 PNG</button>
        <button class="pixel-editor__btn pixel-editor__btn--primary" type="button" @click="apply">
          应用到节点
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/*
  配色沿用画布区的暗色 token，统一带 fallback（这些 token 全局未定义）；
  正文色用 --fg 而不是 --text，后者在 style.css 里是浅色灰，落在暗底上看不清。
*/
.pixel-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  min-height: 0;
  font-size: 12px;
  color: var(--fg, #e9edf5);
}

/* ---------------- 工具条 ---------------- */

.pixel-editor__bar {
  display: flex;
  flex: none;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.pixel-editor__group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pixel-editor__divider {
  width: 1px;
  height: 18px;
  background: var(--border2, #343c4c);
}

.pixel-editor__tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  color: var(--fg, #e9edf5);
  background: var(--surface-2, #1b2130);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    border-color 0.15s ease,
    opacity 0.15s ease;
}

.pixel-editor__tool:hover:not(:disabled) {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.pixel-editor__tool:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

/* 当前工具 / 开关打开：accent 实底 + 深色图标 */
.pixel-editor__tool.is-active {
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.pixel-editor__zoom {
  min-width: 28px;
  padding: 5px 8px;
  font: inherit;
  font-size: 12px;
  color: var(--fg, #e9edf5);
  background: var(--surface-2, #1b2130);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}

.pixel-editor__zoom:hover {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.pixel-editor__zoom-value {
  min-width: 46px;
  font-family: var(--mono, ui-monospace, Consolas, monospace);
  font-size: 11px;
  color: var(--muted, #767f92);
  text-align: center;
}

.pixel-editor__error {
  margin: 0;
  font-size: 12px;
  color: var(--danger, #e06c9f);
}

/* ---------------- 画布区 + 侧栏 ---------------- */

.pixel-editor__main {
  display: flex;
  flex: 1;
  gap: 12px;
  min-height: 0;
}

.pixel-editor__stage {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 0;
  padding: 12px;
  overflow: auto;
  background: #0b0e13;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r, 10px);
}

.pixel-editor__side {
  display: flex;
  flex: none;
  flex-direction: column;
  gap: 10px;
  width: 116px;
}

.pixel-editor__current {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pixel-editor__swatch {
  flex: 1;
  height: 26px;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
}

/* 原生取色器：只留一个方块，样式由浏览器决定 */
.pixel-editor__color-input {
  width: 30px;
  height: 26px;
  padding: 0;
  background: none;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
}

.pixel-editor__palette {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.pixel-editor__chip {
  width: 100%;
  aspect-ratio: 1;
  padding: 0;
  border: 1px solid rgba(0, 0, 0, 0.45);
  border-radius: 4px;
  cursor: pointer;
}

.pixel-editor__chip.is-active {
  box-shadow: 0 0 0 2px var(--accent, #f0a63d);
}

/* ---------------- 状态栏 + 操作 ---------------- */

.pixel-editor__foot {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pixel-editor__status {
  margin: 0;
  font-family: var(--mono, ui-monospace, Consolas, monospace);
  font-size: 11px;
  color: var(--muted, #767f92);
}

.pixel-editor__actions {
  display: flex;
  gap: 8px;
}

.pixel-editor__btn {
  padding: 6px 14px;
  font: inherit;
  font-size: 12px;
  color: var(--fg, #e9edf5);
  background: var(--surface-2, #1b2130);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    border-color 0.15s ease,
    opacity 0.15s ease;
}

.pixel-editor__btn:hover {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.pixel-editor__btn--primary {
  font-weight: 600;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.pixel-editor__btn--primary:hover {
  color: var(--accent-ink, #201404);
  opacity: 0.88;
}
</style>
