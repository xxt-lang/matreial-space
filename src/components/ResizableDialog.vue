<script setup>
/**
 * 通用弹窗（全局组件，交互参考 Element Plus 的 Dialog）
 *
 * 对齐 Element Dialog 的交互：
 * - `v-model` 控制显隐；打开 / 关闭依次触发 open → opened / close → closed
 * - 遮罩层可开关，支持点击遮罩关闭（仅当按下与抬起都在遮罩上）、Esc 关闭、右上角关闭按钮
 * - 打开时锁定页面滚动（并补偿滚动条宽度，避免背景抖动），关闭后恢复
 * - 打开时把焦点移入弹窗，关闭后把焦点还给打开前的元素
 * - 插槽：header（缺省显示 title）、default（内容区，超高内部滚动）、footer（操作区）
 * - 默认 Teleport 到 body，避免被父级 transform / overflow 裁切
 *
 * 相对 Element 额外提供「拖拽移动 + 拖拽调整大小」：
 * - 拖拽标题栏移动弹窗（标题栏内的按钮等交互元素不参与拖拽），位置会限制在视口内
 * - 右边缘 / 下边缘 / 右下角三个把手调整大小，受 min / max 尺寸约束
 * - 打开时按当前尺寸算好 left / top，所以拉伸只会改变右 / 下边缘，缩放过程跟手
 *
 * 画布兼容：根节点带 `nokey`，vue-flow 画布的按键快捷键会忽略弹窗内的按键
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** 标题（未使用 header 插槽时显示） */
  title: { type: String, default: '' },
  /** 初始尺寸：数字按 px 处理，字符串原样使用 */
  width: { type: [Number, String], default: 560 },
  height: { type: [Number, String], default: 400 },
  /** 调整大小的下限 */
  minWidth: { type: Number, default: 320 },
  minHeight: { type: Number, default: 180 },
  /** 调整大小的上限，0 表示不限制 */
  maxWidth: { type: Number, default: 0 },
  maxHeight: { type: Number, default: 0 },
  /** 是否可调整大小 */
  resizable: { type: Boolean, default: true },
  /** 是否可拖拽标题栏移动弹窗 */
  draggable: { type: Boolean, default: true },
  /** 是否显示遮罩 */
  modal: { type: Boolean, default: true },
  /** 是否允许点击遮罩关闭 */
  closeOnClickModal: { type: Boolean, default: true },
  /** 是否允许按 Esc 关闭 */
  closeOnPressEscape: { type: Boolean, default: true },
  /** 是否显示右上角关闭按钮 */
  showClose: { type: Boolean, default: true },
  /** 是否挂载到 body */
  appendToBody: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'open', 'opened', 'close', 'closed'])

const dialogRef = ref(null)

/** 传给 defineProps 的尺寸可能是数字或字符串，这里统一换算成 px */
function toPx(value, fallback) {
  if (typeof value === 'number') return value
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

/* ---------------- 尺寸与位置 ---------------- */

/** 当前尺寸：初始值来自 props，之后由拖拽把手调整 */
const size = ref({ width: 0, height: 0 })
/** 当前定位：打开时按视口居中算一次，之后保持不变 */
const position = ref({ left: 0, top: 0 })

/** 打开时按当前尺寸与视口计算位置（居中偏上，与 Element 的 15vh 观感一致） */
function initBox() {
  const width = toPx(props.width, 560)
  const height = toPx(props.height, 400)
  size.value = { width, height }
  position.value = clampPosition({
    left: (window.innerWidth - width) / 2,
    top: (window.innerHeight - height) * 0.15,
  })
}

watch(
  () => [props.width, props.height],
  () => {
    if (!props.modelValue) return
    initBox()
  },
)

const dialogStyle = computed(() => ({
  width: `${size.value.width}px`,
  height: `${size.value.height}px`,
  left: `${position.value.left}px`,
  top: `${position.value.top}px`,
}))

/* ---------------- 显隐 ---------------- */

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

/** 关闭：统一走 v-model，close / closed 由 watch 发出，避免重复触发 */
function close() {
  visible.value = false
}

/* ---------------- 滚动锁定 / 焦点 ---------------- */

let restoreScroll = null
let restoreFocusEl = null

function lockScroll() {
  const body = document.body
  const barWidth = window.innerWidth - document.documentElement.clientWidth
  const prevOverflow = body.style.overflow
  const prevPadding = body.style.paddingRight
  body.style.overflow = 'hidden'
  if (barWidth > 0) {
    const padding = Number.parseFloat(getComputedStyle(body).paddingRight) || 0
    body.style.paddingRight = `${padding + barWidth}px`
  }
  restoreScroll = () => {
    body.style.overflow = prevOverflow
    body.style.paddingRight = prevPadding
  }
}

function unlockScroll() {
  restoreScroll?.()
  restoreScroll = null
}

function restoreFocus() {
  if (restoreFocusEl instanceof HTMLElement) restoreFocusEl.focus()
  restoreFocusEl = null
}

/* ---------------- Esc 关闭 ---------------- */

function onDocumentKeydown(event) {
  if (event.key !== 'Escape' || !props.closeOnPressEscape) return
  // 阻止画布等下层监听同时响应
  event.stopPropagation()
  close()
}

function bindKeydown() {
  document.addEventListener('keydown', onDocumentKeydown, true)
}

function unbindKeydown() {
  document.removeEventListener('keydown', onDocumentKeydown, true)
}

async function openDialog() {
  restoreFocusEl = document.activeElement
  emit('open')
  initBox()
  if (props.modal) lockScroll()
  bindKeydown()
  await nextTick()
  dialogRef.value?.focus()
  emit('opened')
}

function closeDialog() {
  emit('close')
  unlockScroll()
  unbindKeydown()
  restoreFocus()
  emit('closed')
}

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      openDialog()
      return
    }
    closeDialog()
  },
)

// 父级可能在挂载时就是打开状态（watch 不会触发），这里补一次
onMounted(() => {
  if (props.modelValue) openDialog()
})

onBeforeUnmount(() => {
  unlockScroll()
  unbindKeydown()
  stopResize?.()
  stopDrag?.()
})

/* ---------------- 拖拽移动 ---------------- */

let stopDrag = null

/**
 * 位置约束：整个弹窗留在视口内（留 8px 边距），避免拖丢或把缩放把手推出屏幕
 * 弹窗比视口还大时以 0 为下限，不做反向偏移
 */
function clampPosition(next) {
  const maxLeft = Math.max(window.innerWidth - size.value.width - 8, 0)
  const maxTop = Math.max(window.innerHeight - size.value.height - 8, 0)
  return {
    left: Math.min(Math.max(next.left, 0), maxLeft),
    top: Math.min(Math.max(next.top, 0), maxTop),
  }
}

/** 标题栏按下：开始拖拽移动弹窗 */
function startDrag(event) {
  if (!props.draggable) return
  // 标题栏里的交互元素（关闭按钮、插槽里的按钮等）不参与拖拽
  if (event.target?.closest?.('button, a, input, select, textarea, [contenteditable="true"]')) return
  event.preventDefault()

  const startX = event.clientX
  const startY = event.clientY
  const startLeft = position.value.left
  const startTop = position.value.top
  const prevUserSelect = document.body.style.userSelect
  // 拖拽期间禁止选中文本
  document.body.style.userSelect = 'none'

  function onPointerMove(moveEvent) {
    position.value = clampPosition({
      left: startLeft + (moveEvent.clientX - startX),
      top: startTop + (moveEvent.clientY - startY),
    })
  }

  function cleanup() {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', cleanup)
    window.removeEventListener('pointercancel', cleanup)
    document.body.style.userSelect = prevUserSelect
    stopDrag = null
  }

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', cleanup)
  window.addEventListener('pointercancel', cleanup)
  stopDrag = cleanup
}

/* ---------------- 拖拽调整大小 ---------------- */

let stopResize = null

function clampSize(value, min, max) {
  const lower = Math.max(min, 0)
  const upper = max > 0 ? Math.max(max, lower) : Number.POSITIVE_INFINITY
  return Math.min(Math.max(value, lower), upper)
}

/**
 * 开始调整大小
 * @param {PointerEvent} event 按下事件
 * @param {'e' | 's' | 'se'} direction 拉伸方向：e 右边缘、s 下边缘、se 右下角
 */
function startResize(event, direction) {
  if (!props.resizable) return
  event.preventDefault()
  event.stopPropagation()

  const startX = event.clientX
  const startY = event.clientY
  const startWidth = size.value.width
  const startHeight = size.value.height
  const prevUserSelect = document.body.style.userSelect
  // 拖拽期间禁止选中文本 / 拖出幽灵
  document.body.style.userSelect = 'none'

  function onPointerMove(moveEvent) {
    const next = { ...size.value }
    if (direction.includes('e')) {
      next.width = clampSize(startWidth + (moveEvent.clientX - startX), props.minWidth, props.maxWidth)
    }
    if (direction.includes('s')) {
      next.height = clampSize(startHeight + (moveEvent.clientY - startY), props.minHeight, props.maxHeight)
    }
    size.value = next
  }

  function cleanup() {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', cleanup)
    window.removeEventListener('pointercancel', cleanup)
    document.body.style.userSelect = prevUserSelect
    stopResize = null
  }

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', cleanup)
  window.addEventListener('pointercancel', cleanup)
  stopResize = cleanup
}

/* ---------------- 遮罩点击 ---------------- */

/** 只有按下与抬起都在遮罩上才算「点击遮罩」，避免从弹窗内拖到遮罩上误关闭 */
let pressOnOverlay = false

function onOverlayPointerDown(event) {
  pressOnOverlay = event.target === event.currentTarget
}

function onOverlayClick(event) {
  const onOverlay = event.target === event.currentTarget
  if (pressOnOverlay && onOverlay && props.closeOnClickModal) close()
  pressOnOverlay = false
}
</script>

<template>
  <Teleport to="body" :disabled="!appendToBody">
    <div v-if="visible" class="rd-dialog-root nokey">
      <div
        v-if="modal"
        class="rd-dialog__overlay"
        @pointerdown="onOverlayPointerDown"
        @click="onOverlayClick"
      />

      <section
        ref="dialogRef"
        class="rd-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        tabindex="-1"
        :style="dialogStyle"
      >
        <header
          class="rd-dialog__header"
          :class="{ 'is-draggable': draggable }"
          @pointerdown="startDrag"
        >
          <slot name="header">
            <h2 class="rd-dialog__title">{{ title }}</h2>
          </slot>
          <button
            v-if="showClose"
            class="rd-dialog__close"
            type="button"
            aria-label="关闭"
            title="关闭"
            @click="close"
          >
            ×
          </button>
        </header>

        <div class="rd-dialog__body">
          <slot />
        </div>

        <footer v-if="$slots.footer" class="rd-dialog__footer">
          <slot name="footer" />
        </footer>

        <template v-if="resizable">
          <span class="rd-dialog__resizer rd-dialog__resizer--e" @pointerdown="startResize($event, 'e')" />
          <span class="rd-dialog__resizer rd-dialog__resizer--s" @pointerdown="startResize($event, 's')" />
          <span class="rd-dialog__resizer rd-dialog__resizer--se" @pointerdown="startResize($event, 'se')" />
        </template>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.rd-dialog-root {
  position: fixed;
  inset: 0;
  z-index: 3000;
}

.rd-dialog__overlay {
  position: absolute;
  inset: 0;
  background: rgba(6, 8, 12, 0.58);
}

.rd-dialog {
  position: absolute;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  color: var(--text, #e9edf5);
  background: var(--surface, #151922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: 10px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6);
  outline: none;
}

/* ---------------- 头部 ---------------- */

.rd-dialog__header {
  display: flex;
  flex: none;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border2, #343c4c);
}

/* 可拖拽移动：给出移动光标，并避免拖拽时选中标题文本 */
.rd-dialog__header.is-draggable {
  cursor: move;
  user-select: none;
  touch-action: none;
}

.rd-dialog__title {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.rd-dialog__close {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  font: inherit;
  font-size: 18px;
  line-height: 1;
  color: var(--muted, #767f92);
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease;
}

.rd-dialog__close:hover {
  color: var(--text, #e9edf5);
  background: rgba(255, 255, 255, 0.08);
}

/* ---------------- 内容区（超出内部滚动） ---------------- */

.rd-dialog__body {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow: auto;
}

/* ---------------- 操作区 ---------------- */

.rd-dialog__footer {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border2, #343c4c);
}

/* ---------------- 调整大小把手 ---------------- */

.rd-dialog__resizer {
  position: absolute;
  z-index: 1;
  touch-action: none;
}

/* 右 / 下边缘把手贴在边框外侧：既能整条拖动，又不会压住内容区的滚动条 */
.rd-dialog__resizer--e {
  top: 0;
  right: -6px;
  width: 6px;
  height: 100%;
  cursor: ew-resize;
}

.rd-dialog__resizer--s {
  left: 0;
  bottom: -6px;
  width: 100%;
  height: 6px;
  cursor: ns-resize;
}

/* 右下角把手：画一组斜线，给出可拖拽的视觉暗示 */
.rd-dialog__resizer--se {
  right: 0;
  bottom: 0;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  background: repeating-linear-gradient(
    135deg,
    transparent 0 3px,
    var(--border2, #343c4c) 3px 4px
  );
  border-bottom-right-radius: 10px;
}
</style>
