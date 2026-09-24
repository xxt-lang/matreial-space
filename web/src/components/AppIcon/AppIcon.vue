<script setup>
/**
 * 公共图标组件
 *
 * 用法：<AppIcon type="workspace" :size="18" />
 *
 * - 图标就是 `icon/` 目录下的独立 svg 文件，**文件名（不含扩展名）即 type**
 * - 新增图标 = 丢一个 svg 进 `icon/` 目录，不用改这个组件
 * - 颜色跟随文字色：svg 里写 `stroke="currentColor"` / `fill="currentColor"` 即可，
 *   外层只要改 `color` 就能连带染色，hover 与激活态都不需要额外处理
 * - 每个 svg 自带 viewBox 与描边粗细（那是图标设计的一部分），组件只管尺寸
 */
import { computed } from 'vue'

const props = defineProps({
  /** 图标类型：对应 icon/<type>.svg 的文件名 */
  type: { type: String, required: true },
  /** 渲染尺寸（px），宽高一致 */
  size: { type: [Number, String], default: 16 },
})

/**
 * 把 icon/ 下的 svg 全部按「源码字符串」引入
 *
 * `?raw` + eager：构建期静态分析（不是运行时请求），直接内联进 DOM ——
 * 这样图标能被 currentColor 染色，也不会多出一次网络请求
 */
const SOURCES = import.meta.glob('./icon/*.svg', { eager: true, query: '?raw', import: 'default' })

/** type → svg 源码 */
const ICONS = Object.fromEntries(
  Object.entries(SOURCES).map(([path, source]) => [
    path.replace('./icon/', '').replace(/\.svg$/, ''),
    source,
  ]),
)

/** 找不到图标时只在开发期提示一次，避免控制台被刷屏 */
const warned = new Set()

const markup = computed(() => {
  const source = ICONS[props.type]
  if (!source && import.meta.env.DEV && !warned.has(props.type)) {
    warned.add(props.type)
    console.warn(`[AppIcon] 找不到图标文件 icon/${props.type}.svg`)
  }
  return source ?? ''
})

const rootStyle = computed(() => ({ width: `${props.size}px`, height: `${props.size}px` }))
</script>

<template>
  <!-- v-html 的内容是本仓库内的静态 svg 文件，不含任何外部输入 -->
  <span class="app-icon" :style="rootStyle" aria-hidden="true" v-html="markup" />
</template>

<style scoped>
.app-icon {
  display: block;
  flex: none;
}

/* 内联进来的 svg 撑满外层：它没有 width / height 属性，不给尺寸会退化成默认大小 */
.app-icon :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
