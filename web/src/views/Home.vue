<script setup>
import { useCounterStore } from '../stores/counter'
const counter = useCounterStore()
</script>

<template>
  <div>
    <h1>首页</h1>
    <p>Pinia 计数: {{ counter.count }} (双倍: {{ counter.double }})</p>
    <button @click="counter.increment()">+1</button>
    <p><router-link to="/flow">前往 Vue Flow 示例 →</router-link></p>
  </div>
</template>
