<script setup>
/**
 * 应用根组件
 * - 不再放置导航栏，直接全屏渲染当前路由
 * - 项目主页面即 workSpace/work.vue（画布宿主）
 */
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>
