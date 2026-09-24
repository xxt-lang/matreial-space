<script setup>
/**
 * 公共图标组件
 *
 * 用法：<AppIcon type="workspace" :size="18" />
 *
 * - 所有图标统一按 24×24 坐标系绘制，描边风格（fill: none + stroke: currentColor），
 *   颜色跟随文字色，所以 hover / 激活态只要改 color 就能连带把图标染色
 * - 图标只在这里维护：新增一个图标 = 往 ICONS 里加一条 path 数据（一条数据可以含多条子路径）
 */
import { computed } from 'vue'

const props = defineProps({
  /** 图标类型，取值见下方 ICONS 的 key */
  type: { type: String, required: true },
  /** 渲染尺寸（px），宽高一致 */
  size: { type: [Number, String], default: 16 },
  /** 描边粗细 */
  strokeWidth: { type: [Number, String], default: 1.6 },
})

/** 图标表：type → path 的 d 属性列表（全部按 24×24 画，只描边不填充） */
const ICONS = {
  /** 工作空间：四宫格 */
  workspace: ['M4.5 4.5h5.5v5.5H4.5zM14 4.5h5.5v5.5H14zM4.5 14h5.5v5.5H4.5zM14 14h5.5v5.5H14z'],
  /** LLM：芯片（外框 + 内核 + 引脚） */
  llm: [
    'M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
    'M9.5 9.5h5v5h-5z',
    'M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2',
  ],
  /** Skill：闪电 */
  skill: ['M13 2 4 13h7l-1 9 9-11h-7l1-9z'],
}

/** 未登记的 type 只在开发期提示一次，避免控制台被刷屏 */
const warned = new Set()

const paths = computed(() => {
  const value = ICONS[props.type]
  if (!value && import.meta.env.DEV && !warned.has(props.type)) {
    warned.add(props.type)
    console.warn(`[AppIcon] 未登记的图标 type：${props.type}`)
  }
  return value ?? []
})
</script>

<template>
  <svg
    class="app-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="(d, index) in paths" :key="index" :d="d" />
  </svg>
</template>

<style scoped>
/* display: block 去掉 inline svg 的基线间隙，方便和文字对齐 */
.app-icon {
  display: block;
  flex: none;
}
</style>
