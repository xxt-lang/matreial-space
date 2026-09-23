# material-space 后端（FastAPI）

## 环境要求

- Python 3.10+
- 依赖见 `requirements.txt`

## 快速开始

```bash
cd server

# 虚拟环境（conda 或 venv 二选一）
conda activate <你的虚拟环境>
# python -m venv .venv && .venv\Scripts\activate     # Windows
# python -m venv .venv && source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt

# 配置（可选，不建也能跑，默认值即可本地联调）
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

# 启动
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- 接口文档（OpenAPI）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

## 目录结构

```
server/
├─ app/
│  ├─ main.py          # 入口：CORS、路由挂载、上传目录静态托管
│  ├─ config.py        # 配置（pydantic-settings，读 .env）
│  ├─ api/             # 路由层：health / gen / upload
│  ├─ schemas/         # 请求 / 响应模型
│  └─ services/        # 业务逻辑（路由只做校验与转发）
├─ tests/              # pytest 冒烟测试
├─ uploads/            # 上传产物（运行时生成，已 gitignore）
├─ requirements.txt
├─ requirements-dev.txt
└─ .env.example
```

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/gen` | 生成图片（当前返回 SVG 占位图） |
| POST | `/api/upload` | 图片上传（仅图片类型，默认 5MB 上限） |

### POST /api/gen

对应前端 `web/src/views/workSpace/api/gen.js` 与 `GenImageNode` 的 `onGenerate`。

请求：

```json
{
  "id": "image-1758...",
  "setting": { "model": "flux-schnell", "mode": "hd", "size": 64, "image": "" },
  "text": "赛博朋克风格的猫，参考 @#1",
  "nodes": [{ "id": "image-1758...", "index": 1, "label": "生图", "image": "" }]
}
```

响应：

```json
{ "image": "data:image/svg+xml,... 或 /uploads/<uuid>.png" }
```

**中断**：前端点「中断」会 abort 请求，连接随之断开；
`services/generator.py` 用 `request.is_disconnected()` 周期性检测，断开后抛
`GenerationCancelled`，路由返回 499 并记录日志。

### POST /api/upload

`multipart/form-data`，字段名 `file`。响应：

```json
{ "url": "/uploads/<uuid>.png", "name": "原文件名.png", "size": 12345, "type": "image/png" }
```

文件落在 `uploads/`，由 `/uploads` 静态托管；接入对象存储后改为返回外链。

## 测试

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 接入真实模型时

1. `services/generator.py`：把 `_mock_image()` 换成真实推理调用
   （模型 / 模式 / 尺寸 / 参考图在 `payload.setting`，提示词在 `payload.text`，
   上游节点的图片在 `payload.nodes`）
2. 长任务建议改成「提交任务 + 轮询 / SSE 订阅进度」，同步返回只适合几秒级的任务；
   相应改动同时体现在前端（`api/gen.js`）
3. 中断检测保留 `is_disconnected()`，或改为任务队列的取消接口
