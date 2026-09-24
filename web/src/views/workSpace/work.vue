<script setup>
/**
 * 工作区根组件 / 画布宿主页面
 * - vue-flow 画布全屏铺满
 * - 画布空白处右键 → 弹出上下文菜单（生图 / 生成视频 / 生成地图）
 * - 选择「生图」→ 在落点创建 GenImageNode 节点
 * - 顶部中间悬浮胶囊：展示当前工作空间名称（取自路由参数 /workspace/:workspaceId），可收起 / 展开
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MarkerType, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import PixelEditor from '../../components/PixelEditor/PixelEditor.vue'
import ResizableDialog from '../../components/ResizableDialog.vue'
import ContextMenu from './assistComponent/ContextMenu.vue'
import GenImageNode from './nodesComponent/GenImageNode/GenImageNode.vue'
import { fetchWorkspace } from '../../api/workspace'
import { createGeneration } from './api/gen.js'
import { DEFAULT_SCALE, SCALE_STEP, clampScale } from './nodesComponent/GenImageNode/component/nodeScale.js'
import { VUE_FLOW_SHORTCUT_PROPS, isAltPressed, preventBrowserZoom } from './shortcuts/index.js'

const { screenToFlowCoordinate, flowToScreenCoordinate, getNodes, getSelectedNodes, updateNodeData } =
  useVueFlow()

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

function onConnectStart(connecting) {
  const selectedIds = getSelectedNodes.value.map((node) => node.id)
  // 以「Ctrl 选择顺序」为准排序；未记录到顺序的选中节点追加在后面
  const ordered = selectionOrder.value.filter((id) => selectedIds.includes(id))
  const rest = selectedIds.filter((id) => !ordered.includes(id))
  batchSourceIds = [...ordered, ...rest]
  startBatchPreview(connecting)
}

/* ---------------- 批量连线预览 ---------------- */

/** 批量连线预览的连线路径（画布容器屏幕坐标系的 SVG path） */
const previewPaths = ref([])

/** 结束预览的清理函数（拖拽中为函数，未拖拽时为 null） */
let stopBatchPreview = null

/** 结束批量连线预览（拖拽结束、组件卸载时调用） */
function endBatchPreview() {
  stopBatchPreview?.()
}

/** 与 vue-flow 默认连线一致的贝塞尔路径 */
function bezierPath(from, to) {
  const curve = Math.abs(to.x - from.x) * 0.5
  return `M ${from.x},${from.y} C ${from.x + curve},${from.y} ${to.x - curve},${to.y} ${to.x},${to.y}`
}

/**
 * 开始批量连线预览
 * Ctrl 多选后从其中一个节点的输出点起拖时，把其余选中节点的连线也画出来，
 * 让「这些节点都会连过去」在拖拽过程中就可见（落点确认逻辑仍由 onConnect 负责）
 */
function startBatchPreview(connecting) {
  const container = workspaceRef.value
  const from = connecting?.nodeId
  // 只有「从选中节点的输出点起拖」且还有别的选中节点时才需要预览
  if (!container || connecting?.handleType !== 'source' || !batchSourceIds.includes(from)) return

  const others = batchSourceIds.filter((id) => id !== from)
  if (!others.length) return

  // 拖拽过程中容器不会移动，边界算一次即可
  const rect = container.getBoundingClientRect()

  function onPointerMove(event) {
    const pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top }
    previewPaths.value = others
      .map((id) => getNodes.value.find((node) => node.id === id))
      .filter(Boolean)
      .map((node) => {
        // 输出点在节点右侧、垂直居中（与节点上 Handle 的位置一致）
        const anchor = flowToScreenCoordinate({
          x: node.position.x + (node.dimensions?.width ?? 0),
          y: node.position.y + (node.dimensions?.height ?? 0) / 2,
        })
        return bezierPath(anchor, pointer)
      })
  }

  function cleanup() {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', cleanup)
    window.removeEventListener('pointercancel', cleanup)
    previewPaths.value = []
    stopBatchPreview = null
  }

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', cleanup)
  window.addEventListener('pointercancel', cleanup)
  stopBatchPreview = cleanup
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

// 节点「编辑」回调：打开像素画编辑弹窗
function onNodeEdit({ id, data }) {
  editDialog.value = { visible: true, id, data }
}

/** 像素画编辑器「应用到节点」：把 PNG dataURL 写回节点，图片区直接展示 */
function onPixelApply(image) {
  if (!editDialog.value.id) return
  updateNodeData(editDialog.value.id, { image })
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

/* ---------------- 当前工作空间名称（画布上方悬浮胶囊） ---------------- */

const route = useRoute()
const router = useRouter()

/** 当前工作空间 id：从工作空间列表双击进入时由路由参数带上；直接进画布时为空 */
const workspaceId = computed(() => String(route.params.workspaceId || ''))

const workspaceName = ref('')
const nameError = ref('')

/** 用户点「隐藏」后的收起状态：向上收成画布顶部的一个小角 */
const collapsed = ref(false)
/** 鼠标是否停在胶囊（含收起后的小角）上 */
const hovered = ref(false)
/** 实际呈现：收起之后，鼠标悬浮小角会临时展开（纯展示状态，不写 node.data，也不落库） */
const isCollapsed = computed(() => collapsed.value && !hovered.value)

/** 「隐藏 / 显示」：切换收起状态 */
function toggleBadge() {
  collapsed.value = !collapsed.value
  // 收起时把悬浮状态一并复位：否则鼠标还停在原地，收起后会被判定为「正在悬浮」又立刻展开
  hovered.value = false
}

/** 名称左侧的返回按钮：回工作空间列表 */
function goBackToList() {
  router.push({ name: 'workspace-manage' })
}

/** 展示文案：未指定 / 加载中 / 加载失败都有兜底，不让胶囊空着 */
const badgeText = computed(() => {
  if (!workspaceId.value) return '未指定工作空间'
  if (nameError.value) return nameError.value
  return workspaceName.value || '加载中…'
})

let nameController = null

async function loadWorkspaceName() {
  nameController?.abort()
  workspaceName.value = ''
  nameError.value = ''

  if (!workspaceId.value) return

  const controller = new AbortController()
  nameController = controller

  try {
    const workspace = await fetchWorkspace(workspaceId.value, { signal: controller.signal })
    workspaceName.value = workspace?.name || '未命名工作空间'
  } catch (error) {
    if (error?.name === 'AbortError') return
    // not_found：该工作空间已被删除；其它情况（后端不可用等）统一兜底
    nameError.value = error?.code === 'not_found' ? '工作空间不存在' : '名称加载失败'
  } finally {
    if (nameController === controller) nameController = null
  }
}

// 同一个组件会在不同 /workspace/:id 之间复用，id 变了要重新取名称
watch(workspaceId, loadWorkspaceName)

onMounted(loadWorkspaceName)

onBeforeUnmount(() => {
  nameController?.abort()
})

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
  endBatchPreview()
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
      @connect-end="endBatchPreview"
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

    <!-- 当前工作空间名称：悬浮在画布上方中部。
         点「隐藏」向上收成画布顶部的一个小角，鼠标悬浮小角再展开。
         nokey：vue-flow 的按键快捷键（Delete 等）忽略这里的按键 -->
    <div
      class="work-space__badge nokey"
      :class="{ 'is-collapsed': isCollapsed }"
      @mouseenter="hovered = true"
      @mouseleave="hovered = false"
    >
      <button
        class="work-space__badge-icon"
        type="button"
        title="返回工作空间列表"
        aria-label="返回工作空间列表"
        @click="goBackToList"
      >
        ←
      </button>

      <span class="work-space__badge-text" :title="badgeText">{{ badgeText }}</span>

      <button
        class="work-space__badge-btn"
        type="button"
        :title="collapsed ? '保持展开' : '向上收起'"
        @click="toggleBadge"
      >
        {{ collapsed ? '显示' : '隐藏' }}
      </button>
    </div>

    <!-- 批量连线预览：Ctrl 多选后拖线时，其余选中节点的连线一并展示（虚线，不接收指针事件） -->
    <svg v-if="previewPaths.length" class="work-space__preview" aria-hidden="true">
      <path v-for="(path, index) in previewPaths" :key="index" :d="path" />
    </svg>

    <ContextMenu
      :x="menu.x"
      :y="menu.y"
      :visible="menu.visible"
      :items="MENU_ITEMS"
      @select="onMenuSelect"
      @close="closeMenu"
    />

    <!-- 节点编辑弹窗：像素画编辑器。编辑结果通过「应用到节点」写回 data.image，
         所以这里没有 footer —— 操作按钮都在编辑器自己的底栏里 -->
    <ResizableDialog
      v-model="editDialog.visible"
      :title="editDialog.data?.index ? `编辑节点 #${editDialog.data.index}` : '编辑节点'"
      :width="820"
      :height="660"
      :close-on-click-modal="false"
    >
      <PixelEditor
        :image="editDialog.data?.image || ''"
        :size="editDialog.data?.size || 64"
        @apply="onPixelApply"
      />
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

/* 当前工作空间名称：悬浮在画布上方中部，不参与画布布局 */
.work-space__badge {
  position: absolute;
  /* 贴着画布上边缘，不能留空隙：否则收起后的小角会落在展开态盒子之外，
     悬浮小角时会在「展开 → 光标落在盒子外 → 收起」之间来回抖动 */
  top: 0;
  left: 50%;
  z-index: 6;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: min(70%, 520px);
  padding: 5px;
  font-size: 12px;
  color: var(--fg, #e9edf5);
  background: rgba(20, 25, 34, 0.82);
  border: 1px solid var(--border2, #343c4c);
  border-radius: 999px;
  box-shadow: var(--shadow-lg, 0 12px 32px rgba(0, 0, 0, 0.45));
  backdrop-filter: blur(6px);
  /* 展开态也写成完整的函数列表，和收起态的 transform 一一对应，过渡才不会走矩阵插值 */
  transform: translate(-50%, 0) scaleX(1);
  transition: transform 0.22s ease;
}

/*
  收起：向上移到画布顶边之外，只留底部 10px 露出来当「小角」。
  关键点：残留的小角必须落在展开态的盒子里（y ∈ [0, 高度]），所以 top 得是 0，
  否则悬浮小角触发展开后，光标在盒子外会立刻触发 mouseleave 又收起，来回抖动。
  超出画布的部分由 .work-space 的 overflow: hidden 裁掉；
  scaleX 让残留的小角变窄（此时内容已经淡出，不影响观感），悬浮它即可展开。
*/
.work-space__badge.is-collapsed {
  transform: translate(-50%, calc(-100% + 10px)) scaleX(0.34);
}

/* 收起后只看得到胶囊的底边：内容淡出且不可点 */
.work-space__badge.is-collapsed > * {
  opacity: 0;
  pointer-events: none;
}

.work-space__badge-text {
  max-width: 320px;
  padding: 0 2px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  transition: opacity 0.15s ease;
}

/* 名称左侧的返回按钮 */
.work-space__badge-icon {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  font: inherit;
  font-size: 13px;
  line-height: 1;
  color: var(--muted, #767f92);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 50%;
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    opacity 0.15s ease;
}

.work-space__badge-icon:hover {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.work-space__badge-btn {
  flex: none;
  padding: 3px 10px;
  font: inherit;
  font-size: 11px;
  color: var(--muted, #767f92);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    opacity 0.15s ease;
}

.work-space__badge-btn:hover {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

/* 批量连线预览：盖在画布上的虚线，只做展示，不接收指针事件 */
.work-space__preview {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}

.work-space__preview path {
  fill: none;
  stroke: var(--accent, #f0a63d);
  stroke-width: 1.5;
  stroke-dasharray: 5 4;
  opacity: 0.8;
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

/* 编辑弹窗的内容全部由 PixelEditor 自带样式，这里不再留节点数据的展示样式 */
</style>
