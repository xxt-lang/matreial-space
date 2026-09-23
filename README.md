# material-space

基于 Vue 3 + Vite + [@vue-flow/core](https://vue-flow.dev/) 的节点式素材工作台。
画布上右键创建节点、节点间连线表达上下游关系，节点内可编辑提示词并触发生成。

## 目录结构

```
src/
├─ components/                     # 全局通用组件
│  └─ ResizableDialog.vue          # 可拖动 / 可调整大小的弹窗（交互对齐 Element Dialog）
└─ views/workSpace/                # 画布工作区
   ├─ work.vue                     # 画布宿主：节点 / 连线的增删改、与 api 层交互
   ├─ api/                         # 接口层（当前为本地模拟实现，接入后端时替换实现即可）
   ├─ assistComponent/             # 工作区公共组件
   │  ├─ ContextMenu.vue           # 画布右键菜单
   │  └─ PromptInput.vue           # 提示词富文本输入（TipTap + @ 引用）
   ├─ nodesComponent/GenImageNode/ # 生图节点及其私有子组件
   └─ shortcuts/                   # 画布快捷键定义（键位只在这里维护）
```

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

## 常用命令

```bash
npm install     # 安装依赖
npm run dev     # 启动开发服务器
npm run build   # 生产构建
npm run preview # 预览构建产物
```
