<script setup>
/**
 * 下拉选择（工作区公共组件）
 * - 触发器是按钮，当前选项显示在按钮上
 * - 选项列表向上弹出：放在节点内部时不会被节点下缘裁切
 * - 选中或点击组件外部时收起
 *
 * 画布适配：根元素带 `nodrag`、选项列表带 `nowheel`，
 * 放在 vue-flow 节点内使用时不会触发节点拖动 / 画布缩放
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  /** 候选项：[{ value, label }] */
  options: { type: Array, default: () => [] },
  /** 当前值不在候选项里时的触发器文案 */
  placeholder: { type: String, default: '请选择' },
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const rootRef = ref(null)

/** 触发器文案：优先显示选中项，匹配不到时用占位文案 */
const currentLabel = computed(
  () => props.options.find((item) => item.value === props.modelValue)?.label ?? props.placeholder,
)

function toggle() {
  open.value = !open.value
}

function pick(value) {
  emit('update:modelValue', value)
  open.value = false
}

/** 点击组件外部收起 */
function onDocPointerDown(event) {
  if (!open.value) return
  if (rootRef.value?.contains(event.target)) return
  open.value = false
}

onMounted(() => document.addEventListener('pointerdown', onDocPointerDown, true))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocPointerDown, true))
</script>

<template>
  <div ref="rootRef" class="select-menu nodrag">
    <button
      class="select-menu__trigger"
      :class="{ 'is-open': open }"
      type="button"
      @click="toggle"
    >
      <span class="select-menu__label">{{ currentLabel }}</span>
      <span class="select-menu__caret" aria-hidden="true">▾</span>
    </button>

    <ul v-if="open" class="select-menu__options nowheel">
      <li
        v-for="option in options"
        :key="option.value"
        class="select-menu__option"
        :class="{ 'is-active': option.value === modelValue }"
        @click="pick(option.value)"
      >
        {{ option.label }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.select-menu {
  position: relative;
  display: inline-flex;
  min-width: 0;
}

.select-menu__trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  height: 30px;
  padding: 0 10px;
  font: inherit;
  font-size: 12px;
  color: var(--text, #e9edf5);
  background: transparent;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.select-menu__trigger:hover,
.select-menu__trigger.is-open {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.select-menu__label {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.select-menu__caret {
  flex: none;
  font-size: 10px;
  line-height: 1;
}

/* 向上弹出，保证在节点可视区域内完整显示 */
.select-menu__options {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  z-index: 30;
  min-width: 100%;
  max-height: 200px;
  margin: 0;
  padding: 4px;
  overflow-y: auto;
  list-style: none;
  background: var(--surface, #151922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55);
}

.select-menu__option {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text, #e9edf5);
  white-space: nowrap;
  border-radius: 4px;
  cursor: pointer;
}

.select-menu__option:hover {
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
}

.select-menu__option.is-active {
  color: var(--accent, #f0a63d);
}

.select-menu__option.is-active:hover {
  color: var(--accent-ink, #201404);
}
</style>
