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
│  ├─ AppIcon/                     # 公共图标
│  │  ├─ AppIcon.vue               #   组件：<AppIcon type="workspace" />，按 type 内联 icon/ 下的 svg
│  │  └─ icon/                     #   图标文件：一个图标一个 svg，文件名即 type
│  ├─ PixelEditor/                 # 像素画编辑器（独立组件，见下方「像素画编辑器」）
│  │  ├─ PixelEditor.vue           #   外壳：工具条 / 调色板 / 缩放 / 撤销栈 / 导出
│  │  ├─ PixelCanvas.vue           #   画布：双层 canvas 渲染 + 指针取像素坐标
│  │  └─ pixel.js                  #   像素内核：画点 / 直线 / 油漆桶 / 快照等纯函数
│  └─ ResizableDialog.vue          # 弹窗：可拖动 / 可调整大小，也支持 fullscreen 全屏
└─ views/
   ├─ home/                        # 首页：左侧导航 + 子页面（不带画布）
   │  ├─ HomeLayout.vue            # 布局：左侧纯图标导航（固定 + 垂直居中）+ 右侧 router-view
   │  ├─ WorkspaceManage.vue       # 工作空间管理（默认页）：卡片网格 / 新建 / 删除二次确认 / 双击进画布
   │  ├─ LLMConfig.vue             # LLM 配置（占位页）
   │  └─ SkillConfig.vue           # Skill 配置（占位页）
   ├─ workSpace/                   # 画布工作区（独立全屏页）
   │  ├─ work.vue                  # 画布宿主：节点/连线增删改、顶部名称胶囊、节点编辑弹窗（内嵌像素画编辑器）
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

## 像素画编辑器

`src/components/PixelEditor/`：独立组件，不掺业务。当前宿主是画布节点的编辑弹窗
（`work.vue` 里节点工具栏「编辑」→ **默认全屏**的弹窗内嵌编辑器 → 「应用到节点」写回 `node.data.image`）。

```vue
<PixelEditor
  :image="data.image"
  :size="data.size"
  :canvases="canvases"
  :active-id="activeId"
  @apply="onApply"
  @select="onSelect"
/>
```

| prop / emit | 类型 | 说明 |
| --- | --- | --- |
| `image` | String | 初始内容（dataURL 或同源 URL），为空表示从空白开始；加载后成为撤销栈起点 |
| `size` | Number | 像素画边长。编辑器内**只读**——尺寸的唯一来源是节点工具栏，避免两处都能改 |
| `canvases` | Array | 画布列表 `[{ id, name, image }]`，由宿主传入（节点点击编辑时带过来） |
| `activeId` | String | 列表里当前正在编辑的项：高亮且不可再点 |
| `apply` | event | 点「应用到节点」时抛出 1:1 的 PNG dataURL |
| `select` | event | 在画布列表里选了另一张时抛出它的 id，怎么切换由宿主决定 |

| 文件 | 职责 |
| --- | --- |
| `PixelEditor.vue` | 外壳：工具条 / 调色板 / 缩放 / 撤销栈 / 应用与导出 |
| `PixelCanvas.vue` | 画布：双层 canvas 渲染 + 指针坐标映射，不认识「工具」语义 |
| `pixel.js` | 像素内核：画点 / 直线 / 油漆桶 / 快照 / 颜色互转，纯函数、不碰 DOM |

几个关键设计：

- **数据格式**：`Uint8ClampedArray`，长度 `size × size × 4` 按 RGBA 排列，和 `ImageData.data`
  完全一致，可以直接互相构造，省掉一次逐像素拷贝。
- **两层 canvas**：底图尺寸就是 `size × size`（1 个数据点 = 1 个画布像素），靠 CSS 放大 +
  `image-rendering: pixelated` 做最近邻放大；网格单独一层、画在「显示尺寸」上，放大后仍是 1px 细线
  （画在底图上会被一起放大成粗条）。
- **就地修改 + `version`**：缓冲由编辑器持有并就地改，TypedArray 改内容不会触发 Vue 响应，
  所以改完把 `version` +1 通知画布重绘。
- **撤销栈存整块快照**（64×64 只有 16KB），记「状态」而不是「操作」，撤销/重做就是指针前后移动；
  上限 40 步，内容没变化（如用同色再填一次）不会塞进栈里。
- **拖动补点**：指针事件是离散的，相邻两次 move 之间用 Bresenham 连成直线，快速拖动才不会画成虚线。
- **导入导出都是 1:1**：导入用最近邻重采样，导出 `toDataURL('image/png')` 保持原始分辨率；
  节点图片区用 `image-rendering: pixelated` 放大展示，所以小图不会糊。
- **画布列表由宿主注入**：编辑器不认识节点。宿主在节点编辑事件里把列表塞进 `editDialog.canvases`
  （当前 = 画布上所有生图节点），编辑器只负责展示与上报 `select(id)`；
  宿主收到后切换编辑目标，编辑器按新的 `image` / `size` 重新载入即可，不需要额外接口。
  面板由工具条上的图层图标开关（默认展开）。

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
- **图标统一走 `components/AppIcon/`**：`<AppIcon type="workspace" :size="18" />`，
  不要在页面里散落内联 `<svg>`；新增图标 = 丢一个 svg 进 `AppIcon/icon/` 目录
  （**文件名即 `type`**，按 24×24 坐标系绘制，颜色写 `currentColor` 就会跟随文字色）。
  svg 会被组件以 `?raw` 内联进 DOM，所以不产生额外网络请求。
- **只放图标的按钮必须补 `title` + `aria-label`**（首页左侧导航就是这么做的），
  不要让图标成为唯一的语义来源——鼠标悬浮要有提示，读屏也要能念出用途。

## 常用命令

```bash
npm install     # 安装依赖
npm run dev     # 启动开发服务器
npm run build   # 生产构建
npm run preview # 预览构建产物
```
