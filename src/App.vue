<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <nav style="padding: 8px; border-bottom: 1px solid #eee; display: flex; gap: 12px;">
    <RouterLink to="/">首页</RouterLink>
    <RouterLink to="/flow">Flow</RouterLink>
  </nav>
  <main style="padding: 16px;">
    <RouterView />
  </main>
</template>
