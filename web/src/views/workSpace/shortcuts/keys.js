/**
 * 画布快捷键基础键位
 *
 * 统一处理平台差异：macOS 的修饰键是 ⌘（Meta），其余平台是 Ctrl（Control）。
 * 所有快捷键定义都应从这里取键位，不要在组件里硬编码 'Control' / 'Meta'。
 */

export const IS_MAC =
  typeof navigator !== 'undefined' && /Mac|iPhone|iPad|iPod/.test(navigator.userAgent)

/** 平台修饰键：macOS 用 Meta，其他平台用 Control */
export const MOD = IS_MAC ? 'Meta' : 'Control'

/** 节点缩放修饰键：Alt */
export const ALT = 'Alt'

const LABELS = IS_MAC
  ? { Meta: '⌘', Control: 'Ctrl', Shift: 'Shift', Alt: '⌥', Backspace: '⌫', Delete: '⌦', Space: 'Space' }
  : { Meta: 'Win', Control: 'Ctrl', Shift: 'Shift', Alt: 'Alt', Backspace: 'Backspace', Delete: 'Delete', Space: 'Space' }

const ACTIONS = { click: '点击', drag: '拖拽', wheel: '滚轮' }

/** 把键位格式化成可读文案，如 ['Control', 'click'] → 'Ctrl + 点击' */
export function formatKeys(keys) {
  return (Array.isArray(keys) ? keys : [keys])
    .map((key) => ACTIONS[key] ?? LABELS[key] ?? key)
    .join(' + ')
}

/** 判断事件是否按下了平台修饰键（Ctrl / ⌘） */
export function isModPressed(event) {
  return IS_MAC ? event.metaKey : event.ctrlKey
}

/** 判断事件是否按下了节点缩放修饰键（Alt） */
export function isAltPressed(event) {
  return event.altKey
}
