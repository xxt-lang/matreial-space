/**
 * 生图接口层
 *
 * 当前为「本地模拟实现」：用 setTimeout 模拟一次异步生成，便于先跑通
 * 「触发生成 → 图片区加载中 → 成功 / 失败收尾」的完整链路。
 * 接入真实后端时只需替换 createGeneration 的实现（保持入参与返回结构不变）。
 */

/** 模拟耗时（毫秒） */
const MOCK_DELAY = 2400

/** 模拟失败概率 */
const MOCK_FAIL_RATE = 0.3

/** 占位图配色（仅模拟用） */
const MOCK_COLORS = ['#f0a63d', '#4f9cf9', '#7ee787', '#e06c9f', '#b692f6']

/** 造一张占位图（SVG data URL）：渐变底 + 文案，仅用于模拟生成结果 */
function mockImageUrl(seed = 0) {
  const color = MOCK_COLORS[seed % MOCK_COLORS.length]
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="${color}" stop-opacity="0.9" />
        <stop offset="1" stop-color="#0d1117" stop-opacity="0.95" />
      </linearGradient>
    </defs>
    <rect width="256" height="256" fill="url(#g)" />
    <text x="50%" y="50%" fill="#ffffff" font-family="sans-serif" font-size="28"
      text-anchor="middle" dominant-baseline="middle">mock ${seed}</text>
  </svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

/**
 * 创建一次生成任务
 * @param {{ id: string, setting: object, text: string, nodes: Array }} payload 生成参数
 * @param {{ signal?: AbortSignal }} [options] signal：中断信号，abort 时以 AbortError 拒绝
 * @returns {Promise<{ image: string }>} 成功返回图片地址；失败 reject(Error)
 */
export function createGeneration(payload, { signal } = {}) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      // 便于测试失败分支：提示词里带「失败」二字时必定失败
      const forceFail = /失败/.test(payload?.text ?? '')
      if (forceFail || Math.random() < MOCK_FAIL_RATE) {
        reject(new Error('生成失败，请稍后重试'))
        return
      }
      resolve({ image: mockImageUrl(Math.floor(Math.random() * 1000)) })
    }, MOCK_DELAY)

    // 中断：清掉定时器并以 AbortError 拒绝，宿主据此把节点状态复位
    signal?.addEventListener(
      'abort',
      () => {
        window.clearTimeout(timer)
        reject(new DOMException('生成已中断', 'AbortError'))
      },
      { once: true },
    )
  })
}
