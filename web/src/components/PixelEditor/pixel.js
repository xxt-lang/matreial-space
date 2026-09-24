/**
 * 像素画数据内核
 *
 * 全部是无状态纯函数，不碰 DOM、不认识 Vue，方便单独推演 / 复用 / 测试。
 *
 * 数据格式：Uint8ClampedArray，长度 = size × size × 4，按 RGBA 顺序排列，
 * 和浏览器 ImageData.data 完全一致 —— 可以直接互相构造，省掉一次逐像素拷贝。
 */

/** 透明像素（橡皮 / 清空用） */
export const TRANSPARENT = [0, 0, 0, 0]

/** 新建一块全透明缓冲 */
export function createBuffer(size) {
  return new Uint8ClampedArray(size * size * 4)
}

/** 拷贝缓冲（撤销快照用） */
export function cloneBuffer(buffer) {
  return new Uint8ClampedArray(buffer)
}

/** 两个颜色是否完全相同 */
export function sameRgba(a, b) {
  return a[0] === b[0] && a[1] === b[1] && a[2] === b[2] && a[3] === b[3]
}

/** 读某像素的 RGBA；越界返回 null */
export function getPixel(buffer, size, x, y) {
  if (x < 0 || y < 0 || x >= size || y >= size) return null
  const index = (y * size + x) * 4
  return [buffer[index], buffer[index + 1], buffer[index + 2], buffer[index + 3]]
}

/** 写某像素；越界忽略（画笔拖出画布边缘时的安全兜底） */
export function setPixel(buffer, size, x, y, rgba) {
  if (x < 0 || y < 0 || x >= size || y >= size) return
  const index = (y * size + x) * 4
  buffer[index] = rgba[0]
  buffer[index + 1] = rgba[1]
  buffer[index + 2] = rgba[2]
  buffer[index + 3] = rgba[3]
}

/**
 * 两个像素点之间连成直线（Bresenham，含两端）
 *
 * 为什么要它：指针事件是离散的，快速拖动时相邻两次 move 之间可能隔好几个像素，
 * 只画当前点会得到断续的虚线；用直线把中间补齐才是连续的笔迹。
 *
 * @param {(x: number, y: number) => void} draw 每个点怎么画，由调用方决定
 */
export function line(x0, y0, x1, y1, draw) {
  let x = x0
  let y = y0
  const dx = Math.abs(x1 - x0)
  const dy = -Math.abs(y1 - y0)
  const stepX = x0 < x1 ? 1 : -1
  const stepY = y0 < y1 ? 1 : -1
  let error = dx + dy

  for (;;) {
    draw(x, y)
    if (x === x1 && y === y1) return
    const doubled = 2 * error
    if (doubled >= dy) {
      error += dy
      x += stepX
    }
    if (doubled <= dx) {
      error += dx
      y += stepY
    }
  }
}

/** 整块填充 */
export function fill(buffer, size, rgba) {
  for (let index = 0; index < buffer.length; index += 4) {
    buffer[index] = rgba[0]
    buffer[index + 1] = rgba[1]
    buffer[index + 2] = rgba[2]
    buffer[index + 3] = rgba[3]
  }
}

/**
 * 油漆桶：4 邻域洪水填充
 *
 * 颜色精确匹配才扩散（不做容差），这样渐变图 / 抗锯齿边缘不会被一次性填满 ——
 * 像素画里这种"只填纯色区域"的行为更符合预期。
 */
export function floodFill(buffer, size, x, y, rgba) {
  const target = getPixel(buffer, size, x, y)
  if (!target || sameRgba(target, rgba)) return

  const stack = [[x, y]]
  while (stack.length) {
    const [currentX, currentY] = stack.pop()
    const current = getPixel(buffer, size, currentX, currentY)
    if (!current || !sameRgba(current, target)) continue

    setPixel(buffer, size, currentX, currentY, rgba)
    stack.push([currentX + 1, currentY], [currentX - 1, currentY], [currentX, currentY + 1], [currentX, currentY - 1])
  }
}

/** 两块缓冲是否完全一致（用来跳过没产生变化的一次操作，不往撤销栈里塞垃圾） */
export function isEqualBuffer(a, b) {
  if (!a || !b || a.length !== b.length) return false
  for (let index = 0; index < a.length; index += 1) {
    if (a[index] !== b[index]) return false
  }
  return true
}

/** '#rgb' / '#rrggbb' → [r, g, b, 255]；解析失败返回 null */
export function hexToRgba(hex) {
  const value = String(hex ?? '').trim().replace('#', '')
  const full = value.length === 3 ? value.split('').map((char) => char + char).join('') : value
  if (!/^[0-9a-fA-F]{6}$/.test(full)) return null

  return [
    Number.parseInt(full.slice(0, 2), 16),
    Number.parseInt(full.slice(2, 4), 16),
    Number.parseInt(full.slice(4, 6), 16),
    255,
  ]
}

/** [r, g, b, a] → '#rrggbb'（丢掉 alpha，取色只带 RGB 回来） */
export function rgbaToHex(rgba) {
  const channel = (value) => value.toString(16).padStart(2, '0')
  return `#${channel(rgba[0])}${channel(rgba[1])}${channel(rgba[2])}`
}
