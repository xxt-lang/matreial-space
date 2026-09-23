<script setup>
/**
 * 生图节点（vue-flow 自定义节点，type = GenImageNode）
 *
 * 设计尺寸 450×500（高度会随提示词文本域高度变化），纵向三段式：
 *   上：图片展示区（支持本地上传 / 更换）
 *   中：工具栏（完美像素画 / 高清像素画 / 模型选择 / 尺寸选择 / 编辑）
 *   下：提示词输入 + 生成按钮（节点被选中时展开）
 *
 * 节点整体支持等比缩放（data.scale）：新建节点默认 0.5（设计尺寸的一半），
 * 选中单个节点后按住 Alt 滚动滚轮即可放大 / 缩小（见 work.vue），
 * 缩放不影响内部布局，仅整体等比缩放显示，顶部居中显示当前比例。
 *
 * 画布交互：通过 useVueFlow() 读写节点数据；左右两侧带 vue-flow 连线点；
 * 生成 / 编辑 / 上传动作 emit 给宿主（work.vue），由宿主决定是否调用 api/ 接口层。
 */
import { computed, ref, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import ImageStage from './component/ImageStage.vue'
import NodeToolbar from './component/NodeToolbar.vue'
import UpstreamPanel from './component/UpstreamPanel.vue'
import PromptInput from '../../assistComponent/PromptInput.vue'
import { DEFAULT_MODEL } from './component/modelOptions.js'
import { DEFAULT_SCALE, clampScale } from './component/nodeScale.js'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
})

const emit = defineEmits(['edit', 'generate', 'upload'])

const { updateNodeData, getSelectedNodes, getNodes, getEdges, removeEdges } = useVueFlow()

/** 节点被选中（点击）时进入编辑态，展开工具栏与输入区 */
const isActive = computed(() => getSelectedNodes.value.some((n) => n.id === props.id))

/** 通过连线指向当前节点的上游节点 */
const upstreamNodes = computed(() => {
  const sourceIds = getEdges.value
    .filter((e) => e.target === props.id && e.source !== props.id)
    .map((e) => e.source)
  if (!sourceIds.length) return []
  // 按连线顺序（即批量创建顺序）排列，保持与上游节点的选择顺序一致
  return sourceIds
    .map((id) => getNodes.value.find((n) => n.id === id))
    .filter(Boolean)
})

const prompt = ref(props.data.prompt ?? '')
/** 模型标识 */
const model = ref(props.data.model ?? DEFAULT_MODEL)
/** hd = 高清像素画，perfect = 完美像素画 */
const mode = ref(props.data.mode ?? 'hd')
/** 像素画边长 */
const size = ref(props.data.size ?? 64)

/** 节点设计尺寸（scale = 1 时的像素尺寸） */
const BASE_WIDTH = 450
const BASE_HEIGHT = 500

/**
 * 节点缩放系数
 * 由节点 data 驱动（选中单个节点后 Alt + 滚轮调整，见 work.vue），节点自身不持有状态。
 * 实现方式：外层容器按「设计尺寸 × scale」占位（vue-flow 测量到的节点尺寸即视觉尺寸，
 * 保证连线端点、框选、fitView 都准确）；内层节点仍按设计尺寸布局，再整体 transform: scale。
 * 这样缩放不会挤压内部工具栏 / 输入区，只是整体等比放大缩小。
 */
const scale = computed(() => clampScale(props.data.scale ?? DEFAULT_SCALE))

/**
 * 提示词面板当前高度 / 默认状态下的面板高度（设计像素）
 * 默认高度由 PromptInput 在应用已保存高度前测得，作为节点高度增量的基准
 */
const promptHeight = ref(0)
const promptBaseHeight = ref(0)

/** 节点内层高度 = 设计高度 + 文本域带来的高度增量（图片区尺寸保持不变） */
const nodeHeight = computed(() => {
  const delta = promptBaseHeight.value ? promptHeight.value - promptBaseHeight.value : 0
  return BASE_HEIGHT + delta
})

/** 已保存的文本域高度（重新进入编辑态时按它恢复） */
const savedPromptHeight = computed(() => props.data.promptInputHeight ?? 0)

/**
 * 提示词面板尺寸变化（首次挂载 / 拖拽调节文本域高度）
 * - 刷新节点高度增量
 * - 把文本域高度写回节点 data，保证再次编辑时高度不变
 */
function onPromptResize({ panel, base, input }) {
  promptBaseHeight.value = base
  promptHeight.value = panel
  if (input && input !== savedPromptHeight.value) {
    updateNodeData(props.id, { promptInputHeight: input })
  }
}

const wrapStyle = computed(() => ({
  width: `${BASE_WIDTH * scale.value}px`,
  height: `${nodeHeight.value * scale.value}px`,
}))

const nodeStyle = computed(() => ({
  width: `${BASE_WIDTH}px`,
  height: `${nodeHeight.value}px`,
  transform: `scale(${scale.value})`,
}))

const scaleText = computed(() => `${Math.round(scale.value * 100)}%`)

watch(prompt, (v) => updateNodeData(props.id, { prompt: v }))
watch(model, (v) => updateNodeData(props.id, { model: v }))
watch(mode, (v) => updateNodeData(props.id, { mode: v }))
watch(size, (v) => updateNodeData(props.id, { size: v }))

function onEdit() {
  emit('edit', { id: props.id, data: props.data })
}

/** 删除「上游节点 → 当前节点」这条连线 */
function onRemoveUpstream(sourceId) {
  const edge = getEdges.value.find((e) => e.source === sourceId && e.target === props.id)
  if (edge) removeEdges([edge.id])
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
  <!-- 外层容器：尺寸 = 设计尺寸 × scale，连线点挂在这里，位置始终与节点实际大小一致 -->
  <div
    class="gen-image-node-wrap"
    :class="{ 'is-active': isActive }"
    :style="wrapStyle"
  >
    <!-- 左侧输入连线点（target） -->
    <Handle type="target" :position="Position.Left" class="gen-image-node__handle" />

    <!-- 缩放比例提示（只读）：缩放由「选中单个节点 + Alt + 滚轮」触发 -->
    <span class="gen-image-node__scale">{{ scaleText }}</span>

    <!-- 内层节点：始终按设计尺寸布局，整体等比缩放 -->
    <div class="gen-image-node" :class="{ 'is-active': isActive }" :style="nodeStyle">
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
        <UpstreamPanel
          v-if="upstreamNodes.length"
          :nodes="upstreamNodes"
          @remove="onRemoveUpstream"
        />

        <PromptInput
          v-model="prompt"
          :height="savedPromptHeight"
          placeholder="描述画面，例如：赛博朋克风格的猫"
          @submit="onGenerate"
          @resize="onPromptResize"
        />
      </template>
    </div>

    <!-- 右侧输出连线点（source） -->
    <Handle type="source" :position="Position.Right" class="gen-image-node__handle" />
  </div>
</template>

<style scoped>
/* 外层容器：尺寸由内联样式按缩放系数计算，代表节点在画布上的真实占位 */
.gen-image-node-wrap {
  position: relative;
  transition: width 0.15s ease, height 0.15s ease;
}

.gen-image-node {
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  flex-direction: column;
  /* width / height / transform 由内联样式给出（设计尺寸 × scale） */
  transform-origin: top left;
  color: var(--text, #e9edf5);
  background: var(--surface, #151922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: 12px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5);
  font-size: 13px;
  line-height: 1.4;
  /* height 与外层容器同步过渡，避免拖拽调节文本域高度时内外尺寸短暂错位 */
  transition: height 0.15s ease, transform 0.15s ease, border-color 0.15s ease,
    box-shadow 0.15s ease;
}

/* 缩放比例提示：贴节点右上角，悬停或选中时显示；
   不可交互，缩放由「选中单个节点 + Alt + 滚轮」触发 */
.gen-image-node__scale {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
  padding: 1px 8px;
  font-size: 11px;
  line-height: 16px;
  color: var(--muted, #767f92);
  background: rgba(13, 17, 23, 0.82);
  border: 1px solid var(--border2, #343c4c);
  border-radius: 999px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.gen-image-node-wrap:hover .gen-image-node__scale,
.gen-image-node-wrap.is-active .gen-image-node__scale {
  opacity: 1;
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

.gen-image-node > .prompt-input {
  border-bottom-left-radius: 11px;
  border-bottom-right-radius: 11px;
}

/* 左右连线点：挂在外层容器上，位置随节点实际（缩放后）尺寸变化 */
.gen-image-node-wrap :deep(.gen-image-node__handle) {
  width: 10px;
  height: 10px;
  background: var(--accent, #f0a63d);
  border: 2px solid #0d1117;
  transition: box-shadow 0.15s ease;
}

.gen-image-node-wrap :deep(.vue-flow__handle-left.gen-image-node__handle) {
  left: 0;
  transform: translate(-50%, -50%);
}

.gen-image-node-wrap :deep(.vue-flow__handle-right.gen-image-node__handle) {
  right: 0;
  transform: translate(50%, -50%);
}

.gen-image-node-wrap :deep(.gen-image-node__handle:hover) {
  box-shadow: 0 0 0 4px rgba(240, 166, 61, 0.25);
}
</style>
