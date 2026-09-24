<script setup>
/**
 * LLM 配置页（占位）
 *
 * 规划：维护模型提供方与密钥、默认模型、采样参数，供画布上的节点引用。
 * 界面与后端接口都还没做，这里先占住首页导航的入口。
 */
</script>

<template>
  <section class="config-page">
    <h1 class="config-page__title">LLM 配置</h1>
    <p class="config-page__hint">页面待接入：后续在这里维护模型提供方、密钥与默认参数。</p>
  </section>
</template>

<style scoped>
.config-page__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.config-page__hint {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--muted, #767f92);
}
</style>
