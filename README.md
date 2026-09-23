# material-space

节点式素材工作台：画布上右键创建节点、节点之间连线表达上下游关系、节点内编辑提示词并触发生成。

前端 `Vue 3 + Vite + @vue-flow/core`，后端 `FastAPI`，放在同一个仓库里管理。

## 目录结构

```
material-space/
├─ web/        # 前端（Vue 3 + Vite）
├─ server/     # 后端（Python + FastAPI）
├─ .vscode/    # 编辑器配置（工作区级）
├─ .gitignore
└─ README.md
```

## 快速开始

### 后端（先启动，前端代理指向它）

```bash
cd server

conda activate material-space     # 本机已就绪的环境（Python 3.14，依赖已装）
# 依赖有变动时再执行：pip install -r requirements.txt
# 没有 conda 的机器：python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

> 不想激活环境也可以：`conda run -n material-space uvicorn app.main:app --reload --port 8000`

- 健康检查：http://127.0.0.1:8000/api/health
- 接口文档：http://127.0.0.1:8000/docs
- 更多说明见 [`server/README.md`](./server/README.md)

### 前端

```bash
cd web
npm install
npm run dev        # http://localhost:5173
```

`web/vite.config.js` 已把 `/api`、`/uploads` 代理到 `http://127.0.0.1:8000`，
所以前端统一用相对路径调用后端，**开发期不需要处理 CORS**（后端也配了 CORS 白名单，
便于不经代理直接访问）。

## 前后端约定

| 能力 | 接口 | 契约 |
| --- | --- | --- |
| 生成图片 | `POST /api/gen` | 请求见 `server/app/schemas/gen.py`，响应 `{ image }` |
| 中断生成 | —— | 前端 `AbortController` 断开连接，后端 `is_disconnected()` 检测后取消任务 |
| 图片上传 | `POST /api/upload` | `multipart/form-data`，字段 `file`，响应 `{ url, name, size, type }` |
| 健康检查 | `GET /api/health` | `{ "status": "ok" }` |

前端侧的开发约定（提交类按钮的防抖、防重复提交、可中断，画布交互类命名等）
见 [`web/README.md`](./web/README.md) 的「开发约定」章节。
