<script setup>
/**
 * 首页布局：左侧图标导航 + 右侧页面容器
 *
 * - 导航只展示图标（文案通过 title / aria-label 提供），固定在页面左侧并垂直居中
 * - 右侧渲染子路由：工作空间管理（默认）/ LLM 配置 / Skill 配置
 * - 画布不在本布局内：它是独立的全屏页（/workspace/:workspaceId?）
 */
import { RouterView } from 'vue-router'

import AppIcon from '../../components/AppIcon.vue'

/** 左侧导航项：入口、图标与顺序只在这里维护（icon 取值见 components/AppIcon.vue） */
const NAV_ITEMS = [
  { to: '/workspaces', label: '工作空间管理', icon: 'workspace' },
  { to: '/llm', label: 'LLM 配置', icon: 'llm' },
  { to: '/skill', label: 'Skill 配置', icon: 'skill' },
]
</script>

<template>
  <div class="home">
    <aside class="home__nav">
      <nav class="home__nav-list">
        <router-link
          v-for="item in NAV_ITEMS"
          :key="item.to"
          class="home__nav-item"
          :to="item.to"
          :title="item.label"
          :aria-label="item.label"
        >
          <AppIcon :type="item.icon" :size="18" />
        </router-link>
      </nav>
    </aside>

    <main class="home__content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
/*
  配色沿用画布区的暗色 token，统一带 fallback（这些 token 全局未定义）；
  正文色用 --fg 而不是 --text，后者在 style.css 里是浅色灰，落在暗底上看不清。
*/
.home {
  box-sizing: border-box;
  flex: 1;
  width: 100%;
  min-height: 100svh;
  /* 左侧留出固定导航栏的位置：left(24) + 导航宽度(图标按钮 28 + 内边距 6×2) + 间距(20) */
  padding: 20px 24px 32px 84px;
  color: var(--fg, #e9edf5);
  background-color: var(--bg-deep, #090a0e);
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 22px 22px;
}

/* ---------------- 左侧导航：只有图标，垂直居中固定在页面左侧 ---------------- */

.home__nav {
  position: fixed;
  top: 50%;
  left: 24px;
  /* 高度由内容决定（不占满整屏），靠 translate 做真正的垂直居中 */
  transform: translateY(-50%);
  /* 宽度不写死：由图标按钮撑开（图标 + 一点边距），这里只留一圈内边距 */
  padding: 6px;
  background: var(--surface, #141922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r, 10px);
}

.home__nav-list {
  display: grid;
  gap: 4px;
}

/* 图标按钮：尺寸 = 图标(18) + 边距，所以不写死宽高；hover 走 accent 约定，激活态是 accent 实底 + 深色图标 */
.home__nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5px;
  color: var(--fg, #e9edf5);
  border-radius: var(--r-sm, 6px);
  text-decoration: none;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.home__nav-item:hover {
  color: var(--accent, #f0a63d);
  background: var(--surface-2, #1b2130);
}

/* vue-router 命中当前路由时自动加的类 */
.home__nav-item.router-link-active {
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
}
</style>
