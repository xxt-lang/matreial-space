# material-space 前端（web）

基于 Vue 3 + Vite + [@vue-flow/core](https://vue-flow.dev/) 的节点式素材工作台前端。
画布上右键创建节点、节点间连线表达上下游关系，节点内可编辑提示词并触发生成。

> 仓库根目录是 monorepo：后端在 `../server`，两端启动方式见根目录 `README.md`。

## 目录结构

```
src/
├─ api/                            # 跨页面共用的接口层
│  └─ workspace.js                 # 工作空间接口（首页与画布共用，调 /api/workspaces）
├─ components/                     # 全局通用组件
│  ├─ AppIcon.vue                  # 公共图标：<AppIcon type="workspace" />，按 type 渲染内置 svg
│  └─ ResizableDialog.vue          # 可拖动 / 可调整大小的弹窗（交互对齐 Element Dialog）
└─ views/
   ├─ home/                        # 首页：左侧导航 + 子页面（不带画布）
   │  ├─ HomeLayout.vue            # 布局：左侧纯图标导航（固定 + 垂直居中）+ 右侧 router-view
   │  ├─ WorkspaceManage.vue       # 工作空间管理（默认页）：列表 / 新建 / 删除二次确认 / 双击进画布
   │  ├─ LLMConfig.vue             # LLM 配置（占位页）
   │  └─ SkillConfig.vue           # Skill 配置（占位页）
   ├─ workSpace/                   # 画布工作区（独立全屏页）
   │  ├─ work.vue                  # 画布宿主：节点 / 连线的增删改、顶部工作空间名称胶囊
   │  ├─ api/                      # 接口层（当前为本地模拟实现，接入后端时替换实现即可）
   │  ├─ assistComponent/          # 工作区公共组件
   │  │  ├─ ContextMenu.vue        # 画布右键菜单
   │  │  ├─ PromptInput.vue        # 提示词富文本输入（TipTap + @ 引用）
   │  │  └─ SelectMenu.vue         # 下拉选择（工具栏与输入区共用）
   │  ├─ nodesComponent/GenImageNode/ # 生图节点及其私有子组件
   │  └─ shortcuts/                # 画布快捷键定义（键位只在这里维护）
   └─ FlowDemo.vue                 # Vue Flow 示例页（脚手架保留）
```

## 路由

| 路径 | 名称 | 页面 | 说明 |
| --- | --- | --- | --- |
| `/` | —— | `home/HomeLayout.vue` | 重定向到 `/workspaces` |
| `/workspaces` | `workspace-manage` | `home/WorkspaceManage.vue` | 首页默认页 |
| `/llm` | `llm-config` | `home/LLMConfig.vue` | 占位 |
| `/skill` | `skill-config` | `home/SkillConfig.vue` | 占位 |
| `/workspace/:workspaceId?` | `canvas` | `workSpace/work.vue` | 画布，独立全屏页，不带首页导航 |
| `/flow` | `flow` | `FlowDemo.vue` | 示例页 |

从工作空间卡片**双击**会 `router.push({ name: 'canvas', params: { workspaceId } })`；
画布顶部中间的胶囊拿这个 id 调 `GET /api/workspaces/{id}` 展示当前工作空间名称：

- 左侧「←」回工作空间列表（`workspace-manage`）；
- 点「隐藏」向上收成画布顶部的一个小角（`translate + scaleX`，只露约 10px），
  鼠标悬浮这个小角会临时展开，点「显示」则保持展开。

节点/连线数据仍是内存态，按空间加载 / 保存画布是下一步的接入点。

## 联调后端

`vite.config.js` 已配置开发代理：

| 前端路径 | 代理到 |
| --- | --- |
| `/api/*` | `http://127.0.0.1:8000/api/*` |
| `/uploads/*` | `http://127.0.0.1:8000/uploads/*` |

所以业务代码统一用相对路径（如 `fetch('/api/gen')`）即可，不需要写死域名，也不会有 CORS 问题。
后端起法见 [`../server/README.md`](../server/README.md)。

接口层在 `src/views/workSpace/api/`：现在是本地模拟实现（`setTimeout` 模拟异步返回），
接后端时只替换实现、保持入参与返回结构不变即可。

`src/api/workspace.js` 已经接了真实后端（`fetch('/api/workspaces')`）：
统一请求封装，204 返回 `null`，非 2xx 抛出带 `code` 的 `Error`（`message` 直接用后端的文案），
`{ signal }` 透传到 `fetch`。

接口层放哪：**跨页面共用**的放 `src/api/`；只服务单个页面的放该页面自己的 `api/` 目录
（如 `views/workSpace/api/`）。

## 开发约定

### 提交类按钮：防抖 + 防重复提交 + 可中断

**适用范围**：所有会调用后端（或任何有异步写操作）的按钮，例如生成、保存、上传、删除、
发布等。新增同类按钮时请一并实现下面四条，不要只做其中一部分。

1. **防抖**：短时间内重复点击只生效一次。
   `PromptInput.vue` 中的 `submitDebounce`（默认 400ms）用「上次提交时间戳」实现，
   间隔内的点击直接忽略；需要时可通过 prop 调整。
2. **防重复提交**：请求进行中不允许再次提交。
   判断依据必须是**数据状态**（如 `data.status === 'generating'`），不要用组件内部的
   临时布尔值 —— 否则节点折叠、组件重挂载后状态就丢了。
   现有实现有三层拦截：按钮点击层（`PromptInput.vue` 的 `submit()`）、
   节点层（`GenImageNode.vue` 的 `onGenerate()` 判 status）、
   宿主层（`work.vue` 的 `genControllers` 里已有该节点的任务则直接忽略）。
3. **提交中按钮切换为「中断」**：`PromptInput` 的 `loading` prop 为 `true` 时，
   按钮文案变为 `abortText`（默认「中断」）、样式切为警示描边，点击发出 `abort` 事件，
   而不是再次 `submit`。
4. **中断要真的取消请求**：宿主用 `AbortController` 管理任务
   （见 `work.vue` 的 `genControllers`），把 `signal` 传进 api 层；
   api 层收到 abort 后清理计时器 / 请求，并以 `AbortError` 拒绝，
   宿主据此把节点状态复位（例如 `status: 'idle'`），加载中状态随之撤销。

参考实现（生图链路）：

| 环节 | 位置 | 关键点 |
| --- | --- | --- |
| 防抖 + 提交 / 中断分流 | `assistComponent/PromptInput.vue` | `submit()` / `abort()` / `onSubmitClick()` |
| 状态判定与透传 | `nodesComponent/GenImageNode/GenImageNode.vue` | `:loading="data.status === 'generating'"`、`emit('abort')` |
| 任务管理与状态收尾 | `work.vue` | `genControllers: Map<nodeId, AbortController>`，成功 / 失败 / 中断三条收尾分支 |
| 中断支持 | `api/gen.js` | `createGeneration(payload, { signal })` |

```js
// 宿主侧：一个节点同时只允许一个进行中的任务，且可被中断
async function onNodeGenerate(payload) {
  const { id } = payload
  if (genControllers.has(id)) return            // 防重复提交

  const controller = new AbortController()
  genControllers.set(id, controller)
  updateNodeData(id, { status: 'generating' })

  try {
    const { image } = await createGeneration(payload, { signal: controller.signal })
    updateNodeData(id, { status: 'done', image })
  } catch (error) {
    if (error?.name === 'AbortError') updateNodeData(id, { status: 'idle' })
    else updateNodeData(id, { status: 'error', error: error.message })
  } finally {
    genControllers.delete(id)
  }
}
```

### 其它约定

- **键位只在 `views/workSpace/shortcuts/` 定义**，页面与组件不得硬编码键位；
  需要 vue-flow 识别的键位通过 `VUE_FLOW_SHORTCUT_PROPS` 一次性注入。
- **画布内的交互区**记得加 vue-flow 的约定类：`nodrag`（不触发节点拖动）、
  `nowheel`（不触发画布缩放）、`nokey`（按键不触发画布快捷键，
  contenteditable 内部按键尤其需要）。
- **节点级 UI 状态写进 `node.data`**（如 `status` / `scale` / `promptInputHeight`），
  便于持久化与跨组件读取；只有纯展示的临时状态才放组件内部。
- **图标统一走 `components/AppIcon.vue`**：`<AppIcon type="workspace" :size="18" />`，
  不要在页面里散落内联 `<svg>`；新增图标 = 往该组件的 `ICONS` 表里加一条 path 数据
  （统一 24×24 坐标系、只描边不填充，颜色跟随 `currentColor`）。
- **只放图标的按钮必须补 `title` + `aria-label`**（首页左侧导航就是这么做的），
  不要让图标成为唯一的语义来源——鼠标悬浮要有提示，读屏也要能念出用途。

## 常用命令

```bash
npm install     # 安装依赖
npm run dev     # 启动开发服务器
npm run build   # 生产构建
npm run preview # 预览构建产物
```
