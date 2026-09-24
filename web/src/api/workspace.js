/**
 * 工作空间接口层（首页与画布共用，所以放在 src/api/）
 *
 * 对应后端 server/app/api/workspace.py：
 * - GET    /api/workspaces          列表 → { items, total }
 * - POST   /api/workspaces          创建 → 工作空间对象（201）
 * - GET    /api/workspaces/{id}     详情 → 工作空间对象（不存在则 404）
 * - DELETE /api/workspaces/{id}     删除 → 204 无响应体（不存在则 404）
 *
 * 约定（见 web/README.md）：返回 Promise、接受 { signal }，
 * abort 时以 AbortError 拒绝，由调用方复位状态并重试。
 */

const BASE_URL = '/api/workspaces'

/** 统一请求：204 返回 null；非 2xx 抛出带 code 的 Error */
async function request(url, { method = 'GET', body, signal } = {}) {
  const response = await fetch(url, {
    method,
    signal,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (response.status === 204) return null

  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    // 领域异常是 { code, message }；FastAPI 参数校验失败是 { detail: [...] }
    const detail = Array.isArray(data?.detail) ? data.detail[0]?.msg : data?.detail
    const error = new Error(data?.message || detail || `请求失败（${response.status}）`)
    // 调用方可以据此分支，例如 not_found 表示工作空间已被删除
    error.code = data?.code || 'http_error'
    throw error
  }

  return data
}

/** 列出全部工作空间 */
export function fetchWorkspaces({ signal } = {}) {
  return request(BASE_URL, { signal })
}

/** 取单个工作空间 */
export function fetchWorkspace(id, { signal } = {}) {
  return request(`${BASE_URL}/${encodeURIComponent(id)}`, { signal })
}

/** 创建工作空间 */
export function createWorkspace(payload, { signal } = {}) {
  return request(BASE_URL, { method: 'POST', body: payload, signal })
}

/** 删除工作空间 */
export function deleteWorkspace(id, { signal } = {}) {
  return request(`${BASE_URL}/${encodeURIComponent(id)}`, { method: 'DELETE', signal })
}
