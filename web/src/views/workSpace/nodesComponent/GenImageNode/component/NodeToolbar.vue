<script setup>
/**
 * 工具栏模块（GenImageNode 私有子组件）
 * 完美像素画 / 高清像素画 / 尺寸选择 / 编辑
 *
 * 模型选择在提示词输入区的操作行上（与生成按钮同一行），见 GenImageNode / PromptInput
 */
import SelectMenu from '../../../assistComponent/SelectMenu.vue'

defineProps({
  /** hd = 高清像素画，perfect = 完美像素画 */
  mode: { type: String, default: 'hd' },
  /** 当前尺寸边长 */
  size: { type: Number, default: 64 },
})

const emit = defineEmits(['update:mode', 'update:size', 'edit'])

/** 尺寸候选项 */
const SIZE_OPTIONS = [64, 32, 256].map((value) => ({ value, label: `${value}×${value}` }))
</script>

<template>
  <div class="node-toolbar nodrag">
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

    <SelectMenu
      :model-value="size"
      :options="SIZE_OPTIONS"
      placeholder="尺寸"
      @update:model-value="emit('update:size', $event)"
    />

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
  gap: 6px;
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

.node-toolbar__btn--edit {
  margin-left: auto;
}
</style>
