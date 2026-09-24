<script setup>
/**
 * 图片展示模块（GenImageNode 私有子组件）
 * - 无图：点阵占位 +「上传图片」
 * - 有图：等比完整展示，右下角可「更换」
 * - status = generating：盖一层加载中（无论节点是否处于编辑态都会展示），
 *   由父节点在接口成功 / 失败后改写 status 才会撤掉
 * - status = error：展示失败信息（有图时叠在图片下方，无图时显示在占位区）
 *
 * 上传：选择本地图片 → 校验类型/大小 → 读为 dataURL → emit('upload')，由父节点写入 data
 */
import { computed, ref } from 'vue'

const props = defineProps({
  image: { type: String, default: '' },
  /** idle 空闲 / generating 生成中 / done 成功 / error 失败 */
  status: { type: String, default: 'idle' },
  /** 生成失败时的错误信息 */
  error: { type: String, default: '' },
})

/** 生成中：加载态优先于其它内容展示 */
const isGenerating = computed(() => props.status === 'generating')

const emit = defineEmits(['upload'])

/** 单张图片大小上限：5MB */
const MAX_SIZE = 5 * 1024 * 1024

const fileInputRef = ref(null)
const error = ref('')

function openPicker() {
  error.value = ''
  fileInputRef.value?.click()
}

function onFileChange(event) {
  const input = event.target
  const file = input.files?.[0]
  // 清空 value，保证同一个文件再次选择也能触发 change
  input.value = ''
  if (!file) return

  if (!file.type.startsWith('image/')) {
    error.value = '仅支持图片文件'
    return
  }
  if (file.size > MAX_SIZE) {
    error.value = '图片不能超过 5MB'
    return
  }

  const reader = new FileReader()
  reader.onload = () => {
    error.value = ''
    emit('upload', {
      name: file.name,
      type: file.type,
      size: file.size,
      dataUrl: reader.result,
    })
  }
  reader.onerror = () => {
    error.value = '图片读取失败，请重试'
  }
  reader.readAsDataURL(file)
}
</script>

<template>
  <section class="image-stage">
    <img
      v-if="image"
      class="image-stage__img"
      :src="image"
      alt="生成结果"
      draggable="false"
    />

    <div v-else-if="!isGenerating" class="image-stage__empty">
      <div class="image-stage__grid" aria-hidden="true" />
      <p class="image-stage__hint">暂无图片</p>
      <button class="image-stage__upload nodrag" type="button" @click="openPicker">
        上传图片
      </button>
      <p v-if="error" class="image-stage__error">{{ error }}</p>
    </div>

    <!-- 生成中：盖在图片 / 占位之上，节点折叠时同样可见 -->
    <div v-if="isGenerating" class="image-stage__loading">
      <span class="image-stage__spinner" aria-hidden="true" />
      <p class="image-stage__loading-text">正在生成，请稍候…</p>
    </div>

    <!-- 生成失败：有图时叠一层提示 -->
    <p v-if="!isGenerating && error && image" class="image-stage__error image-stage__error--float">
      {{ error }}
    </p>

    <button
      v-if="image && !isGenerating"
      class="image-stage__change nodrag"
      type="button"
      title="更换图片"
      @click="openPicker"
    >
      更换
    </button>

    <input
      ref="fileInputRef"
      class="image-stage__file"
      type="file"
      accept="image/*"
      @change="onFileChange"
    />
  </section>
</template>

<style scoped>
.image-stage {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 0%, rgba(240, 166, 61, 0.07), transparent 62%),
    #0d1117;
}

.image-stage__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  user-select: none;
  /* 最近邻放大：生成/编辑出来的像素画是小图（如 64×64），
     插值放大就糊了，像素画必须保留硬边 */
  image-rendering: pixelated;
}

.image-stage__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  height: 100%;
}

/* 点阵底纹 */
.image-stage__grid {
  width: 132px;
  height: 132px;
  border-radius: 10px;
  border: 1px dashed var(--border2, #343c4c);
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 14px 14px;
}

.image-stage__hint {
  margin: 0;
  font-size: 12px;
  color: var(--muted, #767f92);
}

.image-stage__upload {
  padding: 6px 14px;
  font: inherit;
  font-size: 12px;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border: none;
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.image-stage__upload:hover {
  opacity: 0.88;
}

.image-stage__error {
  margin: 0;
  font-size: 11px;
  color: #ff7a7a;
}

/* ---------------- 生成中 ---------------- */

/* 盖住整个图片区：折叠态也可见，只有父级把 status 改成成功 / 失败才撤掉 */
.image-stage__loading {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(9, 10, 14, 0.72);
}

.image-stage__spinner {
  width: 26px;
  height: 26px;
  border: 2px solid rgba(240, 166, 61, 0.25);
  border-top-color: var(--accent, #f0a63d);
  border-radius: 50%;
  animation: image-stage-spin 0.8s linear infinite;
}

@keyframes image-stage-spin {
  to {
    transform: rotate(360deg);
  }
}

.image-stage__loading-text {
  margin: 0;
  font-size: 12px;
  color: var(--muted, #767f92);
}

/* 有图但生成失败：贴左下角（右下角留给「更换」按钮） */
.image-stage__error--float {
  position: absolute;
  left: 10px;
  bottom: 10px;
  right: 74px;
  overflow: hidden;
  padding: 4px 8px;
  color: #ff9d9d;
  white-space: nowrap;
  text-overflow: ellipsis;
  background: rgba(13, 17, 23, 0.82);
  border: 1px solid rgba(229, 72, 77, 0.4);
  border-radius: var(--r-sm, 6px);
}

/* 「更换」按钮放右下角，把右上角让给节点的缩放比例提示 */
.image-stage__change {
  position: absolute;
  right: 10px;
  bottom: 10px;
  padding: 4px 10px;
  font: inherit;
  font-size: 11px;
  color: var(--text, #e9edf5);
  background: rgba(13, 17, 23, 0.72);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.image-stage:hover .image-stage__change {
  opacity: 1;
}

.image-stage__change:hover {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.image-stage__file {
  display: none;
}
</style>
