<script setup>
/**
 * 工具栏模块（GenImageNode 私有子组件）
 * 完美像素画 / 高清像素画 / 模型选择 / 尺寸选择 / 编辑
 *
 * 模型与尺寸两个下拉共用一套渲染逻辑；下拉向上弹出，
 * 避免被节点容器的 overflow: hidden 裁切。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { MODEL_OPTIONS } from './modelOptions.js'

const props = defineProps({
  /** hd = 高清像素画，perfect = 完美像素画 */
  mode: { type: String, default: 'hd' },
  /** 当前模型标识 */
  model: { type: String, default: '' },
  /** 当前尺寸边长 */
  size: { type: Number, default: 64 },
})

const emit = defineEmits(['update:mode', 'update:model', 'update:size', 'edit'])

const SIZE_OPTIONS = [64, 32, 256]

/** 下拉配置：key 决定回传事件，label 为触发器文案 */
const selects = computed(() => [
  {
    key: 'model',
    label: MODEL_OPTIONS.find(m => m.value === props.model)?.label ?? '选择模型',
    options: MODEL_OPTIONS,
  },
  {
    key: 'size',
    label: `${props.size}×${props.size}`,
    options: SIZE_OPTIONS.map(v => ({ value: v, label: `${v}×${v}` })),
  },
])

/** 当前展开的下拉 key，空串表示全部收起 */
const openKey = ref('')
const rootRef = ref(null)

function toggle(key) {
  openKey.value = openKey.value === key ? '' : key
}

function pick(key, value) {
  if (key === 'model') emit('update:model', value)
  if (key === 'size') emit('update:size', value)
  openKey.value = ''
}

function onDocPointerDown(event) {
  if (!openKey.value) return
  if (rootRef.value?.contains(event.target)) return
  openKey.value = ''
}

onMounted(() => document.addEventListener('pointerdown', onDocPointerDown, true))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocPointerDown, true))
</script>

<template>
  <div ref="rootRef" class="node-toolbar nodrag">
    <button
      class="node-toolbar__btn"
      :class="{ 'is-active': mode === 'perfect' }"
      type="button"
      @click="emit('update:mode', 'perfect')"
    >
      完美像素画
    </button>

    <button
      class="node-toolbar__btn"
      :class="{ 'is-active': mode === 'hd' }"
      type="button"
      @click="emit('update:mode', 'hd')"
    >
      高清像素画
    </button>

    <div v-for="sel in selects" :key="sel.key" class="node-toolbar__select">
      <button
        class="node-toolbar__btn"
        :class="{ 'is-active': openKey === sel.key }"
        type="button"
        @click="toggle(sel.key)"
      >
        {{ sel.label }}
        <span class="node-toolbar__caret">▾</span>
      </button>

      <ul v-if="openKey === sel.key" class="node-toolbar__options nowheel">
        <li
          v-for="opt in sel.options"
          :key="opt.value"
          class="node-toolbar__option"
          :class="{ 'is-active': opt.value === (sel.key === 'model' ? model : size) }"
          @click="pick(sel.key, opt.value)"
        >
          {{ opt.label }}
        </li>
      </ul>
    </div>

    <button class="node-toolbar__btn node-toolbar__btn--edit" type="button" @click="emit('edit')">
      编辑
    </button>
  </div>
</template>

<style scoped>
.node-toolbar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px;
  border-top: 1px solid var(--border2, #343c4c);
  background: var(--surface-2, #1b2029);
}

.node-toolbar__btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  font: inherit;
  font-size: 12px;
  white-space: nowrap;
  color: var(--text, #e9edf5);
  background: transparent;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}

.node-toolbar__btn:hover {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.node-toolbar__btn.is-active {
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.node-toolbar__caret {
  font-size: 10px;
  line-height: 1;
}

.node-toolbar__select {
  position: relative;
}

/* 向上弹出，保证在节点可视区域内完整显示 */
.node-toolbar__options {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  z-index: 20;
  min-width: 100%;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: var(--surface, #151922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55);
}

.node-toolbar__option {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text, #e9edf5);
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}

.node-toolbar__option:hover {
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
}

.node-toolbar__option.is-active {
  color: var(--accent, #f0a63d);
}

.node-toolbar__option.is-active:hover {
  color: var(--accent-ink, #201404);
}

.node-toolbar__btn--edit {
  margin-left: auto;
}
</style>
