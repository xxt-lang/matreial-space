<script setup>
/**
 * 提示词输入模块（GenImageNode 私有子组件）
 * 文本输入框 + 生成按钮
 */
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'generate'])

const canGenerate = computed(() => props.modelValue.trim().length > 0)

function onInput(event) {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <div class="prompt-panel nodrag">
    <textarea
      class="prompt-panel__input nowheel"
      rows="2"
      :value="modelValue"
      placeholder="描述画面，例如：赛博朋克风格的猫"
      @input="onInput"
      @keydown.enter.exact.prevent="canGenerate && emit('generate')"
    />

    <button
      class="prompt-panel__btn"
      type="button"
      :disabled="!canGenerate"
      @click="emit('generate')"
    >
      生成
    </button>
  </div>
</template>

<style scoped>
.prompt-panel {
  display: flex;
  align-items: stretch;
  gap: 8px;
  padding: 8px;
  border-top: 1px solid var(--border2, #343c4c);
  background: var(--surface-2, #1b2029);
}

.prompt-panel__input {
  flex: 1;
  min-width: 0;
  padding: 7px 10px;
  font: inherit;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text, #e9edf5);
  background: #0f131a;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  resize: none;
  outline: none;
  transition: border-color 0.15s ease;
}

.prompt-panel__input::placeholder {
  color: var(--muted, #767f92);
}

.prompt-panel__input:focus {
  border-color: var(--accent, #f0a63d);
}

.prompt-panel__btn {
  flex: none;
  width: 72px;
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

.prompt-panel__btn:hover:not(:disabled) {
  opacity: 0.88;
}

.prompt-panel__btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}
</style>
