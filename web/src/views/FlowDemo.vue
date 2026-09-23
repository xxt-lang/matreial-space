<script setup>
import { ref } from 'vue'
import { VueFlow } from '@vue-flow/core'

const nodes = ref([
  { id: '1', position: { x: 0, y: 0 }, label: '节点 1' },
  { id: '2', position: { x: 200, y: 100 }, label: '节点 2' },
])

const edges = ref([
  { id: 'e1-2', source: '1', target: '2', label: '连接' },
])
</script>

<template>
  <div style="height: 600px; width: 100%;">
    <h1>Vue Flow 示例</h1>
    <VueFlow :nodes="nodes" :edges="edges" />
  </div>
</template>

<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
</style>
