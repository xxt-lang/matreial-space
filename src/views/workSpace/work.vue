<script setup>
/**
 * 工作区根组件 / 画布宿主页面
 * - vue-flow 画布全屏铺满
 * - 画布空白处右键 → 弹出上下文菜单（生图 / 生成视频 / 生成地图）
 * - 选择「生图」→ 在落点创建 GenImageNode 节点
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { MarkerType, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import ResizableDialog from '../../components/ResizableDialog.vue'
import ContextMenu from './assistComponent/ContextMenu.vue'
import GenImageNode from './nodesComponent/GenImageNode/GenImageNode.vue'
import { createGeneration } from './api/gen.js'
import { DEFAULT_SCALE, SCALE_STEP, clampScale } from './nodesComponent/GenImageNode/component/nodeScale.js'
import { VUE_FLOW_SHORTCUT_PROPS, isAltPressed, preventBrowserZoom } from './shortcuts/index.js'

const { screenToFlowCoordinate, getSelectedNodes, updateNodeData } = useVueFlow()

/**
 * 多选节点（Ctrl 点击）的选择顺序
 * getSelectedNodes 返回的是 nodes 数组顺序，这里额外记录「选择先后」，
 * 供批量连线等需要按选择顺序处理的场景使用
 */
const selectionOrder = ref([])

watch(
  () => getSelectedNodes.value.map((node) => node.id),
  (ids) => {
    const kept = selectionOrder.value.filter((id) => ids.includes(id))
    const added = ids.filter((id) => !kept.includes(id))
    selectionOrder.value = [...kept, ...added]
  },
)

// 连线默认样式：终点（target 端）带箭头
const EDGE_OPTIONS = {
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 18,
    height: 18,
  },
}

const nodes = ref([])
const edges = ref([])

/** 节点序号自增计数（新建节点时分配，用于节点上显示编号） */
let nodeSeq = 0

// 右键菜单状态：屏幕坐标用于定位，画布坐标用于落点
const menu = ref({ visible: false, x: 0, y: 0, flowX: 0, flowY: 0 })

const MENU_ITEMS = [
  { key: 'image', label: '生图' },
  { key: 'video', label: '生成视频' },
  { key: 'map', label: '生成地图' },
]

// 菜单项 → vue-flow 节点类型（type 与 nodesComponent/ 下的文件夹同名）
// 「生成视频 / 生成地图」的节点组件尚未创建，暂用 vue-flow 默认节点占位
const NODE_TYPE = {
  image: 'GenImageNode',
  video: '',
  map: '',
}

// 各类型节点创建时的初始 data
// scale：节点缩放系数（1 = 设计尺寸，默认值为设计尺寸的一半，见 nodeScale.js）
// promptInputHeight：提示词文本域高度（0 = 默认两行），拖拽调节后由节点自行写回
const NODE_DEFAULT_DATA = {
  image: {
    prompt: '',
    mode: 'hd',
    size: 64,
    image: '',
    // status：idle 空闲 / generating 生成中 / done 成功 / error 失败
    status: 'idle',
    error: '',
    scale: DEFAULT_SCALE,
    promptInputHeight: 0,
  },
}

function openMenu(event) {
  event.preventDefault()
  const [x, y] = [event.clientX, event.clientY]
  const pos = screenToFlowCoordinate({ x, y })
  menu.value = { visible: true, x, y, flowX: pos.x, flowY: pos.y }
}

function closeMenu() {
  menu.value.visible = false
}

async function onMenuSelect(key) {
  const { flowX, flowY } = menu.value
  closeMenu()
  if (!MENU_ITEMS.some(i => i.key === key)) return
  await nextTick()
  nodes.value.push({
    id: `${key}-${Date.now()}`,
    type: NODE_TYPE[key] || 'default',
    position: { x: flowX, y: flowY },
    data: {
      kind: key,
      index: ++nodeSeq,
      label: MENU_ITEMS.find(i => i.key === key)?.label,
      ...(NODE_DEFAULT_DATA[key] || {}),
    },
  })
}

// 拖线开始时快照「Ctrl 多选」的节点，用于批量连线
let batchSourceIds = []

function onConnectStart() {
  const selectedIds = getSelectedNodes.value.map((node) => node.id)
  // 以「Ctrl 选择顺序」为准排序；未记录到顺序的选中节点追加在后面
  const ordered = selectionOrder.value.filter((id) => selectedIds.includes(id))
  const rest = selectedIds.filter((id) => !ordered.includes(id))
  batchSourceIds = [...ordered, ...rest]
}

/** 连线去重键：同一对「上游 → 下游」只允许存在一条连线 */
function edgeKey(source, target) {
  return `${source}->${target}`
}

/**
 * 连线校验
 * - 拖拽过程中实时调用：不允许自环、不允许重复连线
 * - vue-flow 还会在用 createGraphEdges 重算整份连线时调用它校验「已存在」的连线，
 *   所以必须排除正在校验的这条边自身（按 id），否则每次新增连线都会把旧连线判成重复而丢弃
 */
function isValidConnection({ id, source, target }, { edges: currentEdges }) {
  if (!source || !target || source === target) return false
  return !currentEdges.some(
    (edge) => edge.id !== id && edge.source === source && edge.target === target,
  )
}

// 节点连线：vue-flow 默认 autoConnect 为 false，这里手动把连接写入 edges
function onConnect(connection) {
  const { source, target, sourceHandle, targetHandle } = connection
  if (!source || !target) return

  const stamp = Date.now()
  const batch = []
  // 已存在的连线 + 本批已生成的连线，统一用于去重
  const taken = new Set(edges.value.map((edge) => edgeKey(edge.source, edge.target)))

  /** 追加一条「id → target」的连线：自环或已链接过则跳过 */
  function pushEdge(id) {
    if (!id || id === target) return
    const key = edgeKey(id, target)
    if (taken.has(key)) return
    taken.add(key)
    batch.push({
      id: `edge-${id}-${target}-${stamp}-${batch.length}`,
      source: id,
      target,
      sourceHandle,
      targetHandle,
    })
  }

  pushEdge(source)

  // 多选后从其中一个节点拉线：其余选中节点用相同位置的连接点连到同一目标
  if (batchSourceIds.length > 1 && batchSourceIds.includes(source)) {
    // 起点自身由上面处理；这里只跳过「已连到该目标」的选中节点，避免重复连线
    batchSourceIds.filter((id) => id !== source).forEach(pushEdge)
  }

  if (batch.length) edges.value.push(...batch)
  batchSourceIds = []
}

/** 编辑弹窗状态：visible 控制显隐，id / data 为当前编辑的节点（data 是响应式引用，内容会跟着节点更新） */
const editDialog = ref({ visible: false, id: '', data: null })

// 节点「编辑」回调：打开编辑弹窗（面板内容待接入）
function onNodeEdit({ id, data }) {
  editDialog.value = { visible: true, id, data }
}

/**
 * 每个节点正在进行的生成任务（nodeId → AbortController）
 * 既用于「中断」，也用于挡住重复提交（生成中再次提交直接忽略）
 */
const genControllers = new Map()

// 节点「生成」回调：调用 api/ 接口层，并按响应更新节点的 data.status / data.image
// payload.setting：工具栏配置（model / mode / size）；payload.text：提示词文本
async function onNodeGenerate(payload) {
  const { id } = payload
  // 生成中重复提交直接忽略（此时按钮已变为「中断」）
  if (genControllers.has(id)) return

  const controller = new AbortController()
  genControllers.set(id, controller)
  // 进入生成中：图片区的加载态在折叠状态下同样展示
  updateNodeData(id, { status: 'generating', error: '' })

  try {
    const { image } = await createGeneration(payload, { signal: controller.signal })
    // 成功：取消加载中并展示结果
    updateNodeData(id, { status: 'done', image })
  } catch (error) {
    if (error?.name === 'AbortError') {
      // 中断：取消加载中，保留已有图片
      updateNodeData(id, { status: 'idle' })
    } else {
      // 失败：同样取消加载中，并把错误信息交给节点展示
      updateNodeData(id, { status: 'error', error: error?.message || '生成失败' })
    }
  } finally {
    genControllers.delete(id)
  }
}

// 节点「中断生成」回调：中止该节点正在进行的生成任务
function onNodeAbort({ id }) {
  genControllers.get(id)?.abort()
}

// 节点「上传图片」回调：图片已由节点本地以 dataURL 展示
function onNodeUpload({ id, name, type, size }) {
  // TODO: 调用 api/ 上传接口，成功后将节点的 data.image 替换为返回的远程地址
}

// 画布容器：屏蔽浏览器「Ctrl / ⌘ + 滚轮」的整页缩放
const workspaceRef = ref(null)
let stopWheelGuard = null

/**
 * Alt + 滚轮：缩放「当前唯一选中的节点」
 * - 只有恰好选中一个节点时生效；滚轮向上放大、向下缩小，结果写回该节点 data.scale
 * - 监听挂在画布容器并走捕获阶段：命中后阻止冒泡，避免同时触发画布自身的滚轮行为
 */
function onWheelZoomNode(event) {
  if (!isAltPressed(event)) return
  const selected = getSelectedNodes.value
  if (selected.length !== 1) return
  const [node] = selected
  // 仅支持带缩放能力的节点类型（当前只有生图节点）
  if (node.type !== NODE_TYPE.image) return

  event.preventDefault()
  event.stopPropagation()

  const current = clampScale(node.data?.scale ?? DEFAULT_SCALE)
  const next = clampScale(current + (event.deltaY < 0 ? SCALE_STEP : -SCALE_STEP))
  if (next !== current) updateNodeData(node.id, { scale: next })
}

onMounted(() => {
  if (!workspaceRef.value) return
  stopWheelGuard = preventBrowserZoom(workspaceRef.value)
  workspaceRef.value.addEventListener('wheel', onWheelZoomNode, { capture: true, passive: false })
})

onBeforeUnmount(() => {
  stopWheelGuard?.()
  workspaceRef.value?.removeEventListener('wheel', onWheelZoomNode, { capture: true })
})

// 自身节点也屏蔽浏览器原生菜单（pane 之外的区域）
function preventNativeMenu(e) {
  e.preventDefault()
}
</script>

<template>
  <div ref="workspaceRef" class="work-space" @contextmenu="preventNativeMenu">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      class="work-space__flow"
      :min-zoom="0.2"
      :max-zoom="2.5"
      :default-viewport="{ zoom: 1 }"
      :default-edge-options="EDGE_OPTIONS"
      :is-valid-connection="isValidConnection"
      v-bind="VUE_FLOW_SHORTCUT_PROPS"
      @pane-context-menu="openMenu"
      @pane-click="closeMenu"
      @move-start="closeMenu"
      @connect-start="onConnectStart"
      @connect="onConnect"
    >
      <!-- 生图节点：自定义节点组件 -->
      <template #node-GenImageNode="nodeProps">
        <GenImageNode
          v-bind="nodeProps"
          @edit="onNodeEdit"
          @generate="onNodeGenerate"
          @abort="onNodeAbort"
          @upload="onNodeUpload"
        />
      </template>
    </VueFlow>

    <ContextMenu
      :x="menu.x"
      :y="menu.y"
      :visible="menu.visible"
      :items="MENU_ITEMS"
      @select="onMenuSelect"
      @close="closeMenu"
    />

    <!-- 节点编辑弹窗：内容待接入，先展示节点当前数据 -->
    <ResizableDialog
      v-model="editDialog.visible"
      :title="editDialog.data?.index ? `编辑节点 #${editDialog.data.index}` : '编辑节点'"
      :width="560"
      :height="420"
    >
      <p class="edit-panel__hint">编辑面板内容待接入，当前节点数据如下：</p>

      <dl class="edit-panel__list">
        <div class="edit-panel__row">
          <dt>节点 ID</dt>
          <dd>{{ editDialog.id }}</dd>
        </div>
        <div class="edit-panel__row">
          <dt>类型</dt>
          <dd>{{ editDialog.data?.label || '-' }}</dd>
        </div>
        <div class="edit-panel__row">
          <dt>模式</dt>
          <dd>{{ editDialog.data?.mode === 'perfect' ? '完美像素画' : '高清像素画' }}</dd>
        </div>
        <div class="edit-panel__row">
          <dt>模型</dt>
          <dd>{{ editDialog.data?.model || '默认模型' }}</dd>
        </div>
        <div class="edit-panel__row">
          <dt>尺寸</dt>
          <dd>{{ editDialog.data?.size }}×{{ editDialog.data?.size }}</dd>
        </div>
      </dl>

      <p class="edit-panel__prompt">{{ editDialog.data?.prompt || '（提示词为空）' }}</p>

      <template #footer>
        <button class="edit-panel__btn" type="button" @click="editDialog.visible = false">
          关闭
        </button>
      </template>
    </ResizableDialog>
  </div>
</template>

<style scoped>
.work-space {
  position: relative;
  flex: 1;
  min-width: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: var(--bg-deep, #090a0e);
  /* 点阵网格底纹 */
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.07) 1px, transparent 1px);
  background-size: 22px 22px;
}

/* 让 vue-flow 铺满宿主，并露出宿主网格底纹。
   用绝对定位而非 height:100%，避免父级高度非确定值时百分比高度失效导致画布塌成 0 */
.work-space :deep(.vue-flow) {
  position: absolute;
  inset: 0;
  background: transparent;
}

.work-space :deep(.vue-flow__pane) {
  background: transparent;
}

/* 自定义节点容器：去掉 vue-flow 默认外观，尺寸完全由节点组件决定 */
.work-space :deep(.vue-flow__node-GenImageNode) {
  padding: 0;
  width: auto;
  font-size: inherit;
  color: inherit;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 0;
}

/* ---------------- 编辑弹窗内容（面板待接入，先展示节点数据） ---------------- */

.edit-panel__hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--muted, #767f92);
}

.edit-panel__list {
  display: grid;
  gap: 6px;
  margin: 0;
}

.edit-panel__row {
  display: flex;
  gap: 12px;
  font-size: 13px;
}

.edit-panel__row dt {
  flex: none;
  width: 72px;
  color: var(--muted, #767f92);
}

.edit-panel__row dd {
  min-width: 0;
  margin: 0;
  word-break: break-all;
}

.edit-panel__prompt {
  margin: 12px 0 0;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  background: #0f131a;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
}

.edit-panel__btn {
  padding: 7px 18px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border: none;
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.edit-panel__btn:hover {
  opacity: 0.88;
}
</style>
