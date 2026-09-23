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
import ContextMenu from './assistComponent/ContextMenu.vue'
import GenImageNode from './nodesComponent/GenImageNode/GenImageNode.vue'
import { VUE_FLOW_SHORTCUT_PROPS, preventBrowserZoom } from './shortcuts/index.js'

const { screenToFlowCoordinate, getSelectedNodes } = useVueFlow()

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
const NODE_DEFAULT_DATA = {
  image: { prompt: '', mode: 'hd', size: 64, image: '', status: 'idle' },
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

// 节点连线：vue-flow 默认 autoConnect 为 false，这里手动把连接写入 edges
function onConnect(connection) {
  const { source, target, sourceHandle, targetHandle } = connection
  const stamp = Date.now()
  const batch = [{ ...connection, id: `edge-${source}-${target}-${stamp}` }]

  // 多选后从其中一个节点拉线：其余选中节点用相同位置的连接点连到同一目标
  if (batchSourceIds.length > 1 && batchSourceIds.includes(source)) {
    batchSourceIds
      // 排除起始节点自身与目标节点（其余选中节点恰好是目标时会产生自环）
      .filter((id) => id !== source && id !== target)
      .forEach((id, index) => {
        batch.push({
          id: `edge-${id}-${target}-${stamp}-${index}`,
          source: id,
          target,
          sourceHandle,
          targetHandle,
        })
      })
  }

  edges.value.push(...batch)
  batchSourceIds = []
}

// 节点「编辑」回调：待接入编辑面板
function onNodeEdit({ id }) {
  // TODO: 依据 id 打开该节点的编辑面板
}

// 节点「生成」回调：待接入 api/ 接口层
// setting：工具栏配置（model / mode / size）；text：提示词文本
function onNodeGenerate({ id, setting, text }) {
  // TODO: 调用 api/gen.js 的 createGeneration({ id, setting, text })，
  //       并按响应更新节点的 data.image / data.status
}

// 节点「上传图片」回调：图片已由节点本地以 dataURL 展示
function onNodeUpload({ id, name, type, size }) {
  // TODO: 调用 api/ 上传接口，成功后将节点的 data.image 替换为返回的远程地址
}

// 画布容器：屏蔽浏览器「Ctrl / ⌘ + 滚轮」的整页缩放
const workspaceRef = ref(null)
let stopWheelGuard = null

onMounted(() => {
  if (workspaceRef.value) stopWheelGuard = preventBrowserZoom(workspaceRef.value)
})

onBeforeUnmount(() => {
  stopWheelGuard?.()
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
</style>
