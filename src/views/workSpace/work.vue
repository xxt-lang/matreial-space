<script setup>
/**
 * 工作区根组件 / 画布宿主页面
 * - vue-flow 画布全屏铺满
 * - 画布空白处右键 → 弹出上下文菜单（生图 / 生成视频 / 生成地图）
 */
import { nextTick, ref } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import ContextMenu from './assistComponent/ContextMenu.vue'

const { screenToFlowCoordinate } = useVueFlow()

const nodes = ref([])
const edges = ref([])

// 右键菜单状态：屏幕坐标用于定位，画布坐标用于落点
const menu = ref({ visible: false, x: 0, y: 0, flowX: 0, flowY: 0 })

const MENU_ITEMS = [
  { key: 'image', label: '生图' },
  { key: 'video', label: '生成视频' },
  { key: 'map', label: '生成地图' },
]

// 节点类型占位映射：后续接入 nodesComponent/<NodeType> 组件时替换为真实 type
const NODE_TYPE = {
  image: 'genImage',
  video: 'genVideo',
  map: 'genMap',
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
  if (!NODE_TYPE[key]) return
  await nextTick()
  // TODO: 接入 nodesComponent/<NodeType> 后，将 type 换为对应自定义节点组件
  nodes.value.push({
    id: `${key}-${Date.now()}`,
    type: 'default',
    position: { x: flowX, y: flowY },
    data: { kind: key, label: MENU_ITEMS.find(i => i.key === key)?.label },
  })
}

// 自身节点也屏蔽浏览器原生菜单（pane 之外的区域）
function preventNativeMenu(e) {
  e.preventDefault()
}
</script>

<template>
  <div class="work-space" @contextmenu="preventNativeMenu">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      class="work-space__flow"
      :min-zoom="0.2"
      :max-zoom="2.5"
      :default-viewport="{ zoom: 1 }"
      @pane-context-menu="openMenu"
      @pane-click="closeMenu"
      @move-start="closeMenu"
    />

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
</style>
