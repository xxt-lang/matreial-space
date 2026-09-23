<script setup>
/**
 * 提示词输入框（工作区公共组件）
 *
 * 基于 TipTap（ProseMirror）的轻量富文本输入：
 * - 输入 @ 弹出候选列表（键盘 ↑/↓ 选择、Enter/Tab 确认、Esc 关闭，也可鼠标点击）
 * - 选中后插入行内 mention 节点：`@#序号` 显示为蓝色标签，可整体选中 / 删除
 * - 文本中所有 @ 字符都会染蓝（见 AtKeyword 装饰插件）
 * - box 内展示当前文本已引用的候选项内容（缩略图 + 序号）
 * - 引用节点保存来源节点 id（渲染为 data-id 隐藏信息），
 *   配合 validMentionIds 可校验引用是否失效（如来源节点已被删除）：失效的引用会置灰
 * - 与业务无关：文案、候选、初始高度通过 props 传入；对外是纯文本，
 *   引用标记序列化为 `@#<序号>`，语义（对应哪个上游节点）由使用方决定
 *
 * 画布适配：根元素带 `nodrag nokey`、候选列表带 `nowheel`，
 * 放在 vue-flow 节点内使用时不会触发节点拖动 / 画布缩放，
 * 编辑区里的 Delete / Backspace 也不会被画布当作「删除所选」
 *
 * 高度（offsetHeight，不受父级 transform 影响，始终是未缩放的 CSS 像素）：
 *   panel —— 面板当前高度（使用方可据此同步自身高度）
 *   base  —— 默认（空内容）状态下的面板高度，作为高度增量的基准
 *   input —— 文本域当前高度（使用方据此持久化，供下次恢复）
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { Extension, mergeAttributes } from '@tiptap/core'
import Document from '@tiptap/extension-document'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import HardBreak from '@tiptap/extension-hard-break'
import History from '@tiptap/extension-history'
import Mention from '@tiptap/extension-mention'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

const props = defineProps({
  modelValue: { type: String, default: '' },
  /** 已保存的文本域高度（px），0 表示使用默认高度 */
  height: { type: Number, default: 0 },
  placeholder: { type: String, default: '请输入提示词' },
  /** 提交按钮文案 */
  submitText: { type: String, default: '生成' },
  /**
   * @ 候选列表：[{ id, index?, label?, image? }]
   * index 用于生成引用标记 @#index，label / image 用于展示
   */
  mentions: { type: Array, default: () => [] },
  /** @ 与引用标记的文字颜色 */
  mentionColor: { type: String, default: '#4f9cf9' },
  /**
   * 仍然有效的引用 id 列表（如「画布上仍存在的节点 id」）
   * 引用节点本身保存了 id（渲染为 data-id 隐藏信息），据此校验引用是否失效；
   * 不传该 prop 则不做校验
   */
  validMentionIds: { type: Array, default: null },
})

const emit = defineEmits(['update:modelValue', 'submit', 'resize'])

const canSubmit = computed(() => props.modelValue.trim().length > 0)

/**
 * 是否为空：决定占位文案显隐
 * 直接由对外文本推导，避免与编辑器内部状态不同步——
 * 重新挂载时初始内容不会触发 onUpdate，用内部状态会导致占位文案压在已有内容上
 */
const isEmpty = computed(() => props.modelValue.length === 0)

const panelRef = ref(null)
const fieldRef = ref(null)
/** 编辑器中当前插入的引用节点（含 id / index / 快照信息），随编辑器内容同步 */
const docMentions = ref([])
let observer = null

/** 默认（空内容）状态下的面板高度：组件样式固定，模块级量一次即可 */
let PANEL_BASE_HEIGHT = 0
/** 是否已恢复过保存的文本域高度（保证 base 先于恢复被测量） */
let restored = false

/* ---------------- 引用标记 ↔ 纯文本 ---------------- */

/** 引用标记：`@#<序号>` */
function mentionToken(index) {
  return `@#${index ?? ''}`
}

/**
 * 纯文本 → 段落节点数组（把 @#序号 还原为 mention 节点）
 * 注意：数组只适合交给 setContent / insertContent 这类「插入内容」的接口
 */
function buildContent(text, mentions) {
  const lines = String(text ?? '').split('\n')
  return lines.map((line) => {
    const content = []
    const re = /@#(\d+)/g
    let last = 0
    let match
    while ((match = re.exec(line))) {
      if (match.index > last) content.push({ type: 'text', text: line.slice(last, match.index) })
      const item = mentions.find((m) => String(m.index) === match[1])
      content.push({
        type: 'mention',
        attrs: {
          id: item?.id ?? mentionToken(match[1]),
          index: Number(match[1]),
          label: item?.label ?? '',
          image: item?.image ?? '',
        },
      })
      last = match.index + match[0].length
    }
    if (last < line.length) content.push({ type: 'text', text: line.slice(last) })
    return content.length ? { type: 'paragraph', content } : { type: 'paragraph' }
  })
}

/**
 * 纯文本 → 初始内容（doc JSON）
 * 必须包成 doc：TipTap 的 createNodeFromContent 对「数组」只会返回 Fragment，
 * 而 EditorState.create 依赖 doc.type.schema，Fragment 没有 type，
 * 会导致 "Cannot read properties of undefined (reading 'schema')"
 */
function buildDocument(text, mentions) {
  return { type: 'doc', content: buildContent(text, mentions) }
}

/** 编辑器内容 → 纯文本提示词（mention 节点还原为 @#序号） */
function serialize(editor) {
  const lines = []
  editor.state.doc.forEach((block) => {
    let line = ''
    block.forEach((child) => {
      if (child.isText) line += child.text
      else if (child.type.name === 'mention') line += mentionToken(child.attrs.index)
      else if (child.type.name === 'hardBreak') line += '\n'
    })
    lines.push(line)
  })
  return lines.join('\n')
}

/* ---------------- 扩展 ---------------- */

/** 候选过滤：序号 / 名称 / 标识都能命中 */
function filterMentions(query) {
  const q = String(query ?? '').toLowerCase()
  if (!q) return props.mentions
  return props.mentions.filter((item) =>
    [item.index, item.label, item.id]
      .filter((v) => v !== null && v !== undefined && v !== '')
      .some((v) => String(v).toLowerCase().includes(q)),
  )
}

/**
 * mention 节点：`@` 与序号分行内标签渲染（@ 单独包一层便于染色），
 * 额外携带 index / image 属性，序列化与展示用
 */
const MentionNode = Mention.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      index: {
        default: null,
        parseHTML: (element) => Number(element.getAttribute('data-index')) || null,
        renderHTML: (attributes) => (attributes.index == null ? {} : { 'data-index': attributes.index }),
      },
      image: {
        default: '',
        parseHTML: (element) => element.getAttribute('data-image') ?? '',
        renderHTML: (attributes) => (attributes.image ? { 'data-image': attributes.image } : {}),
      },
    }
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'span',
      mergeAttributes({ 'data-type': this.name }, this.options.HTMLAttributes, HTMLAttributes),
      ['span', { class: 'prompt-input__at' }, '@'],
      `#${node.attrs.index ?? ''}`,
    ]
  },
})

/** 把文本里所有 @ 字符染蓝（mention 节点内的 @ 由节点样式负责） */
const AtKeyword = Extension.create({
  name: 'atKeyword',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('atKeyword'),
        props: {
          decorations(state) {
            const decorations = []
            state.doc.descendants((node, pos) => {
              if (!node.isText || !node.text?.includes('@')) return
              const re = /@/g
              let match
              while ((match = re.exec(node.text))) {
                decorations.push(
                  Decoration.inline(pos + match.index, pos + match.index + 1, {
                    class: 'prompt-input__at',
                  }),
                )
              }
            })
            return DecorationSet.create(state.doc, decorations)
          },
        },
      }),
    ]
  },
})

/* ---------------- 引用存活性校验 ---------------- */

/** 有效引用 id 集合（未传 validMentionIds 时为 null，表示不校验） */
const validIdSet = computed(() => (props.validMentionIds ? new Set(props.validMentionIds) : null))

/** 引用是否仍然有效：未开启校验时一律视为有效 */
function isMentionAlive(mention) {
  return validIdSet.value ? validIdSet.value.has(mention.id) : true
}

/**
 * 给「来源节点已不存在」的引用加失效标记
 * 引用节点把来源节点 id 存在 attrs.id 里（渲染成 data-id 隐藏信息），
 * 校验只依赖 id，因此不受序号变化影响
 */
const MentionValidity = Extension.create({
  name: 'mentionValidity',

  addProseMirrorPlugins: () => [
    new Plugin({
      key: new PluginKey('mentionValidity'),
      props: {
        decorations(state) {
          const decorations = []
          state.doc.descendants((node, pos) => {
            if (node.type.name !== 'mention' || isMentionAlive(node.attrs)) return
            decorations.push(
              Decoration.node(pos, pos + node.nodeSize, {
                class: 'prompt-input__mention--invalid',
                title: '引用的节点已不存在',
              }),
            )
          })
          return DecorationSet.create(state.doc, decorations)
        },
      },
    }),
  ],
})

/* ---------------- @ 候选列表 ---------------- */

/** open：是否展开；items：候选项；index：高亮项；command：确认回调（由 TipTap 注入） */
const menu = ref({ open: false, items: [], index: 0, command: null })

function closeMenu() {
  menu.value = { ...menu.value, open: false }
}

/** 确认候选项：调用 TipTap 提供的 command，把 @ 查询片段替换为 mention 节点 */
function selectMention(item) {
  if (!item || !menu.value.command) return
  menu.value.command(item)
}

/**
 * 已引用的、仍然有效的节点，用于展示「相关内容」
 * 以编辑器里的引用节点为准（它们带着来源节点 id），并按 id 去重
 */
const referencedMentions = computed(() => {
  const list = []
  const seen = new Set()
  docMentions.value.forEach((mention) => {
    if (seen.has(mention.id) || !isMentionAlive(mention)) return
    seen.add(mention.id)
    // 优先取候选列表里的最新信息，取不到时回退到插入引用时保存的快照
    list.push(props.mentions.find((item) => item.id === mention.id) ?? mention)
  })
  return list
})

/** 已失效的引用（来源节点已不存在），用于提示 */
const invalidMentions = computed(() => docMentions.value.filter((mention) => !isMentionAlive(mention)))

/** 候选项标题：`#序号 名称` */
function mentionTitle(item) {
  const label = item.label || item.id
  return item.index ? `#${item.index} ${label}` : label
}

const suggestion = {
  char: '@',
  // 允许 @ 出现在任意位置（中文提示词里常直接跟在文字后面）
  allowedPrefixes: null,
  items: ({ query }) => filterMentions(query),
  render: () => ({
    onStart: ({ items, command }) => {
      menu.value = { open: true, items, index: 0, command }
    },
    onUpdate: ({ items, command }) => {
      menu.value = { open: true, items, index: 0, command }
    },
    onKeyDown: ({ event }) => {
      const { open, items } = menu.value
      if (!open || !items.length) return false

      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        const step = event.key === 'ArrowDown' ? 1 : -1
        menu.value = { ...menu.value, index: (menu.value.index + step + items.length) % items.length }
        return true
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        selectMention(items[menu.value.index])
        return true
      }
      if (event.key === 'Escape') {
        closeMenu()
        return true
      }
      return false
    },
    onExit: () => closeMenu(),
  }),
  command: ({ editor, range, props: item }) => {
    editor
      .chain()
      .focus()
      .insertContentAt(range, [
        {
          type: 'mention',
          attrs: {
            id: item.id,
            index: item.index ?? null,
            label: item.label ?? '',
            image: item.image ?? '',
          },
        },
        { type: 'text', text: ' ' },
      ])
      .run()
  },
}

/* ---------------- 编辑器 ---------------- */

const editor = useEditor({
  content: buildDocument(props.modelValue, props.mentions),
  extensions: [
    Document,
    Paragraph,
    Text,
    HardBreak,
    History,
    MentionNode.configure({
      HTMLAttributes: { class: 'prompt-input__mention' },
      suggestion,
    }),
    AtKeyword,
    MentionValidity,
  ],
  editorProps: {
    attributes: {
      class: 'prompt-input__editor',
      role: 'textbox',
      'aria-multiline': 'true',
    },
    handleKeyDown(view, event) {
      // 候选列表展开时，方向键 / Enter 交给 @ 补全处理
      if (menu.value.open && menu.value.items.length) return false

      // Enter（无修饰键）提交，Shift + Enter 换行
      const noModifier = !event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey
      if (event.key === 'Enter' && noModifier) {
        if (canSubmit.value) emit('submit')
        return true
      }
      return false
    },
  },
  onCreate: ({ editor }) => {
    syncDocMentions(editor)
  },
  onUpdate: ({ editor }) => {
    emit('update:modelValue', serialize(editor))
    syncDocMentions(editor)
  },
  onBlur: () => closeMenu(),
})

/** 收集编辑器里的引用节点（带 id），供「引用内容展示」与失效校验使用 */
function syncDocMentions(editorInstance) {
  const mentions = []
  editorInstance.state.doc.descendants((node) => {
    if (node.type.name === 'mention') mentions.push({ ...node.attrs })
  })
  docMentions.value = mentions
}

// 外部（父级）改写文本时同步进编辑器；内容一致则跳过，避免打断输入
watch(
  () => props.modelValue,
  (value) => {
    const instance = editor.value
    if (!instance || serialize(instance) === value) return
    instance.commands.setContent(buildContent(value, props.mentions), false)
    syncDocMentions(instance)
  },
)

// 引用存活性变化时：刷新引用节点快照，并派发一次空事务让失效装饰重新计算
watch(
  () => (props.validMentionIds ? props.validMentionIds.join(',') : ''),
  () => {
    const instance = editor.value
    if (!instance || instance.isDestroyed) return
    instance.view.dispatch(instance.state.tr)
    syncDocMentions(instance)
  },
)

/* ---------------- 高度上报 ---------------- */

/** 应用已保存的文本域高度（空值表示回到默认高度） */
function applyHeight(height) {
  if (fieldRef.value) fieldRef.value.style.height = height > 0 ? `${height}px` : ''
}

/**
 * 面板尺寸变化时上报：panel / base / input
 * 首次测量必须发生在应用已保存高度「之前」，量到的才是默认（空内容）状态的面板高度；
 * 应用保存高度会让面板变高，ResizeObserver 会再触发一次上报
 */
function measure() {
  const panel = panelRef.value
  if (!panel) return
  if (!PANEL_BASE_HEIGHT) PANEL_BASE_HEIGHT = panel.offsetHeight
  if (!restored) {
    restored = true
    applyHeight(props.height)
  }
  emit('resize', {
    panel: panel.offsetHeight,
    base: PANEL_BASE_HEIGHT,
    input: fieldRef.value?.offsetHeight ?? 0,
  })
}

onMounted(() => {
  observer = new ResizeObserver(measure)
  if (panelRef.value) observer.observe(panelRef.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})
</script>

<template>
  <!-- nokey：编辑区内的 Delete / Backspace 交给文本处理，vue-flow 不再据此删除节点
       （vue-flow 只认 input/textarea/contenteditable 元素与 .nokey，contenteditable 内部
        的按键目标常常是其中的 <p> 等元素，识别不到） -->
  <div ref="panelRef" class="prompt-input nodrag nokey">
    <!-- 文本域、引用内容、提交按钮共用一个 box：背景、边框、圆角由 box 统一提供 -->
    <div class="prompt-input__box">
      <!-- @ 候选列表：向上弹出，避免超出节点被裁切 -->
      <ul v-if="menu.open && menu.items.length" class="prompt-input__options nowheel">
        <li
          v-for="(item, i) in menu.items"
          :key="item.id"
          class="prompt-input__option"
          :class="{ 'is-active': i === menu.index }"
          @mousedown.prevent="selectMention(item)"
          @mouseenter="menu.index = i"
        >
          <img
            v-if="item.image"
            class="prompt-input__thumb"
            :src="item.image"
            alt=""
            draggable="false"
          />
          <span v-else class="prompt-input__thumb prompt-input__thumb--empty" />
          <span class="prompt-input__option-label">{{ mentionTitle(item) }}</span>
        </li>
      </ul>

      <!-- 富文本输入区：可纵向拖拽调节高度 -->
      <div
        ref="fieldRef"
        class="prompt-input__field"
        :style="{ '--mention-color': mentionColor }"
      >
        <EditorContent :editor="editor" />
        <span v-if="isEmpty" class="prompt-input__placeholder">{{ placeholder }}</span>
      </div>

      <!-- 已引用的上游节点：缩略图 + 序号 -->
      <ul v-if="referencedMentions.length" class="prompt-input__referenced">
        <li
          v-for="item in referencedMentions"
          :key="item.id"
          class="prompt-input__reference"
          :title="mentionTitle(item)"
        >
          <img
            v-if="item.image"
            class="prompt-input__thumb"
            :src="item.image"
            alt=""
            draggable="false"
          />
          <span v-else class="prompt-input__thumb prompt-input__thumb--empty" />
          <span v-if="item.index" class="prompt-input__reference-seq">#{{ item.index }}</span>
        </li>
      </ul>

      <!-- 引用的节点已被删除：提示重新选择 -->
      <p v-if="invalidMentions.length" class="prompt-input__warning">
        有 {{ invalidMentions.length }} 处引用的节点已不存在，建议重新选择上游节点
      </p>

      <button
        class="prompt-input__submit"
        type="button"
        :disabled="!canSubmit"
        @click="emit('submit')"
      >
        {{ submitText }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.prompt-input {
  padding: 8px;
  border-top: 1px solid var(--border2, #343c4c);
  background: var(--surface-2, #1b2029);
}

/* 统一 box：文本域、引用内容与提交按钮的公共容器，背景与边框都在这里 */
.prompt-input__box {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  background: #0f131a;
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  transition: border-color 0.15s ease;
}

/* 聚焦态由 box 整体反馈（输入区自身无边框） */
.prompt-input__box:focus-within {
  border-color: var(--accent, #f0a63d);
}

/* ---------------- 富文本输入区 ---------------- */

.prompt-input__field {
  position: relative;
  box-sizing: border-box;
  /* 可纵向拖拽调节高度，上下限避免内容区被挤没 / 溢出容器 */
  min-height: 44px;
  max-height: 200px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text, #e9edf5);
  overflow-y: auto;
  resize: vertical;
}

/* 编辑器根元素（.prompt-input__editor 由 editorProps.attributes 指定） */
.prompt-input__field :deep(.prompt-input__editor) {
  outline: none;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  word-break: break-word;
}

.prompt-input__field :deep(.prompt-input__editor p) {
  margin: 0;
}

.prompt-input__placeholder {
  position: absolute;
  top: 0;
  left: 0;
  color: var(--muted, #767f92);
  pointer-events: none;
}

/* @ 字符与引用标记统一蓝色 */
.prompt-input__field :deep(.prompt-input__at) {
  color: var(--mention-color, #4f9cf9);
  font-weight: 600;
}

.prompt-input__field :deep(.prompt-input__mention) {
  color: var(--mention-color, #4f9cf9);
  background: rgba(79, 156, 249, 0.14);
  font-weight: 600;
  border-radius: 4px;
  padding: 0 2px;
  cursor: default;
}

.prompt-input__field :deep(.prompt-input__mention.ProseMirror-selectednode) {
  background: rgba(79, 156, 249, 0.32);
}

/* 引用的来源节点已被删除：置灰 + 删除线提示失效 */
.prompt-input__field :deep(.prompt-input__mention--invalid) {
  color: var(--muted, #767f92);
  background: rgba(229, 72, 77, 0.14);
  text-decoration: line-through;
  cursor: help;
}

.prompt-input__field :deep(.prompt-input__mention--invalid .prompt-input__at) {
  color: inherit;
}

/* ---------------- @ 候选列表 ---------------- */

.prompt-input__options {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 30;
  max-height: 160px;
  margin: 0;
  padding: 4px;
  overflow-y: auto;
  list-style: none;
  background: var(--surface, #151922);
  border: 1px solid var(--border2, #343c4c);
  border-radius: var(--r-sm, 6px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55);
}

.prompt-input__option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  font-size: 12px;
  color: var(--text, #e9edf5);
  border-radius: 4px;
  cursor: pointer;
}

.prompt-input__option.is-active {
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
}

.prompt-input__option-label {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.prompt-input__thumb {
  flex: none;
  display: block;
  width: 22px;
  height: 22px;
  object-fit: cover;
  border: 1px solid var(--border2, #343c4c);
  border-radius: 4px;
  background: #0d1117;
}

/* 无图时用点阵占位 */
.prompt-input__thumb--empty {
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.12) 1px, transparent 1px);
  background-size: 6px 6px;
}

/* ---------------- 已引用的上游节点 ---------------- */

.prompt-input__referenced {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.prompt-input__reference {
  position: relative;
}

.prompt-input__reference-seq {
  position: absolute;
  right: -2px;
  bottom: -2px;
  padding: 0 3px;
  font-size: 9px;
  line-height: 12px;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border-radius: 999px;
}

/* ---------------- 失效引用提示 ---------------- */

.prompt-input__warning {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: #ff7a7a;
}

/* ---------------- 提交按钮 ---------------- */

.prompt-input__submit {
  flex: none;
  box-sizing: border-box;
  width: 100%;
  height: 34px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-ink, #201404);
  background: var(--accent, #f0a63d);
  border: none;
  border-radius: var(--r-sm, 6px);
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.prompt-input__submit:hover:not(:disabled) {
  opacity: 0.88;
}

.prompt-input__submit:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}
</style>
