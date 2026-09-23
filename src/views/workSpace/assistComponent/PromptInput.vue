<script setup>
/**
 * 提示词输入框（工作区公共组件）
 *
 * 交互与结构：
 * - 文本域（可纵向拖拽调节高度）+ 提交按钮，二者共用一个带背景的 box；
 *   输入框自身透明无边框，聚焦态由 box 的 :focus-within 统一反馈
 * - 与业务无关：文案、初始高度都通过 props 传入，高度变化通过 emit 上报，
 *   由使用方决定是否持久化、以及如何联动自身尺寸
 *
 * 画布适配：根元素带 `nodrag`、文本域带 `nowheel`，
 * 放在 vue-flow 节点内使用时不会触发节点拖动 / 画布缩放
 *
 * 高度（offsetHeight，不受父级 transform 影响，始终是未缩放的 CSS 像素）：
 *   panel —— 面板当前高度（使用方可据此同步自身高度）
 *   base  —— 默认状态（文本域两行）下的面板高度，作为高度增量的基准
 *   input —— 文本域当前高度（使用方据此持久化，供下次恢复）
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  /** 已保存的文本域高度（px），0 表示使用默认两行高度 */
  height: { type: Number, default: 0 },
  placeholder: { type: String, default: '请输入提示词' },
  /** 提交按钮文案 */
  submitText: { type: String, default: '生成' },
})

const emit = defineEmits(['update:modelValue', 'submit', 'resize'])

const canSubmit = computed(() => props.modelValue.trim().length > 0)

const panelRef = ref(null)
const inputRef = ref(null)
let observer = null

/**
 * 默认状态下的面板高度：组件样式固定，模块级量一次即可
 * 注意必须在应用已保存高度「之前」测量，否则量到的是恢复后的高度
 */
let PANEL_BASE_HEIGHT = 0

/** 上报面板高度 / 面板基准高度 / 文本域高度 */
function reportHeight() {
  if (!panelRef.value) return
  emit('resize', {
    panel: panelRef.value.offsetHeight,
    base: PANEL_BASE_HEIGHT,
    input: inputRef.value?.offsetHeight ?? 0,
  })
}

/** 应用已保存的文本域高度（空值表示回到默认高度） */
function applyHeight(height) {
  if (inputRef.value) inputRef.value.style.height = height > 0 ? `${height}px` : ''
}

onMounted(() => {
  const panel = panelRef.value
  if (panel) {
    if (!PANEL_BASE_HEIGHT) PANEL_BASE_HEIGHT = panel.offsetHeight
    applyHeight(props.height)
  }
  reportHeight()
  observer = new ResizeObserver(reportHeight)
  if (panel) observer.observe(panel)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})

function onInput(event) {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <div ref="panelRef" class="prompt-input nodrag">
    <!-- 文本域与提交按钮共用一个 box：背景、边框、圆角由 box 统一提供 -->
    <div class="prompt-input__box">
      <textarea
        ref="inputRef"
        class="prompt-input__field nowheel"
        rows="2"
        :value="modelValue"
        :placeholder="placeholder"
        @input="onInput"
        @keydown.enter.exact.prevent="canSubmit && emit('submit')"
      />

      <button
        class="prompt-input__submit"
        type="button"
        :disabled="!canSubmit"
        @click="emit('submit')"
      >
        {{ submitText }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.prompt-input {
  padding: 8px;
  border-top: 1px solid var(--border2, #343c4c);
  background: var(--surface-2, #1b2029);
}

/* 统一 box：文本域与提交按钮的公共容器，背景与边框都在这里 */
.prompt-input__box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  background: #0f131a;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  transition: border-color 0.15s ease;
}

/* 聚焦态由 box 整体反馈（输入框自身已无边框） */
.prompt-input__box:focus-within {
  border-color: var(--accent, #f0a63d);
}

.prompt-input__field {
  width: 100%;
  box-sizing: border-box;
  /* 可纵向拖拽调节高度，上下限避免内容区被挤没 / 溢出容器 */
  min-height: 44px;
  max-height: 200px;
  padding: 0;
  font: inherit;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text, #e9edf5);
  /* 背景与边框交给外层 box，输入框自身透明无边框 */
  background: transparent;
  border: none;
  resize: vertical;
  overflow-y: auto;
  outline: none;
}

.prompt-input__field::placeholder {
  color: var(--muted, #767f92);
}

/* 提交按钮：位于文本域下方，撑满 box 宽度 */
.prompt-input__submit {
  flex: none;
  box-sizing: border-box;
  width: 100%;
  height: 34px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border: none;
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.prompt-input__submit:hover:not(:disabled) {
  opacity: 0.88;
}

.prompt-input__submit:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}
</style>
