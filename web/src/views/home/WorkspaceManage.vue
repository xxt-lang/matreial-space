<script setup>
/**
 * 工作空间管理页面（首页默认页）：列表 / 新建 / 删除（二次确认）/ 双击进入画布
 *
 * 接口见 src/api/workspace.js。提交类按钮按 web/README.md 的约定实现完整四条：
 * 1. 防抖：SUBMIT_DEBOUNCE 内的重复点击直接忽略
 * 2. 防重复提交：判断依据是数据状态（表单项 createDialog.status、列表项 item.status），
 *    而不是组件内的临时布尔值 —— 组件重挂载后状态也不会丢
 * 3. 提交中按钮切换为「中断」：文案变「中断」、样式切警示描边，点击改为 abort
 * 4. 中断真的取消请求：AbortController 的 signal 透传给 api 层
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import ResizableDialog from '../../components/ResizableDialog.vue'
import { createWorkspace, deleteWorkspace, fetchWorkspaces } from '../../api/workspace'

/** 提交类按钮的防抖间隔（ms），与 PromptInput 的 submitDebounce 保持一致 */
const SUBMIT_DEBOUNCE = 400

const router = useRouter()

/* ---------------- 列表 ---------------- */

const items = ref([])
const total = ref(0)
/** loading | ready | error */
const listStatus = ref('loading')
const listError = ref('')

let listController = null

async function loadList() {
  // 重复触发时只保留最后一次请求
  listController?.abort()
  const controller = new AbortController()
  listController = controller

  listStatus.value = 'loading'
  listError.value = ''

  try {
    const data = await fetchWorkspaces({ signal: controller.signal })
    // status 挂在数据上：删除中的状态跟着数据走，不依赖组件临时变量
    items.value = data.items.map((item) => ({ ...item, status: 'idle' }))
    total.value = data.total
    listStatus.value = 'ready'
  } catch (error) {
    if (error?.name === 'AbortError') return
    listStatus.value = 'error'
    listError.value = error.message
  } finally {
    if (listController === controller) listController = null
  }
}

/** 后端返回 ISO 8601（UTC），转成本地时间展示 */
function formatTime(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString('zh-CN', { hour12: false })
}

/* ---------------- 双击进入画布 ---------------- */

/**
 * 双击卡片进入该工作空间的画布。
 * 画布是独立全屏页（路由名 canvas），工作空间 id 以路由参数带过去，
 * 画布侧后续可据此加载 / 保存节点数据。
 */
function openWorkspace(item, event) {
  // 双击落在「删除」按钮上时不进画布，避免误触
  if (event.target.closest('.ws-list__btn')) return
  router.push({ name: 'canvas', params: { workspaceId: item.id } })
}

/* ---------------- 新建 ---------------- */

const createDialog = reactive({ visible: false, name: '', description: '', status: 'idle', error: '' })
const createSubmitting = computed(() => createDialog.status === 'creating')

let createController = null
let lastCreateClickAt = 0

function openCreateDialog() {
  createDialog.name = ''
  createDialog.description = ''
  createDialog.error = ''
  createDialog.status = 'idle'
  createDialog.visible = true
}

/** 提交中不允许关闭（只能「中断」），否则请求还在飞就把弹窗收掉了 */
function closeCreateDialog() {
  if (createSubmitting.value) return
  createDialog.visible = false
}

async function onCreateClick() {
  // 提交中：按钮即「中断」，点击改为取消请求
  if (createSubmitting.value) {
    createController?.abort()
    return
  }
  if (createDialog.status !== 'idle') return
  const now = Date.now()
  if (now - lastCreateClickAt < SUBMIT_DEBOUNCE) return
  lastCreateClickAt = now

  const name = createDialog.name.trim()
  if (!name) {
    createDialog.error = '请输入工作空间名称'
    return
  }

  const controller = new AbortController()
  createController = controller
  createDialog.status = 'creating'
  createDialog.error = ''

  try {
    await createWorkspace(
      { name, description: createDialog.description.trim() },
      { signal: controller.signal },
    )
    createDialog.status = 'idle'
    createDialog.visible = false
    await loadList()
  } catch (error) {
    createDialog.status = 'idle'
    // 中断不算失败：保留已填内容，用户可以接着重试
    if (error?.name !== 'AbortError') createDialog.error = error.message
  } finally {
    if (createController === controller) createController = null
  }
}

/* ---------------- 删除（二次确认） ---------------- */

const deleteDialog = reactive({ visible: false, id: '', name: '', error: '' })
let deleteController = null
let lastDeleteClickAt = 0

/** 待删除项直接取自列表数据，所以「删除中」的状态本身就在数据上 */
const deleteTarget = computed(() => items.value.find((item) => item.id === deleteDialog.id) || null)
const deleting = computed(() => deleteTarget.value?.status === 'deleting')

function openDeleteDialog(item) {
  if (item.status !== 'idle') return
  deleteDialog.id = item.id
  deleteDialog.name = item.name
  deleteDialog.error = ''
  deleteDialog.visible = true
}

function closeDeleteDialog() {
  if (deleting.value) return
  deleteDialog.visible = false
}

async function onDeleteClick() {
  if (deleting.value) {
    deleteController?.abort()
    return
  }

  const target = deleteTarget.value
  if (!target || target.status !== 'idle') return
  const now = Date.now()
  if (now - lastDeleteClickAt < SUBMIT_DEBOUNCE) return
  lastDeleteClickAt = now

  const controller = new AbortController()
  deleteController = controller
  target.status = 'deleting'
  deleteDialog.error = ''

  try {
    await deleteWorkspace(target.id, { signal: controller.signal })
    deleteDialog.visible = false
    // 本地先摘掉再扣总数，避免整表重拉
    items.value = items.value.filter((item) => item.id !== target.id)
    total.value = Math.max(0, total.value - 1)
  } catch (error) {
    if (error?.name === 'AbortError') {
      // 中断时服务端可能已经删掉了，重拉一次以对齐真实数据
      deleteDialog.visible = false
      await loadList()
      return
    }
    deleteDialog.error = error.message
    target.status = 'idle'
  } finally {
    if (deleteController === controller) deleteController = null
  }
}

/* ---------------- 生命周期 ---------------- */

onMounted(loadList)

onBeforeUnmount(() => {
  listController?.abort()
  createController?.abort()
  deleteController?.abort()
})
</script>

<template>
  <div class="ws-page">
    <header class="ws-page__header">
      <div>
        <h1 class="ws-page__title">工作空间管理</h1>
        <p class="ws-page__subtitle">
          {{ listStatus === 'ready' ? `共 ${total} 个工作空间 · 双击卡片进入画布` : '工作空间是素材画布的容器' }}
        </p>
      </div>

      <div class="ws-page__actions">
        <button
          class="ws-page__btn ws-page__btn--primary"
          type="button"
          :disabled="listStatus !== 'ready'"
          @click="openCreateDialog"
        >
          新建工作空间
        </button>
      </div>
    </header>

    <p v-if="listError" class="ws-page__alert">
      <span>{{ listError }}</span>
      <button class="ws-page__btn" type="button" @click="loadList">重试</button>
    </p>

    <p v-if="listStatus === 'loading'" class="ws-page__placeholder">加载中…</p>
    <p v-else-if="!items.length" class="ws-page__placeholder">
      还没有工作空间，点右上角「新建工作空间」开始。
    </p>

    <ul v-else class="ws-list">
      <li
        v-for="item in items"
        :key="item.id"
        class="ws-list__item"
        @dblclick="openWorkspace(item, $event)"
      >
        <div class="ws-list__main" title="双击进入画布">
          <p class="ws-list__name">{{ item.name }}</p>
          <p class="ws-list__desc">{{ item.description || '（无描述）' }}</p>
          <p class="ws-list__meta">ID {{ item.id }} · 创建于 {{ formatTime(item.created_at) }}</p>
        </div>

        <button
          class="ws-list__btn"
          :class="{ 'ws-list__btn--busy': item.status === 'deleting' }"
          type="button"
          :disabled="item.status !== 'idle'"
          @click="openDeleteDialog(item)"
        >
          {{ item.status === 'deleting' ? '删除中…' : '删除' }}
        </button>
      </li>
    </ul>

    <!-- 新建：名称 + 描述 -->
    <ResizableDialog
      v-model="createDialog.visible"
      title="新建工作空间"
      :width="460"
      :height="330"
      :resizable="false"
      :close-on-click-modal="!createSubmitting"
      :close-on-press-escape="!createSubmitting"
      :show-close="!createSubmitting"
    >
      <label class="ws-form__field">
        <span class="ws-form__label">名称</span>
        <input
          v-model="createDialog.name"
          class="ws-form__input"
          type="text"
          maxlength="64"
          placeholder="例如：角色设定"
          @keyup.enter="onCreateClick"
        />
      </label>

      <label class="ws-form__field">
        <span class="ws-form__label">描述</span>
        <textarea
          v-model="createDialog.description"
          class="ws-form__input ws-form__input--area"
          maxlength="255"
          rows="3"
          placeholder="可选，一句话说明这个空间放什么"
        />
      </label>

      <p v-if="createDialog.error" class="ws-form__error">{{ createDialog.error }}</p>

      <template #footer>
        <button
          class="ws-page__btn"
          type="button"
          :disabled="createSubmitting"
          @click="closeCreateDialog"
        >
          取消
        </button>
        <button
          class="ws-page__btn"
          :class="createSubmitting ? 'ws-page__btn--danger' : 'ws-page__btn--primary'"
          type="button"
          @click="onCreateClick"
        >
          {{ createSubmitting ? '中断' : '创建' }}
        </button>
      </template>
    </ResizableDialog>

    <!-- 删除二次确认：按钮点击只是打开这个弹窗，真正删除要在这里再确认一次 -->
    <ResizableDialog
      v-model="deleteDialog.visible"
      title="删除工作空间"
      :width="420"
      :height="260"
      :resizable="false"
      :close-on-click-modal="!deleting"
      :close-on-press-escape="!deleting"
      :show-close="!deleting"
    >
      <p class="ws-confirm__text">
        确定删除工作空间「<strong class="ws-confirm__name">{{ deleteDialog.name }}</strong>」吗？
      </p>
      <p class="ws-confirm__hint">删除后无法恢复。</p>
      <p v-if="deleteDialog.error" class="ws-form__error">{{ deleteDialog.error }}</p>

      <template #footer>
        <button class="ws-page__btn" type="button" :disabled="deleting" @click="closeDeleteDialog">
          取消
        </button>
        <button
          class="ws-page__btn"
          :class="deleting ? 'ws-page__btn--danger' : 'ws-page__btn--danger-solid'"
          type="button"
          @click="onDeleteClick"
        >
          {{ deleting ? '中断' : '确认删除' }}
        </button>
      </template>
    </ResizableDialog>
  </div>
</template>

<style scoped>
/*
  页面外壳（背景 / 内边距 / 最小高度）由首页布局 HomeLayout 提供，这里只管内容。
  配色沿用画布区的暗色 token，统一带 fallback（这些 token 全局未定义）；
  正文色用 --fg 而不是 --text，后者在 style.css 里是浅色灰，落在暗底上看不清。
*/
.ws-page {
  color: var(--fg, #e9edf5);
}

/* ---------------- 头部 ---------------- */

.ws-page__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border2, #343c4c);
}

.ws-page__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.ws-page__subtitle {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted, #767f92);
}

.ws-page__actions {
  display: flex;
  flex: none;
  gap: 8px;
}

/* ---------------- 按钮（hover 走 accent 约定） ---------------- */

.ws-page__btn {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  font: inherit;
  font-size: 12px;
  line-height: 1.6;
  color: var(--fg, #e9edf5);
  background: var(--surface-2, #1b2130);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    border-color 0.15s ease,
    opacity 0.15s ease;
}

.ws-page__btn:hover:not(:disabled) {
  color: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.ws-page__btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

/* 主操作：accent 实底 */
.ws-page__btn--primary {
  font-weight: 600;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border-color: var(--accent, #f0a63d);
}

.ws-page__btn--primary:hover:not(:disabled) {
  color: var(--accent-ink, #201404);
  opacity: 0.88;
}

/* 警示描边：提交中按钮切到这个样式（可中断） */
.ws-page__btn--danger {
  color: var(--danger, #e06c9f);
  border-color: var(--danger, #e06c9f);
}

.ws-page__btn--danger:hover:not(:disabled) {
  color: var(--danger, #e06c9f);
  background: rgba(224, 108, 159, 0.12);
}

/* 危险操作确认：实底 */
.ws-page__btn--danger-solid {
  font-weight: 600;
  color: #1b0a13;
  background: var(--danger, #e06c9f);
  border-color: var(--danger, #e06c9f);
}

.ws-page__btn--danger-solid:hover:not(:disabled) {
  color: #1b0a13;
  opacity: 0.88;
}

/* ---------------- 状态提示 ---------------- */

.ws-page__alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 16px 0 0;
  padding: 10px 14px;
  font-size: 12px;
  color: var(--danger, #e06c9f);
  background: rgba(224, 108, 159, 0.1);
  border: 1px solid rgba(224, 108, 159, 0.4);
  border-radius: var(--r-sm, 6px);
}

.ws-page__placeholder {
  margin: 48px 0 0;
  font-size: 13px;
  color: var(--muted, #767f92);
  text-align: center;
}

/* ---------------- 列表 ---------------- */

.ws-list {
  display: grid;
  gap: 10px;
  margin: 20px 0 0;
  padding: 0;
  list-style: none;
}

.ws-list__item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  background: var(--surface, #141922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r, 10px);
  transition: border-color 0.15s ease;
}

.ws-list__item:hover {
  border-color: rgba(240, 166, 61, 0.45);
}

.ws-list__main {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.ws-list__name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.ws-list__desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--muted, #767f92);
}

.ws-list__meta {
  margin: 6px 0 0;
  font-family: var(--mono, ui-monospace, Consolas, monospace);
  font-size: 11px;
  color: #5b6376;
}

.ws-list__btn {
  flex: none;
  padding: 6px 14px;
  font: inherit;
  font-size: 12px;
  color: var(--danger, #e06c9f);
  background: transparent;
  border: 1px solid var(--danger, #e06c9f);
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    opacity 0.15s ease;
}

.ws-list__btn:hover:not(:disabled) {
  color: #1b0a13;
  background: var(--danger, #e06c9f);
}

/* 删除请求进行中：按钮不可再点，实际的中断入口在确认弹窗里 */
.ws-list__btn--busy {
  color: var(--muted, #767f92);
  border-color: var(--border2, #343c4c);
}

.ws-list__btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* ---------------- 弹窗内的表单 / 确认文案 ---------------- */

.ws-form__field {
  display: block;
  margin-bottom: 14px;
}

.ws-form__label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--muted, #767f92);
}

.ws-form__input {
  display: block;
  box-sizing: border-box;
  width: 100%;
  padding: 8px 10px;
  font: inherit;
  font-size: 13px;
  color: var(--fg, #e9edf5);
  background: #0f131a;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  outline: none;
  transition: border-color 0.15s ease;
}

.ws-form__input:focus {
  border-color: var(--accent, #f0a63d);
}

.ws-form__input--area {
  min-height: 64px;
  resize: vertical;
}

.ws-form__error {
  margin: 0;
  font-size: 12px;
  color: var(--danger, #e06c9f);
}

.ws-confirm__text {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--fg, #e9edf5);
}

.ws-confirm__name {
  font-weight: 600;
  color: var(--accent, #f0a63d);
}

.ws-confirm__hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--muted, #767f92);
}
</style>
