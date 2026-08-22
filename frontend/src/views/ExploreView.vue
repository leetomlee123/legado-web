<template>
  <div class="explore-page" role="main" aria-label="书源探索发现">
    <!-- ── 顶部书源与工具栏 ───────────────────────────────────── -->
    <header class="explore-header">
      <div class="header-top-row">
        <div class="explore-title-group">
          <h1 class="explore-title">探索发现</h1>
          <span v-if="sources.length > 0" class="source-count-badge">
            {{ sources.length }} 个可用书源
          </span>
        </div>

        <div class="source-selector-wrap">
          <el-select
            v-model="currentSourceId"
            placeholder="选择书源..."
            filterable
            class="source-select"
            @change="onSourceChange"
          >
            <el-option
              v-for="s in sources"
              :key="s.id"
              :label="`${s.name} (${s.exploreItems.filter(it => it.url).length} 分类)`"
              :value="s.id"
            >
              <div class="source-option-item">
                <span class="opt-name">{{ s.name }}</span>
                <span class="opt-group">{{ s.group || '默认' }}</span>
              </div>
            </el-option>
          </el-select>
        </div>
      </div>

      <!-- ── 分类与榜单标签栏 ───────────────────────────────── -->
      <nav v-if="validCategories.length > 0" class="category-nav-wrap" aria-label="探索分类">
        <div class="category-scroll-container">
          <button
            v-for="(cat, idx) in validCategories"
            :key="idx"
            class="category-tab"
            :class="{ 'is-active': selectedCategoryUrl === cat.url }"
            @click="selectCategory(cat)"
          >
            <span class="cat-title">{{ cat.title }}</span>
          </button>
        </div>
      </nav>
    </header>

    <!-- ── 内容区 ───────────────────────────────────────────── -->
    <main class="explore-main">
      <!-- 初始全页加载中 -->
      <div v-if="initialLoading" class="skeleton-grid" aria-busy="true">
        <div v-for="n in 12" :key="n" class="skeleton-card">
          <div class="sk-cover"></div>
          <div class="sk-title"></div>
          <div class="sk-author"></div>
        </div>
      </div>

      <!-- 无书源或书源无探索规则 -->
      <div v-else-if="sources.length === 0" class="empty-state">
        <div class="empty-icon" aria-hidden="true">🧭</div>
        <h2 class="empty-title">暂无可探索的书源</h2>
        <p class="empty-desc">当前启用的书源中未配置 exploreUrl 发现规则，请先导入支持探索的书源</p>
        <router-link to="/sources" class="btn-primary-action">前往书源管理</router-link>
      </div>

      <!-- 分类内容为空 -->
      <div v-else-if="!loading && books.length === 0" class="empty-state">
        <div class="empty-icon" aria-hidden="true">📭</div>
        <h2 class="empty-title">暂未获取到书籍</h2>
        <p class="empty-desc">该分类暂无内容或书源网络响应超时，建议尝试切换其他分类或书源</p>
        <button class="btn-primary-action" @click="loadBooks(1)">重新加载</button>
      </div>

      <!-- 书籍流网格 -->
      <div v-else class="book-flow-container">
        <div class="books-grid">
          <article
            v-for="(book, idx) in books"
            :key="idx"
            class="explore-book-card"
            tabindex="0"
            @click="openBookModal(book)"
            @keydown.enter="openBookModal(book)"
          >
            <div class="cover-wrapper">
              <img
                v-if="book.cover && !failedCovers.has(book.name + book.author)"
                :src="book.cover"
                :alt="`《${book.name}》封面`"
                class="book-cover-img"
                loading="lazy"
                @error="failedCovers.add(book.name + book.author)"
              />
              <div v-else class="book-cover-fallback" :style="placeholderBg(book.name)">
                <div class="fb-spine"></div>
                <div class="fb-border"></div>
                <span class="fb-text">{{ (book.name || '书').slice(0, 4) }}</span>
                <span v-if="book.author" class="fb-author">{{ book.author }}</span>
              </div>
              <span v-if="book.kind" class="kind-tag">{{ book.kind.split(',')[0] }}</span>
            </div>

            <div class="book-info">
              <h3 class="book-name" :title="book.name">{{ book.name }}</h3>
              <p class="book-author" :title="book.author">{{ book.author || '佚名' }}</p>
              <p v-if="book.last_chapter" class="book-last-chapter" :title="book.last_chapter">
                {{ book.last_chapter }}
              </p>
            </div>
          </article>
        </div>

        <!-- 加载更多 -->
        <div v-if="hasMore && !loading" class="load-more-section">
          <button class="btn-load-more" @click="loadNextPage">
            加载下一页 (第 {{ page + 1 }} 页)
          </button>
        </div>

        <div v-if="loading && books.length > 0" class="loading-indicator" aria-live="polite">
          <div class="dot-spin">
            <span></span><span></span><span></span>
          </div>
          <span class="loading-tip">正在探索更多书籍...</span>
        </div>
      </div>
    </main>

    <!-- ── 书籍详情快捷弹窗 ───────────────────────────────── -->
    <el-dialog
      v-model="showBookModal"
      title="书籍概览"
      width="480px"
      class="book-detail-dialog"
      destroy-on-close
      append-to-body
    >
      <div v-if="selectedBook" class="modal-book-detail">
        <div class="modal-top">
          <div class="modal-cover-wrap">
            <img
              v-if="selectedBook.cover && !failedCovers.has(selectedBook.name + selectedBook.author)"
              :src="selectedBook.cover"
              :alt="selectedBook.name"
              class="modal-cover"
            />
            <div v-else class="modal-cover modal-cover-fallback" :style="placeholderBg(selectedBook.name)">
              <span>{{ (selectedBook.name || '书').slice(0, 4) }}</span>
            </div>
          </div>

          <div class="modal-meta">
            <h3 class="modal-title">{{ selectedBook.name }}</h3>
            <p class="modal-author">作者：{{ selectedBook.author || '未知' }}</p>
            <p class="modal-source">来源：{{ selectedBook.source_name || currentSource?.name }}</p>
            <p v-if="selectedBook.kind" class="modal-kind">类型：{{ selectedBook.kind }}</p>
            <p v-if="selectedBook.last_chapter" class="modal-chapter">最新：{{ selectedBook.last_chapter }}</p>
          </div>
        </div>

        <div v-if="selectedBook.intro" class="modal-intro">
          <h4>作品简介</h4>
          <p>{{ selectedBook.intro }}</p>
        </div>

        <div class="modal-actions">
          <button
            class="btn-action-read"
            :disabled="actionLoading"
            @click="startReading(selectedBook)"
          >
            立即阅读
          </button>

          <button
            class="btn-action-shelf"
            :disabled="actionLoading || isBookInShelf(selectedBook)"
            @click="addToShelf(selectedBook)"
          >
            {{ isBookInShelf(selectedBook) ? '已在书架' : '+ 加入书架' }}
          </button>

          <button
            class="btn-action-search"
            @click="searchGlobal(selectedBook)"
          >
            全网搜书
          </button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchExploreSources, fetchExploreBooks, listBooks } from '@/api'
import { getMutedCoverStyle } from '@/utils/cover'
import http from '@/utils/http'
import type { ExploreSource, ExploreBook, ExploreItem, Book } from '@/types'

const router = useRouter()

const sources = ref<ExploreSource[]>([])
const currentSourceId = ref<number | null>(null)
const selectedCategoryUrl = ref<string>('')
const selectedCategoryTitle = ref<string>('')

const books = ref<ExploreBook[]>([])
const page = ref(1)
const hasMore = ref(false)
const initialLoading = ref(true)
const loading = ref(false)
const actionLoading = ref(false)

const failedCovers = reactive(new Set<string>())
const shelfBookNames = reactive(new Set<string>())

const showBookModal = ref(false)
const selectedBook = ref<ExploreBook | null>(null)

const currentSource = computed(() => {
  return sources.value.find(s => s.id === currentSourceId.value) || null
})

const validCategories = computed<ExploreItem[]>(() => {
  if (!currentSource.value) return []
  return currentSource.value.exploreItems.filter(it => Boolean(it.url))
})

const placeholderBg = getMutedCoverStyle

async function loadShelfBooks() {
  try {
    const res = await listBooks('', '', 0, 1000)
    shelfBookNames.clear()
    res.items?.forEach((b: Book) => {
      shelfBookNames.add(b.name)
    })
  } catch (e) {
    // ignore
  }
}

function isBookInShelf(book: ExploreBook | null): boolean {
  if (!book) return false
  return shelfBookNames.has(book.name)
}

async function loadSources() {
  initialLoading.value = true
  try {
    const list = await fetchExploreSources()
    // 仅保留有有效分类链接的书源
    sources.value = list.filter(s => s.exploreItems.some(it => Boolean(it.url)))

    if (sources.value.length > 0) {
      currentSourceId.value = sources.value[0].id
      const firstCat = sources.value[0].exploreItems.find(it => Boolean(it.url))
      if (firstCat) {
        selectedCategoryUrl.value = firstCat.url
        selectedCategoryTitle.value = firstCat.title
        await loadBooks(1)
      }
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载书源探索规则失败')
  } finally {
    initialLoading.value = false
  }
}

async function onSourceChange(sid: number) {
  currentSourceId.value = sid
  const src = currentSource.value
  if (!src) return
  const firstCat = src.exploreItems.find(it => Boolean(it.url))
  if (firstCat) {
    selectedCategoryUrl.value = firstCat.url
    selectedCategoryTitle.value = firstCat.title
    await loadBooks(1)
  } else {
    books.value = []
  }
}

function selectCategory(cat: ExploreItem) {
  if (selectedCategoryUrl.value === cat.url && books.value.length > 0) return
  selectedCategoryUrl.value = cat.url
  selectedCategoryTitle.value = cat.title
  loadBooks(1)
}

async function loadBooks(pageNum: number) {
  if (!currentSourceId.value || !selectedCategoryUrl.value) return
  loading.value = true
  if (pageNum === 1) {
    books.value = []
  }

  try {
    const res = await fetchExploreBooks(currentSourceId.value, selectedCategoryUrl.value, pageNum)
    if (pageNum === 1) {
      books.value = res.books || []
    } else {
      books.value.push(...(res.books || []))
    }
    page.value = pageNum
    hasMore.value = res.hasMore && (res.books?.length || 0) > 0
  } catch (e: any) {
    ElMessage.warning(e.message || '抓取探索书籍失败')
  } finally {
    loading.value = false
  }
}

function loadNextPage() {
  if (loading.value || !hasMore.value) return
  loadBooks(page.value + 1)
}

function openBookModal(book: ExploreBook) {
  selectedBook.value = book
  showBookModal.value = true
}

async function addToShelf(book: ExploreBook) {
  actionLoading.value = true
  try {
    await http.post('/books/from-search', {
      name: book.name,
      author: book.author,
      cover: book.cover,
      intro: book.intro,
      bookUrl: book.book_url,
      sourceId: book.source_id,
      inBookcase: true,
    })
    shelfBookNames.add(book.name)
    ElMessage.success(`《${book.name}》已成功加入书架`)
  } catch (e: any) {
    ElMessage.error(e.message || '加入书架失败')
  } finally {
    actionLoading.value = false
  }
}

async function startReading(book: ExploreBook) {
  actionLoading.value = true
  try {
    const res: any = await http.post('/books/init-preview', {
      name: book.name,
      author: book.author,
      cover: book.cover,
      intro: book.intro,
      bookUrl: book.book_url,
      sourceId: book.source_id,
      inBookcase: false,
    })
    showBookModal.value = false
    const bookId = res?.uuid || res?.id
    if (bookId) {
      router.push(`/read/${bookId}`)
    } else {
      ElMessage.error('初始化阅读失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '进入阅读失败')
  } finally {
    actionLoading.value = false
  }
}

function searchGlobal(book: ExploreBook) {
  showBookModal.value = false
  router.push({
    path: '/search',
    query: { q: book.name },
  })
}

onMounted(() => {
  loadShelfBooks()
  loadSources()
})
</script>

<style scoped>
/* ─── 探索页面主容器 ────────────────────────────────────────── */
.explore-page {
  padding: 20px 24px 60px;
  max-width: 1240px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ─── 顶部工具栏 ────────────────────────────────────────────── */
.explore-header {
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.explore-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.explore-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

.source-count-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  background: var(--color-accent-pale);
  color: var(--color-accent);
  border-radius: 99px;
  font-size: 11.5px;
  font-weight: 600;
}

.source-selector-wrap {
  min-width: 240px;
}

.source-option-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.opt-name {
  font-weight: 500;
  color: var(--color-text-primary);
}

.opt-group {
  font-size: 11px;
  color: var(--color-text-muted);
}

/* ─── 分类标签横向滑动栏 ────────────────────────────────────── */
.category-nav-wrap {
  width: 100%;
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 12px;
}

.category-scroll-container {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  white-space: nowrap;
  padding-bottom: 4px;
  -webkit-overflow-scrolling: touch;
}

.category-scroll-container::-webkit-scrollbar {
  height: 4px;
}

.category-scroll-container::-webkit-scrollbar-thumb {
  background: var(--color-border-subtle);
  border-radius: 4px;
}

.category-tab {
  padding: 6px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: 20px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
  user-select: none;
}

.category-tab:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.category-tab.is-active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(184, 134, 58, 0.3);
}

/* ─── 主体内容区与书籍网格 ──────────────────────────────────── */
.explore-main {
  flex: 1;
}

.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 22px 16px;
  justify-content: start;
}

/* ─── 书籍卡片 ──────────────────────────────────────────────── */
.explore-book-card {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  position: relative;
  user-select: none;
  transition: transform var(--transition-fast);
}

.explore-book-card:hover {
  transform: translateY(-4px);
}

.cover-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  background: var(--color-surface);
  transition: box-shadow var(--transition-base);
}

.explore-book-card:hover .cover-wrapper {
  box-shadow: var(--shadow-lg), 0 8px 24px rgba(184, 134, 58, 0.16);
}

.book-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.book-cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 8px;
  box-sizing: border-box;
  text-align: center;
  position: relative;
}

.fb-spine {
  position: absolute;
  left: 5px;
  top: 0;
  bottom: 0;
  width: 2.5px;
  background: var(--cover-spine, rgba(90, 78, 64, 0.09));
  border-right: 1px solid rgba(255, 255, 255, 0.5);
}

.fb-border {
  position: absolute;
  inset: 6px 6px 6px 9px;
  border: 1px solid var(--cover-border, rgba(90, 78, 64, 0.14));
  border-radius: 3px;
  pointer-events: none;
}

.fb-text {
  font-family: var(--font-serif, "'Noto Serif SC', 'Songti SC', 'SimSun', serif");
  font-size: 14px;
  font-weight: 700;
  color: var(--cover-text, #363028);
  letter-spacing: 0.06em;
  line-height: 1.3;
  z-index: 1;
}

.fb-author {
  font-size: 10px;
  color: var(--cover-sub, #7c7365);
  margin-top: 5px;
  z-index: 1;
}

.kind-tag {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  color: #fff;
  font-size: 9.5px;
  padding: 1px 5px;
  border-radius: 3px;
}

.book-info {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.book-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.book-author {
  font-size: 11.5px;
  color: var(--color-text-muted);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-last-chapter {
  font-size: 11px;
  color: var(--color-text-secondary);
  opacity: 0.8;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ─── 分页与加载状态 ────────────────────────────────────────── */
.load-more-section {
  text-align: center;
  margin: 36px 0 20px;
}

.btn-load-more {
  padding: 10px 28px;
  background: var(--color-surface);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-load-more:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-pale);
}

.loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin: 28px 0;
}

.dot-spin {
  display: flex;
  gap: 6px;
}

.dot-spin span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dot-bounce 1.2s ease-in-out infinite;
}

.dot-spin span:nth-child(2) { animation-delay: 0.15s; }
.dot-spin span:nth-child(3) { animation-delay: 0.3s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.loading-tip {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* ─── 骨架屏 ────────────────────────────────────────────────── */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 22px 16px;
}

.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sk-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--color-bg-subtle) 25%, var(--color-surface) 50%, var(--color-bg-subtle) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.sk-title {
  height: 14px;
  width: 80%;
  border-radius: 3px;
  background: var(--color-bg-subtle);
}

.sk-author {
  height: 11px;
  width: 50%;
  border-radius: 3px;
  background: var(--color-bg-subtle);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ─── 空状态 ────────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: var(--color-surface);
  border: 1px dashed var(--color-border-subtle);
  border-radius: var(--radius-lg);
  gap: 12px;
  text-align: center;
}

.empty-icon {
  font-size: 42px;
}

.empty-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  color: var(--color-text-muted);
  max-width: 420px;
  margin: 0;
}

.btn-primary-action {
  margin-top: 6px;
  padding: 8px 20px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13.5px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-primary-action:hover {
  opacity: 0.9;
}

/* ─── 弹窗详情 ──────────────────────────────────────────────── */
.modal-book-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-top {
  display: flex;
  gap: 16px;
}

.modal-cover-wrap {
  width: 90px;
  height: 120px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.modal-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal-cover-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 16px;
}

.modal-meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 0;
}

.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.modal-author, .modal-source, .modal-kind, .modal-chapter {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modal-intro {
  background: var(--color-bg);
  padding: 12px 14px;
  border-radius: var(--radius-md);
}

.modal-intro h4 {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 6px;
  color: var(--color-text-primary);
}

.modal-intro p {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.btn-action-read {
  flex: 1.2;
  padding: 10px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}

.btn-action-shelf {
  flex: 1;
  padding: 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
}

.btn-action-shelf:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-action-search {
  padding: 10px 14px;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  font-size: 13px;
  cursor: pointer;
}

/* ─── 移动端响应式适配 (<= 768px) ────────────────────────── */
@media (max-width: 768px) {
  .explore-page {
    padding: 14px 12px 30px;
    gap: 14px;
  }

  .explore-header {
    padding: 12px 14px;
    gap: 12px;
  }

  .header-top-row {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .source-selector-wrap {
    width: 100%;
    min-width: 0;
  }

  .source-select {
    width: 100%;
  }

  .books-grid, .skeleton-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px 10px;
  }

  .book-name {
    font-size: 13px;
  }

  .book-author {
    font-size: 11px;
  }

  :deep(.el-dialog) {
    width: 92vw !important;
    max-width: 440px;
    margin: 20px auto !important;
  }
}
</style>
