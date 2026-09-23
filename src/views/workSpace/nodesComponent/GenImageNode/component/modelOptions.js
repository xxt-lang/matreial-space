/**
 * 生图节点可选模型（暂为写死的静态列表）
 * 后续接入后端后，改为从 api/ 拉取模型列表
 */
export const MODEL_OPTIONS = [
  { value: 'flux-schnell', label: 'Flux Schnell' },
  { value: 'flux-dev', label: 'Flux Dev' },
  { value: 'sdxl', label: 'SDXL' },
  { value: 'sd15', label: 'SD 1.5' },
]

export const DEFAULT_MODEL = MODEL_OPTIONS[0].value
