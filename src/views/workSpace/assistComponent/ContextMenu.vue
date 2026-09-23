<script setup>
/**
 * 通用右键上下文菜单（辅助组件）
 * - 与业务无关：仅接收坐标 / 显隐 / 菜单项，通过 emit 回传选择结果
 * - 坐标基于视口（fixed + Teleport），避免受父级 transform 影响
 */
import { computed, onBeforeUnmount, onMounted } from 'vue'

const props = defineProps({
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  visible: { type: Boolean, default: false },
  /** [{ key, label, disabled? }] */
  items: { type: Array, default: () => [] },
})

const emit = defineEmits(['select', 'close'])

const MENU_W = 152
const MENU_H = 132

// 贴边时自动内收，保证菜单完整可见
const style = computed(() => ({
  left: Math.max(4, Math.min(props.x, window.innerWidth - MENU_W - 8)) + 'px',
  top: Math.max(4, Math.min(props.y, window.innerHeight - MENU_H - 8)) + 'px',
}))

function onSelect(item) {
  if (item.disabled) return
  emit('select', item.key, item)
}

function onClose() {
  if (props.visible) emit('close')
}

// 点击菜单外 / Esc / 缩放窗口 / 滚动 → 关闭
function onDocMouseDown(e) {
  if (!props.visible) return
  if (e.target?.closest?.('.ctx-menu')) return
  emit('close')
}

function onKeydown(e) {
  if (e.key === 'Escape') onClose()
}

onMounted(() => {
  document.addEventListener('mousedown', onDocMouseDown, true)
  document.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onClose)
  window.addEventListener('wheel', onClose, { passive: true })
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocMouseDown, true)
  document.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onClose)
  window.removeEventListener('wheel', onClose)
})
</script>

<template>
  <Teleport to="body">
    <ul v-if="visible && items.length" class="ctx-menu" :style="style" @contextmenu.prevent>
      <li
        v-for="it in items"
        :key="it.key"
        class="ctx-menu__item"
        :class="{ 'is-disabled': it.disabled }"
        @click="onSelect(it)"
      >
        {{ it.label }}
      </li>
    </ul>
  </Teleport>
</template>

<style scoped>
.ctx-menu {
  position: fixed;
  z-index: 3000;
  min-width: 152px;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: var(--surface, #151922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r, 8px);
  box-shadow: var(--shadow-lg, 0 16px 48px rgba(0, 0, 0, 0.55));
  user-select: none;
}

.ctx-menu__item {
  padding: 7px 12px;
  font-size: 13px;
  color: var(--text, #e9edf5);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  white-space: nowrap;
}

.ctx-menu__item:hover {
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
}

.ctx-menu__item.is-disabled {
  color: var(--muted, #767f92);
  cursor: not-allowed;
  background: none;
}
</style>
