/**
 * 生图节点缩放配置（节点缩放规则的唯一来源）
 *
 * 缩放只改变节点在画布上的整体显示尺寸（等比），不改变内部布局：
 * 节点外层按「设计尺寸 × scale」占位，内层仍按设计尺寸布局后整体 transform: scale。
 */

/** 新建节点的默认缩放系数：设计尺寸（450×500）的一半 */
export const DEFAULT_SCALE = 0.5

/** 缩放区间 */
export const MIN_SCALE = 0.25
export const MAX_SCALE = 1.5

/** 滚轮每格的缩放步进 */
export const SCALE_STEP = 0.1

/** 把缩放系数收敛到合法区间，并保留两位小数 */
export function clampScale(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return DEFAULT_SCALE
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, Number(num.toFixed(2))))
}
