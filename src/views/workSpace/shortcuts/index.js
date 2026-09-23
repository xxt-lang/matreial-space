/**
 * 画布平台快捷键 —— 统一管理
 *
 * 约定：
 * 1. 所有快捷键的键位只在本目录定义，页面 / 节点组件不得散落硬编码；
 * 2. 需要 vue-flow 内部识别的键位，统一由 VUE_FLOW_SHORTCUT_PROPS 导出，
 *    在 <VueFlow v-bind="VUE_FLOW_SHORTCUT_PROPS"> 一次性注入；
 * 3. SHORTCUTS 同时作为快捷键帮助面板的数据源（含文案与键位显示）。
 */
import { MOD, formatKeys } from './keys.js'

export { IS_MAC, MOD, formatKeys, isModPressed } from './keys.js'

const SHIFT = 'Shift'
const SPACE = 'Space'
const DELETE_KEYS = ['Backspace', 'Delete']

/**
 * 快捷键清单
 * - keys：用于显示（与 keys.js 的 formatKeys 配合）
 * - title / description：帮助面板文案
 */
export const SHORTCUTS = [
  {
    id: 'multiSelect',
    keys: [MOD, 'click'],
    title: '多选节点 / 连线',
    description: '按住修饰键点击节点或连线，可累加选中多个；再次点击已选中的元素则取消它',
  },
  {
    id: 'boxSelect',
    keys: [SHIFT, 'drag'],
    title: '框选',
    description: '按住 Shift 在画布空白处拖拽，框选范围内的节点',
  },
  {
    id: 'pan',
    keys: ['drag'],
    title: '平移画布',
    description: `在画布空白处按住鼠标拖拽；或按住 ${formatKeys([SPACE])} 后拖拽`,
  },
  {
    id: 'zoom',
    keys: ['wheel'],
    title: '缩放画布',
    description: `滚轮缩放；按住 ${formatKeys([MOD])} 时滚轮改为平移`,
  },
  {
    id: 'remove',
    keys: DELETE_KEYS,
    title: '删除所选',
    description: '删除当前选中的节点与连线',
  },
]

/**
 * 交由 <VueFlow> 识别的快捷键配置
 * 在画布上一次性注入，保证快捷键只在 shortcuts/ 里维护
 */
export const VUE_FLOW_SHORTCUT_PROPS = {
  /** 多选（节点 / 连线）：Ctrl 或 ⌘ */
  multiSelectionKeyCode: MOD,
  /** 框选：Shift */
  selectionKeyCode: SHIFT,
  /** 删除所选：Backspace / Delete */
  deleteKeyCode: DELETE_KEYS,
  /** 平移激活键：Space */
  panActivationKeyCode: SPACE,
  /** 缩放激活键：Ctrl 或 ⌘ */
  zoomActivationKeyCode: MOD,
}

/** 按 id 取快捷键定义（复用键位文案时使用） */
export function getShortcut(id) {
  return SHORTCUTS.find((item) => item.id === id) ?? null
}
