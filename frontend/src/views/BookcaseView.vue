<template>
  <section class="bookcase" aria-label="我的书架">
    <!-- ── 正常模式工具栏 ───────────────────────────────────── -->
    <div v-if="!isManaging" class="toolbar">
      <div class="search-wrap">
        <span class="search-icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
        </span>
        <input
          id="bookcase-search"
          v-model="keyword"
          type="search"
          class="search-input"
          placeholder="搜索书架..."
          aria-label="搜索书架中的书籍"
          @input="onSearch"
        />
      </div>

      <div class="toolbar-actions">
        <!-- 批量管理按钮（仅在有书时可用） -->
        <button
          v-if="books.length > 0"
          id="bookcase-manage-btn"
          class="btn-manage"
          aria-label="管理书架"
          @click="startManaging"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 11 12 14 22 4"/>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
          </svg>
          批量管理
        </button>

        <router-link to="/import" class="btn-import" id="bookcase-import-btn" aria-label="导入新书籍">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          导入书籍
        </router-link>
      </div>
    </div>

    <!-- ── 管理模式专属操作栏 ───────────────────────────────── -->
    <div v-else class="manage-bar" role="toolbar" aria-label="书架管理工具栏">
      <div class="manage-info">
        <span class="manage-badge">管理模式</span>
        <span class="manage-count">
          已选择 <strong class="highlight-count">{{ selectedIds.size }}</strong> / {{ books.length }} 本
        </span>
      </div>

      <div class="manage-actions">
        <button
          class="btn-manage-action"
          id="manage-toggle-all-btn"
          @click="toggleSelectAll"
        >
          {{ isAllSelected ? '取消全选' : '全选' }}
        </button>

        <button
          class="btn-manage-action btn-danger"
          id="manage-delete-btn"
          :disabled="selectedIds.size === 0 || deleting"
          @click="confirmBatchDelete"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          移出书架 ({{ selectedIds.size }})
        </button>

        <button
          class="btn-manage-done"
          id="manage-done-btn"
          @click="exitManaging"
        >
          完成
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="books.length === 0 && !loading" class="empty-state" aria-live="polite">
      <div class="empty-icon" aria-hidden="true">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="8" y="8" width="20" height="48" rx="3" fill="var(--color-accent)" opacity="0.15"/>
          <rect x="8" y="8" width="20" height="48" rx="3" stroke="var(--color-accent)" stroke-width="1.5" opacity="0.4"/>
          <rect x="32" y="12" width="20" height="44" rx="3" fill="var(--color-accent)" opacity="0.1"/>
          <rect x="32" y="12" width="20" height="44" rx="3" stroke="var(--color-accent)" stroke-width="1.5" opacity="0.25"/>
          <line x1="12" y1="20" x2="24" y2="20" stroke="var(--color-accent)" stroke-width="1.5" opacity="0.5" stroke-linecap="round"/>
          <line x1="12" y1="25" x2="24" y2="25" stroke="var(--color-accent)" stroke-width="1.5" opacity="0.35" stroke-linecap="round"/>
          <line x1="12" y1="30" x2="20" y2="30" stroke="var(--color-accent)" stroke-width="1.5" opacity="0.25" stroke-linecap="round"/>
        </svg>
      </div>
      <p class="empty-title">书架还是空的</p>
      <p class="empty-desc">导入 TXT、EPUB 或搜索添加网络书籍，开启阅读体验</p>
      <router-link to="/import" class="btn-import empty-cta" id="empty-import-btn">导入第一本书</router-link>
    </div>

    <!-- 骨架屏 -->
    <div v-else-if="loading && books.length === 0" class="book-grid" aria-hidden="true">
      <div v-for="n in 8" :key="n" class="book-card skeleton-card">
        <div class="cover-wrap skeleton-cover"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line skeleton-line-short"></div>
      </div>
    </div>

    <!-- 书格 -->
    <div v-else class="book-grid" :class="{ 'is-managing-grid': isManaging }" role="list" aria-label="书籍列表">
      <article
        v-for="(book, index) in books"
        :key="book.uuid || book.id"
        class="book-card"
        :class="{
          'is-selected': isManaging && isSelected(book),
          'is-manage-mode': isManaging
        }"
        role="listitem"
        :style="{ '--delay': `${index * 25}ms` }"
        tabindex="0"
        :aria-label="isManaging ? `选择《${book.name}》` : `打开《${book.name}》`"
        @click="onCardClick(book)"
        @keydown.enter="onCardClick(book)"
      >
        <div class="cover-wrap">
          <img
            v-if="book.cover && !failedCovers.has(getBookKey(book))"
            :src="coverUrl(book.uuid || book.id!)"
            class="cover"
            :alt="`《${book.name}》封面`"
            loading="lazy"
            @error="handleCoverError(book)"
          />
          <div v-else class="cover cover-placeholder" :style="placeholderStyle(book.name)">
            <div class="placeholder-spine"></div>
            <div class="placeholder-border"></div>
            <span class="placeholder-text">{{ (book.name || '书').slice(0, 4) }}</span>
            <span v-if="book.author" class="placeholder-author">{{ book.author }}</span>
          </div>
          <div class="cover-overlay"></div>

          <!-- 更新角标 -->
          <span v-if="book.hasUpdate && !isManaging" class="badge" aria-label="有更新">新</span>

          <!-- 管理模式下：勾选指示器 -->
          <div v-if="isManaging" class="select-indicator" :class="{ active: isSelected(book) }">
            <svg v-if="isSelected(book)" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>

          <!-- 普通模式下：快捷移出按钮（悬浮出现） -->
          <button
            v-if="!isManaging"
            class="btn-quick-delete"
            :title="`移出《${book.name}》`"
            :aria-label="`移出《${book.name}》`"
            @click.stop="confirmSingleDelete(book)"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>

        <div class="info">
          <div class="name" :title="book.name">{{ book.name }}</div>
          <div class="author">{{ book.author || '佚名' }}</div>
        </div>
      </article>
    </div>

    <!-- 加载更多 -->
    <div v-if="total > books.length && !loading && !isManaging" class="load-more">
      <button class="btn-load-more" id="load-more-btn" @click="loadMore">
        查看更多 ({{ total - books.length }})
      </button>
    </div>

    <!-- 追加加载中 -->
    <div v-if="loading && books.length > 0" class="loading-more" aria-live="polite">
      <div class="loading-dots">
        <span></span><span></span><span></span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listBooks, coverUrl, deleteBook, batchDeleteBooks } from '@/api'
import type { Book } from '@/types'

const router = useRouter()
const keyword = ref('')
const books = ref<Book[]>([])
const total = ref(0)
const page = ref(0)
const loading = ref(false)
const failedCovers = ref<Set<string | number>>(new Set())
let timer: number | undefined

function handleCoverError(book: Book) {
  failedCovers.value.add(getBookKey(book))
}

// ── 管理状态 ─────────────────────────────────────────────
const isManaging = ref(false)
const selectedIds = ref<Set<string | number>>(new Set())
const deleting = ref(false)

const isAllSelected = computed(() => {
  if (books.value.length === 0) return false
  return books.value.every((b) => isSelected(b))
})

function getBookKey(book: Book): string | number {
  return book.uuid || book.id!
}

function isSelected(book: Book): boolean {
  return selectedIds.value.has(getBookKey(book))
}

function startManaging() {
  isManaging.value = true
  selectedIds.value = new Set()
}

function exitManaging() {
  isManaging.value = false
  selectedIds.value = new Set()
}

function toggleSelect(book: Book) {
  const key = getBookKey(book)
  const next = new Set(selectedIds.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  selectedIds.value = next
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = new Set()
  } else {
    const next = new Set<string | number>()
    books.value.forEach((b) => next.add(getBookKey(b)))
    selectedIds.value = next
  }
}

// ── 点击卡片 ─────────────────────────────────────────────
function onCardClick(book: Book) {
  if (isManaging.value) {
    toggleSelect(book)
  } else {
    openBook(book)
  }
}

function openBook(book: Book) {
  router.push({ name: 'read', params: { book: book.uuid || String(book.id) } })
}

// ── 单本删除 ─────────────────────────────────────────────
async function confirmSingleDelete(book: Book) {
  try {
    await ElMessageBox.confirm(`确认将《${book.name}》移出书架吗？`, '移出书架', {
      confirmButtonText: '移出',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'bookcase-confirm-box',
    })
  } catch {
    return
  }

  try {
    await deleteBook(book.uuid || book.id!)
    ElMessage.success(`已移出《${book.name}》`)
    fetchBooks(true)
  } catch (e: any) {
    ElMessage.error(e.message || '移出失败')
  }
}

// ── 批量删除 ─────────────────────────────────────────────
async function confirmBatchDelete() {
  const count = selectedIds.value.size
  if (count === 0) return

  try {
    await ElMessageBox.confirm(`确认将选中的 ${count} 本书籍移出书架吗？`, '批量移出', {
      confirmButtonText: `移出 (${count})`,
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'bookcase-confirm-box',
    })
  } catch {
    return
  }

  deleting.value = true
  try {
    const ids = Array.from(selectedIds.value)
    const res = await batchDeleteBooks(ids)
    ElMessage.success(`已成功移出 ${res?.count || count} 本书籍`)
    selectedIds.value = new Set()
    await fetchBooks(true)
    if (books.value.length === 0) {
      isManaging.value = false
    }
  } catch (e: any) {
    ElMessage.error(e.message || '批量移出失败')
  } finally {
    deleting.value = false
  }
}

// ── 基于书名生成不重复的暖色渐变 ─────────────────────────
const GRADIENTS = [
  ['#c0692e', '#8b3a10'], // 棕红
  ['#2e7d6e', '#1a4a42'], // 墨绿
  ['#b8863a', '#7a5520'], // 金棕
  ['#5c4a8a', '#3a2e5c'], // 深紫（偏蓝）
  ['#2e6b8a', '#1a3d52'], // 深蓝
  ['#8a4a2e', '#5c2810'], // 赭石
  ['#4a7a3a', '#2c4e22'], // 苔绿
  ['#7a4a6a', '#4e2842'], // 烟紫
]

function placeholderStyle(name: string): Record<string, string> {
  const idx = name.charCodeAt(0) % GRADIENTS.length
  const [from, to] = GRADIENTS[idx]
  return {
    background: `linear-gradient(145deg, ${from}, ${to})`,
  }
}

async function fetchBooks(reset = false) {
  if (reset) {
    page.value = 0
    books.value = []
  }
  loading.value = true
  try {
    const res = await listBooks(keyword.value, undefined, page.value, 30)
    total.value = res.total
    books.value = reset ? res.items : [...books.value, ...res.items]
  } catch (e: any) {
    ElMessage.error(e.message || '加载书架失败')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  window.clearTimeout(timer)
  timer = window.setTimeout(() => fetchBooks(true), 300)
}

function loadMore() {
  page.value += 1
  fetchBooks()
}

onMounted(() => fetchBooks(true))
</script>

<style scoped>
/* ─── 布局 ────────────────────────────────────────────────── */
.bookcase {
  padding: 24px 28px;
  max-width: 1280px;
  margin: 0 auto;
  min-height: 100%;
}

/* ─── 普通模式工具栏 ──────────────────────────────────────── */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.search-wrap {
  position: relative;
  flex: 1;
  max-width: 360px;
  min-width: 200px;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 9px 12px 9px 38px;
  border: 1.5px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-family: var(--font-ui);
  font-size: 14px;
  outline: none;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
  box-sizing: border-box;
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.search-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-pale);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 管理按钮 */
.btn-manage {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color var(--transition-base), color var(--transition-base), background var(--transition-base);
  white-space: nowrap;
}

.btn-manage:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-pale);
}

.btn-import {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: var(--color-accent);
  color: #fff;
  border-radius: var(--radius-lg);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.02em;
  white-space: nowrap;
  transition:
    background var(--transition-base),
    transform var(--transition-fast),
    box-shadow var(--transition-base);
  flex-shrink: 0;
}

.btn-import:hover {
  background: var(--color-accent-light);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.btn-import:active {
  transform: translateY(0) scale(0.97);
}

/* ─── 管理模式专属操作栏 ─────────────────────────────────── */
.manage-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 20px;
  background: var(--color-surface);
  border: 1.5px solid var(--color-accent-pale);
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 20px rgba(184, 134, 58, 0.1);
  margin-bottom: 28px;
  animation: bar-slide var(--transition-base) both;
  flex-wrap: wrap;
}

@keyframes bar-slide {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.manage-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.manage-badge {
  padding: 3px 9px;
  background: var(--color-accent);
  color: #fff;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.manage-count {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.highlight-count {
  color: var(--color-accent);
  font-weight: 700;
}

.manage-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-manage-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: var(--color-bg-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-manage-action:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-pale);
}

.btn-manage-action.btn-danger {
  color: #d9534f;
  border-color: rgba(217, 83, 79, 0.25);
  background: rgba(217, 83, 79, 0.06);
}

.btn-manage-action.btn-danger:hover:not(:disabled) {
  background: rgba(217, 83, 79, 0.15);
  border-color: #d9534f;
  color: #d9534f;
}

.btn-manage-action:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-manage-done {
  padding: 7px 18px;
  background: var(--color-accent);
  border: none;
  border-radius: var(--radius-md);
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast), transform var(--transition-fast);
}

.btn-manage-done:hover {
  background: var(--color-accent-light);
  transform: translateY(-1px);
}

/* ─── 空状态 ──────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  gap: 12px;
}

.empty-icon {
  margin-bottom: 8px;
  opacity: 0.85;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
  text-wrap: balance;
}

.empty-cta {
  margin-top: 8px;
}

/* ─── 书格 ────────────────────────────────────────────────── */
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
  gap: 24px 18px;
}

/* ─── 书卡 ────────────────────────────────────────────────── */
.book-card {
  cursor: pointer;
  animation: card-in var(--transition-slow) var(--delay, 0ms) both;
  position: relative;
  user-select: none;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.book-card:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 4px;
  border-radius: var(--radius-md);
}

.cover-wrap {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 3 / 4;
  box-shadow: var(--shadow-md);
  transition:
    box-shadow var(--transition-base),
    transform var(--transition-slow),
    border-color var(--transition-base);
}

/* 普通悬浮效果 */
.book-card:not(.is-manage-mode):hover .cover-wrap {
  transform: translateY(-5px) scale(1.02);
  box-shadow: var(--shadow-lg), 0 12px 30px rgba(184, 134, 58, 0.15);
}

/* 管理模式选中状态 */
.book-card.is-selected .cover-wrap {
  box-shadow: 0 0 0 3px var(--color-accent), var(--shadow-lg);
  transform: scale(0.97);
}

.cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 245, 220, 0);
  transition: background var(--transition-base);
}

.book-card:hover .cover-overlay {
  background: rgba(255, 245, 220, 0.06);
}

.cover-placeholder {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 12px 10px;
  box-sizing: border-box;
  overflow: hidden;
  text-align: center;
}

.placeholder-spine {
  position: absolute;
  left: 6px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(255, 255, 255, 0.18);
  box-shadow: 1px 0 2px rgba(0, 0, 0, 0.25);
}

.placeholder-border {
  position: absolute;
  inset: 7px 7px 7px 11px;
  border: 1px solid rgba(255, 248, 220, 0.28);
  border-radius: 3px;
  pointer-events: none;
}

.placeholder-text {
  font-family: var(--font-serif, "'Noto Serif SC', 'Songti SC', serif");
  font-size: 15px;
  font-weight: 700;
  color: rgba(255, 248, 220, 0.95);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
  letter-spacing: 0.08em;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  z-index: 1;
}

.placeholder-author {
  font-size: 10px;
  color: rgba(255, 248, 220, 0.7);
  margin-top: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 90%;
  z-index: 1;
}

.badge {
  position: absolute;
  top: 7px;
  right: 7px;
  background: #c0692e;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.05em;
}

/* ─── 勾选指示器（管理模式）──────────────────────────────── */
.select-indicator {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.45);
  border: 2px solid #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: all var(--transition-fast);
  backdrop-filter: blur(4px);
}

.select-indicator.active {
  background: var(--color-accent);
  border-color: #fff;
  box-shadow: 0 2px 8px rgba(184, 134, 58, 0.5);
  transform: scale(1.08);
}

/* ─── 快捷删除按钮（普通模式悬停）────────────────────────── */
.btn-quick-delete {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: none;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transform: scale(0.85);
  transition: opacity var(--transition-fast), transform var(--transition-fast), background var(--transition-fast);
  backdrop-filter: blur(4px);
  z-index: 5;
}

.book-card:hover .btn-quick-delete {
  opacity: 1;
  transform: scale(1);
}

.btn-quick-delete:hover {
  background: #d9534f;
  transform: scale(1.1);
}

/* ─── 书籍信息 ────────────────────────────────────────────── */
.info {
  margin-top: 10px;
}

.name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.author {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ─── 骨架屏 ──────────────────────────────────────────────── */
.skeleton-card {
  cursor: default;
  animation: none;
}

.skeleton-cover {
  border-radius: var(--radius-md);
  aspect-ratio: 3 / 4;
  background: linear-gradient(90deg, var(--color-bg-subtle) 25%, var(--color-surface) 50%, var(--color-bg-subtle) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-line {
  height: 10px;
  margin-top: 10px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--color-bg-subtle) 25%, var(--color-surface) 50%, var(--color-bg-subtle) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-line-short {
  width: 65%;
  height: 8px;
  margin-top: 6px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ─── 加载更多 ────────────────────────────────────────────── */
.load-more {
  text-align: center;
  margin-top: 32px;
}

.btn-load-more {
  padding: 9px 24px;
  background: transparent;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  font-family: var(--font-ui);
  font-size: 13px;
  cursor: pointer;
  transition: border-color var(--transition-base), color var(--transition-base), background var(--transition-base);
}

.btn-load-more:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-pale);
}

/* ─── 追加加载中 ──────────────────────────────────────────── */
.loading-more {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

.loading-dots {
  display: flex;
  gap: 6px;
  align-items: center;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dot-bounce 1.2s ease-in-out infinite;
}

.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* ─── 移动端响应式适配 (<= 768px) ────────────────────────── */
@media (max-width: 768px) {
  .bookcase {
    padding: 16px 12px 24px;
  }

  .toolbar {
    margin-bottom: 16px;
    gap: 10px;
  }

  .search-wrap {
    max-width: 100%;
    min-width: 0;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: space-between;
  }

  .btn-manage, .btn-import {
    flex: 1;
    justify-content: center;
    padding: 8px 12px;
    font-size: 13px;
  }

  .manage-bar {
    padding: 10px 14px;
    margin-bottom: 16px;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .manage-actions {
    justify-content: space-between;
    width: 100%;
  }

  .btn-manage-action {
    flex: 1;
    justify-content: center;
    padding: 6px 8px;
    font-size: 12px;
  }

  .btn-manage-done {
    padding: 6px 14px;
    font-size: 12px;
  }

  .book-grid {
    grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
    gap: 16px 10px;
  }

  .book-title {
    font-size: 13px;
  }

  .book-author {
    font-size: 11px;
  }
}
</style>