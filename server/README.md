# material-space 后端（FastAPI）

## 环境要求

- Python 3.14
- 依赖见 `requirements.txt`

## 快速开始

本机已就绪：conda 环境 **`material-space`**（Python 3.14）中已装好运行依赖与测试依赖
（fastapi / uvicorn / pydantic-settings / python-multipart / sqlalchemy / aiosqlite /
langchain / langchain-community / pytest / httpx），
日常只需激活后启动即可：

```bash
cd server

conda activate material-space
# 依赖有变动时再执行：pip install -r requirements.txt
# 没有配置 conda 的机器可以用 venv：python -m venv .venv && .venv\Scripts\activate

# 配置（可选，不建也能跑，默认值即可本地联调）
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

# 启动
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

不想激活环境时，也可以用 `conda run` 直接跑：

```bash
conda run -n material-space uvicorn app.main:app --reload --port 8000
```

- 接口文档（OpenAPI）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

## 目录结构

```
server/
├─ app/
│  ├─ main.py          # 入口：CORS、路由挂载、上传目录静态托管
│  ├─ config.py        # 配置（pydantic-settings，读 .env）
│  ├─ api/             # ① Controller 层：health / gen / upload
│  ├─ schemas/         # 请求 / 响应 / DTO 模型
│  ├─ services/        # ② Service 层：业务编排、事务边界（路由只做校验与转发）
│  ├─ pipeline/        # ③ Model pipeline 层：提示词组装、推理编排、后处理
│  ├─ database/        # ④ Database 层：ORM 模型与仓储（唯一写 SQL 的地方）
│  └─ utils/           # ⑤ Utils 层：图像转换、文件校验等纯函数
├─ tests/              # pytest 测试（按层组织）
├─ uploads/            # 上传产物（运行时生成，已 gitignore）
├─ data/               # SQLite 数据库文件（运行时生成，已 gitignore）
├─ docs/               # 后端开发规范（docs/backend-standards.md）
├─ requirements.txt
├─ requirements-dev.txt
└─ .env.example
```

## 开发规范

后端采用五层结构，依赖严格单向（Controller → Service → Pipeline / Database → Utils）：

| 层 | 目录 | 职责 |
| --- | --- | --- |
| Controller | `app/api/` | 路由、入参校验、状态码与响应模型，不含业务逻辑 |
| Service | `app/services/` | 用例编排、事务边界、领域异常，不感知 HTTP 与 SQL |
| Pipeline | `app/pipeline/` | 模型流程：提示词组装 → 预处理 → 推理 → 后处理 |
| Database | `app/database/` | ORM 模型与仓储，唯一允许出现 SQL 的地方 |
| Utils | `app/utils/` | 图像转换、编码、文件校验等无状态纯函数 |

新增代码前请先阅读 **[`docs/backend-standards.md`](./docs/backend-standards.md)**（分层职责、
依赖方向、异常与日志、测试组织、新增能力的落地清单）。

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
