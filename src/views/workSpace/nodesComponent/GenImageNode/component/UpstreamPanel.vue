<script setup>
/**
 * 上游节点展示（GenImageNode 私有子组件）
 * 展示通过连线指向当前节点的上游节点，按顺序显示其缩略图
 */
defineProps({
  /** 上游节点列表（vue-flow Node 数组） */
  nodes: { type: Array, default: () => [] },
})
</script>

<template>
  <section class="upstream-panel nodrag">
    <span class="upstream-panel__label">上游</span>

    <ul class="upstream-panel__list nowheel">
      <li
        v-for="node in nodes"
        :key="node.id"
        class="upstream-panel__item"
        :title="node.data?.label || node.id"
      >
        <img
          v-if="node.data?.image"
          class="upstream-panel__thumb"
          :src="node.data.image"
          alt=""
          draggable="false"
        />
        <span v-else class="upstream-panel__thumb upstream-panel__thumb--empty" />
      </li>
    </ul>
  </section>
</template>

<style scoped>
.upstream-panel {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-top: 1px solid var(--border2, #343c4c);
  background: var(--surface-2, #1b2029);
}

.upstream-panel__label {
  flex: none;
  font-size: 11px;
  color: var(--muted, #767f92);
}

.upstream-panel__list {
  display: flex;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
  overflow-x: auto;
}

.upstream-panel__item {
  flex: none;
}

.upstream-panel__thumb {
  display: block;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  background: #0d1117;
  object-fit: cover;
}

/* 无图时用点阵占位 */
.upstream-panel__thumb--empty {
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.12) 1px, transparent 1px);
  background-size: 8px 8px;
}
</style>
