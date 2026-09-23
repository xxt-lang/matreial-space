<script setup>
/**
 * 上游节点展示（GenImageNode 私有子组件）
 * 展示通过连线指向当前节点的上游节点：缩略图 + 序号角标
 * 悬浮时右上角出现删除按钮，用于断开该条连线
 */
defineProps({
  /** 上游节点列表（vue-flow Node 数组） */
  nodes: { type: Array, default: () => [] },
})

const emit = defineEmits(['remove'])

/** 悬停提示：`#序号 名称` */
function itemTitle(node) {
  const label = node.data?.label || node.id
  return node.data?.index ? `#${node.data.index} ${label}` : label
}
</script>

<template>
  <section class="upstream-panel nodrag">
    <span class="upstream-panel__label">上游</span>

    <ul class="upstream-panel__list nowheel">
      <li
        v-for="node in nodes"
        :key="node.id"
        class="upstream-panel__item"
        :title="itemTitle(node)"
      >
        <img
          v-if="node.data?.image"
          class="upstream-panel__thumb"
          :src="node.data.image"
          alt=""
          draggable="false"
        />
        <span v-else class="upstream-panel__thumb upstream-panel__thumb--empty" />

        <span v-if="node.data?.index" class="upstream-panel__seq">#{{ node.data.index }}</span>

        <button
          class="upstream-panel__remove nodrag"
          type="button"
          title="删除该连线"
          @click.stop="emit('remove', node.id)"
        >
          ×
        </button>
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
  position: relative;
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

/* 上游节点序号角标（贴缩略图右下角，避免超出容器被裁切） */
.upstream-panel__seq {
  position: absolute;
  right: 2px;
  bottom: 2px;
  padding: 0 4px;
  font-size: 10px;
  line-height: 14px;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border-radius: 999px;
}

/* 删除连线按钮：默认隐藏，悬浮该项时出现（贴缩略图右上角，避免被列表裁切） */
.upstream-panel__remove {
  position: absolute;
  top: 1px;
  right: 1px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  padding: 0;
  font: inherit;
  font-size: 11px;
  line-height: 1;
  color: var(--text, #e9edf5);
  background: rgba(13, 17, 23, 0.85);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, color 0.15s ease, background 0.15s ease;
}

.upstream-panel__item:hover .upstream-panel__remove {
  opacity: 1;
}

.upstream-panel__remove:hover {
  color: #fff;
  background: #e5484d;
}
</style>
