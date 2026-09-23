<script setup>
/**
 * 生图节点（vue-flow 自定义节点，type = GenImageNode）
 *
 * 固定尺寸 450×500，纵向三段式：
 *   上：图片展示区（支持本地上传 / 更换）
 *   中：工具栏（完美像素画 / 高清像素画 / 模型选择 / 尺寸选择 / 编辑）
 *   下：提示词输入 + 生成按钮（节点被选中时展开）
 *
 * 画布交互：通过 useVueFlow() 读写节点数据；左右两侧带 vue-flow 连线点；
 * 生成 / 编辑 / 上传动作 emit 给宿主（work.vue），由宿主决定是否调用 api/ 接口层。
 */
import { computed, ref, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import ImageStage from './component/ImageStage.vue'
import NodeToolbar from './component/NodeToolbar.vue'
import PromptPanel from './component/PromptPanel.vue'
import UpstreamPanel from './component/UpstreamPanel.vue'
import { DEFAULT_MODEL } from './component/modelOptions.js'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
})

const emit = defineEmits(['edit', 'generate', 'upload'])

const { updateNodeData, getSelectedNodes, getNodes, getEdges } = useVueFlow()

/** 节点被选中（点击）时进入编辑态，展开工具栏与输入区 */
const isActive = computed(() => getSelectedNodes.value.some((n) => n.id === props.id))

/** 通过连线指向当前节点的上游节点 */
const upstreamNodes = computed(() => {
  const sourceIds = getEdges.value.filter((e) => e.target === props.id).map((e) => e.source)
  if (!sourceIds.length) return []
  return getNodes.value.filter((n) => sourceIds.includes(n.id))
})

const prompt = ref(props.data.prompt ?? '')
/** 模型标识 */
const model = ref(props.data.model ?? DEFAULT_MODEL)
/** hd = 高清像素画，perfect = 完美像素画 */
const mode = ref(props.data.mode ?? 'hd')
/** 像素画边长 */
const size = ref(props.data.size ?? 64)

watch(prompt, (v) => updateNodeData(props.id, { prompt: v }))
watch(model, (v) => updateNodeData(props.id, { model: v }))
watch(mode, (v) => updateNodeData(props.id, { mode: v }))
watch(size, (v) => updateNodeData(props.id, { size: v }))

function onEdit() {
  emit('edit', { id: props.id, data: props.data })
}

/**
 * 提交生成。
 * payload 分三部分：
 *   setting —— 生成配置项（模型 / 模式 / 尺寸 / 参考图地址）
 *   text    —— 提示词文本
 *   nodes   —— 上游节点信息
 */
function onGenerate() {
  const text = prompt.value.trim()
  if (!text) return
  const payload = {
    id: props.id,
    setting: {
      model: model.value,
      mode: mode.value,
      size: size.value,
      // 上传 / 参考图的地址（本地为 dataURL，上传接口就绪后为远程地址）
      image: props.data.image || '',
    },
    text,
    // 上游节点信息（通过连线指向当前节点的节点）
    nodes: upstreamNodes.value.map((node) => ({
      id: node.id,
      index: node.data?.index ?? null,
      label: node.data?.label ?? '',
      image: node.data?.image ?? '',
    })),
  }
  console.log(payload)
  emit('generate', payload)
}

/** 本地选图后先直接展示；上传接口就绪后，由宿主替换为远程地址 */
function onUpload(payload) {
  updateNodeData(props.id, { image: payload.dataUrl })
  emit('upload', { id: props.id, ...payload })
}
</script>

<template>
  <div class="gen-image-node" :class="{ 'is-active': isActive }">
    <!-- 左侧输入连线点（target） -->
    <Handle type="target" :position="Position.Left" class="gen-image-node__handle" />

    <ImageStage :image="data.image" :status="data.status" :index="data.index" @upload="onUpload" />

    <!-- 编辑态（节点被选中）才显示工具栏与输入区 -->
    <template v-if="isActive">
      <NodeToolbar
        :mode="mode"
        :model="model"
        :size="size"
        @update:mode="mode = $event"
        @update:model="model = $event"
        @update:size="size = $event"
        @edit="onEdit"
      />

      <!-- 存在上游节点时，在工具栏与输入区之间展示 -->
      <UpstreamPanel v-if="upstreamNodes.length" :nodes="upstreamNodes" />

      <PromptPanel v-model="prompt" @generate="onGenerate" />
    </template>

    <!-- 右侧输出连线点（source） -->
    <Handle type="source" :position="Position.Right" class="gen-image-node__handle" />
  </div>
</template>

<style scoped>
.gen-image-node {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 450px;
  height: 500px;
  color: var(--text, #e9edf5);
  background: var(--surface, #151922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: 12px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5);
  font-size: 13px;
  line-height: 1.4;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.gen-image-node.is-active {
  border-color: var(--accent, #f0a63d);
  box-shadow: 0 18px 44px rgba(240, 166, 61, 0.18);
}

/* 这里不能用 overflow: hidden（会把两侧连线点裁掉），
   改由首/末子元素补偿圆角，保持圆角卡片外观 */
.gen-image-node > .image-stage {
  border-top-left-radius: 11px;
  border-top-right-radius: 11px;
}

.gen-image-node:not(.is-active) > .image-stage {
  border-bottom-left-radius: 11px;
  border-bottom-right-radius: 11px;
}

.gen-image-node > .prompt-panel {
  border-bottom-left-radius: 11px;
  border-bottom-right-radius: 11px;
}

/* 左右连线点 */
.gen-image-node :deep(.gen-image-node__handle) {
  width: 10px;
  height: 10px;
  background: var(--accent, #f0a63d);
  border: 2px solid #0d1117;
  transition: box-shadow 0.15s ease;
}

.gen-image-node :deep(.vue-flow__handle-left.gen-image-node__handle) {
  left: 0;
  transform: translate(-50%, -50%);
}

.gen-image-node :deep(.vue-flow__handle-right.gen-image-node__handle) {
  right: 0;
  transform: translate(50%, -50%);
}

.gen-image-node :deep(.gen-image-node__handle:hover) {
  box-shadow: 0 0 0 4px rgba(240, 166, 61, 0.25);
}
</style>
