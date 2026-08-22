<template>
  <div class="explore-page" role="main" aria-label="书源探索发现">
    <!-- ── 移动端顶部快捷分类导航条 ───────────────────────── -->
    <div class="mobile-explore-bar">
      <button class="mobile-source-btn" @click="showMobileDrawer = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
          <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
        </svg>
        <span>{{ currentSource?.name || '选择书源' }}</span>
        <span class="mobile-cat-name">· {{ selectedCategoryTitle || '全部' }}</span>
      </button>

      <div class="mobile-view-toggle">
        <button
          class="view-mode-btn"
          :class="{ active: viewMode === 'grid' }"
          title="网格视图"
          @click="viewMode = 'grid'"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
          </svg>
        </button>
        <button
          class="view-mode-btn"
          :class="{ active: viewMode === 'list' }"
          title="列表视图"
          @click="viewMode = 'list'"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
            <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- ── 主布局：左侧分类侧栏 + 右侧探索书籍流 ───────────── -->
    <div class="explore-layout-container">
      <!-- ── 左侧：书源与分类层级导航 ────────────────────────── -->
      <aside class="explore-sidebar" :class="{ 'is-mobile-open': showMobileDrawer }">
        <!-- 侧栏头部：书源选择器 -->
        <div class="sidebar-header">
          <div class="source-card-header">
            <div class="source-header-top">
              <span class="sidebar-title">探索书源</span>
              <span v-if="sources.length > 0" class="source-pill">
                {{ sources.length }} 个可用
              </span>
            </div>

            <!-- 书源选择下拉 -->
            <el-select
              v-model="currentSourceId"
              placeholder="选择书源..."
              filterable
              class="sidebar-source-select"
              @change="onSourceChange"
            >
              <el-option
                v-for="s in sources"
                :key="s.id"
                :label="s.name"
                :value="s.id"
              >
                <div class="source-option-row">
                  <span class="opt-name">{{ s.name }}</span>
                  <span class="opt-badge">{{ s.exploreItems.filter(it => it.url).length }} 分类</span>
                </div>
              </el-option>
            </el-select>
          </div>

          <!-- 分类实时快速搜索过滤 -->
          <div class="category-search-box">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              v-model="categorySearchKw"
              type="text"
              placeholder="搜索分类/榜单..."
              class="category-search-input"
            />
            <button v-if="categorySearchKw" class="btn-clear-kw" @click="categorySearchKw = ''">×</button>
          </div>
        </div>

        <!-- 侧栏主体：分类树列表（支持智能分组） -->
        <div class="sidebar-category-list">
          <template v-if="groupedCategories.length > 0">
            <div
              v-for="group in groupedCategories"
              :key="group.name"
              class="category-group-block"
            >
              <div class="group-header">
                <span class="group-icon">{{ group.icon }}</span>
                <span class="group-title">{{ group.name }}</span>
                <span class="group-count">({{ group.items.length }})</span>
              </div>

              <div class="group-items-wrap">
                <button
                  v-for="cat in group.items"
                  :key="cat.url"
                  class="category-nav-btn"
                  :class="{ 'is-active': selectedCategoryUrl === cat.url }"
                  @click="selectCategory(cat)"
                >
                  <span class="cat-dot"></span>
                  <span class="cat-label">{{ cat.title }}</span>
                </button>
              </div>
            </div>
          </template>

          <div v-else-if="validCategories.length === 0" class="sidebar-empty">
            <span>当前书源未发现有效分类</span>
          </div>

          <div v-else class="sidebar-empty">
            <span>未匹配到相关分类</span>
          </div>
        </div>

        <!-- 移动端侧栏遮罩关闭按钮 -->
        <div class="mobile-drawer-footer">
          <button class="btn-close-drawer" @click="showMobileDrawer = false">
            完成选择
          </button>
        </div>
      </aside>

      <!-- 移动端遮罩层 -->
      <div
        v-if="showMobileDrawer"
        class="mobile-backdrop"
        @click="showMobileDrawer = false"
      ></div>

      <!-- ── 右侧：主内容展示区 ──────────────────────────────── -->
      <section class="explore-content-area">
        <!-- 顶部操作栏 -->
        <div class="content-action-bar">
          <div class="bar-left">
            <div class="active-category-info">
              <h2 class="active-cat-title">{{ selectedCategoryTitle || '探索发现' }}</h2>
              <span v-if="currentSource" class="active-source-badge">
                {{ currentSource.name }}
              </span>
              <span v-if="books.length > 0" class="books-count-badge">
                已加载 {{ books.length }} 部作品
              </span>
            </div>
          </div>

          <div class="bar-right">
            <!-- 列表内快速搜索过滤 -->
            <div class="book-filter-box">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              <input
                v-model="bookFilterKw"
                type="text"
                placeholder="在当前结果中筛选..."
                class="book-filter-input"
              />
              <button v-if="bookFilterKw" class="btn-clear-kw" @click="bookFilterKw = ''">×</button>
            </div>

            <!-- 视图模式切换 (桌面端) -->
            <div class="view-mode-group">
              <button
                class="view-mode-btn"
                :class="{ active: viewMode === 'grid' }"
                title="网格视图"
                @click="viewMode = 'grid'"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                  <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
                </svg>
              </button>
              <button
                class="view-mode-btn"
                :class="{ active: viewMode === 'list' }"
                title="列表视图"
                @click="viewMode = 'list'"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
                  <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
                </svg>
              </button>
            </div>

            <!-- 重新抓取刷新 -->
            <button
              class="btn-refresh"
              :disabled="loading"
              title="重新加载当前分类"
              @click="loadBooks(1)"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spin: loading }">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
              </svg>
              <span>刷新</span>
            </button>
          </div>
        </div>

        <!-- 初始全页加载中骨架屏 -->
        <div v-if="initialLoading || (loading && books.length === 0)" class="explore-skeleton-grid">
          <div v-for="n in 10" :key="n" class="skeleton-book-card">
            <div class="sk-cover"></div>
            <div class="sk-meta">
              <div class="sk-line sk-title"></div>
              <div class="sk-line sk-author"></div>
              <div class="sk-line sk-intro"></div>
            </div>
          </div>
        </div>

        <!-- 无可用书源 -->
        <div v-else-if="sources.length === 0" class="explore-empty-panel">
          <div class="empty-illustration">🧭</div>
          <h3 class="empty-heading">暂无可探索的书源</h3>
          <p class="empty-sub">当前书库中的书源未配置 exploreUrl 规则，您可以导入支持探索发现的精品书源</p>
          <router-link to="/sources" class="btn-goto-sources">前往书源管理</router-link>
        </div>

        <!-- 内容为空提示 -->
        <div v-else-if="!loading && displayBooks.length === 0" class="explore-empty-panel">
          <div class="empty-illustration">📭</div>
          <h3 class="empty-heading">未找到相关书籍</h3>
          <p class="empty-sub">
            {{ bookFilterKw ? '没有匹配当前过滤条件的书籍，请尝试更换关键词' : '该分类暂未返回书籍数据或书源响应超时' }}
          </p>
          <button class="btn-goto-sources" @click="loadBooks(1)">重新抓取</button>
        </div>

        <!-- ── 书籍展示区 ────────────────────────────────────── -->
        <div v-else class="explore-books-wrapper">
          <!-- 🌟 头牌 Spotlight Showcase 横幅推荐卡片（精选第一本书） -->
          <div v-if="spotlightBook && page === 1 && !bookFilterKw" class="spotlight-showcase-card">
            <div class="spotlight-badge">🔥 热门头牌精选</div>
            <div class="spotlight-main" @click="openBookModal(spotlightBook)">
              <div class="spotlight-cover-wrap">
                <img
                  v-if="spotlightBook.cover && !failedCovers.has(spotlightBook.name + spotlightBook.author)"
                  :src="spotlightBook.cover"
                  :alt="spotlightBook.name"
                  class="spotlight-cover"
                  loading="lazy"
                  @error="failedCovers.add(spotlightBook.name + spotlightBook.author)"
                />
                <div v-else class="spotlight-cover spotlight-fallback" :style="placeholderBg(spotlightBook.name)">
                  <div class="fb-spine"></div>
                  <span class="fb-text">{{ (spotlightBook.name || '书').slice(0, 4) }}</span>
                </div>
              </div>

              <div class="spotlight-info">
                <div class="spotlight-title-row">
                  <h3 class="spotlight-name">{{ spotlightBook.name }}</h3>
                  <span v-if="spotlightBook.kind" class="spotlight-tag">{{ spotlightBook.kind.split('')[0] }}</span>
                </div>
                <div class="spotlight-author-row">
                  <span class="spotlight-author">作者：{{ spotlightBook.author || '佚名' }}</span>
                  <span v-if="spotlightBook.word_count" class="spotlight-words">{{ spotlightBook.word_count }}</span>
                  <span v-if="spotlightBook.last_chapter" class="spotlight-chapter">最新：{{ spotlightBook.last_chapter }}</span>
                </div>
                <p class="spotlight-intro">{{ spotlightBook.intro || '暂无作品简介...' }}</p>

                <div class="spotlight-actions" @click.stop>
                  <button class="btn-spot-read" @click="startReading(spotlightBook)">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                    立即阅读
                  </button>
                  <button
                    class="btn-spot-shelf"
                    :disabled="isBookInShelf(spotlightBook)"
                    @click="addToShelf(spotlightBook)"
                  >
                    {{ isBookInShelf(spotlightBook) ? '✓ 已在书架' : '+ 加入书架' }}
                  </button>
                  <button class="btn-spot-search" @click="searchGlobal(spotlightBook)">
                    全网搜书
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- ── 网格视图 (Grid View) ────────────────────────── -->
          <div v-if="viewMode === 'grid'" class="explore-grid-view">
            <article
              v-for="(book, idx) in gridBooks"
              :key="idx"
              class="explore-card"
              tabindex="0"
              @click="openBookModal(book)"
              @keydown.enter="openBookModal(book)"
            >
              <!-- 封面区域 -->
              <div class="card-cover-container">
                <img
                  v-if="book.cover && !failedCovers.has(book.name + book.author)"
                  :src="book.cover"
                  :alt="book.name"
                  class="card-cover-img"
                  loading="lazy"
                  @error="failedCovers.add(book.name + book.author)"
                />
                <div v-else class="card-cover-img card-cover-fallback" :style="placeholderBg(book.name)">
                  <div class="fb-spine"></div>
                  <div class="fb-border"></div>
                  <span class="fb-text">{{ (book.name || '书').slice(0, 4) }}</span>
                  <span v-if="book.author" class="fb-author">{{ book.author }}</span>
                </div>

                <!-- 类别徽章 -->
                <span v-if="book.kind" class="card-kind-badge">{{ book.kind.split('')[0] }}</span>

                <!-- 悬浮快速操作浮层 -->
                <div class="card-hover-overlay" @click.stop>
                  <button
                    class="hover-btn hover-btn-read"
                    title="立即阅读"
                    @click="startReading(book)"
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                  </button>
                  <button
                    class="hover-btn hover-btn-shelf"
                    :class="{ 'in-shelf': isBookInShelf(book) }"
                    :title="isBookInShelf(book) ? '已在书架' : '加入书架'"
                    :disabled="isBookInShelf(book)"
                    @click="addToShelf(book)"
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                    </svg>
                  </button>
                  <button
                    class="hover-btn hover-btn-search"
                    title="全网多源搜书"
                    @click="searchGlobal(book)"
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                    </svg>
                  </button>
                </div>
              </div>

              <!-- 信息区 -->
              <div class="card-body">
                <h4 class="card-book-title" :title="book.name">{{ book.name }}</h4>
                <div class="card-meta-line">
                  <span class="card-author" :title="book.author">{{ book.author || '佚名' }}</span>
                  <span v-if="book.word_count" class="card-words">{{ book.word_count }}</span>
                </div>
                <p v-if="book.intro" class="card-intro" :title="book.intro">
                  {{ book.intro }}
                </p>
                <p v-else-if="book.last_chapter" class="card-chapter" :title="book.last_chapter">
                  {{ book.last_chapter }}
                </p>
              </div>
            </article>
          </div>

          <!-- ── 列表视图 (List View) ────────────────────────── -->
          <div v-else class="explore-list-view">
            <article
              v-for="(book, idx) in displayBooks"
              :key="idx"
              class="list-item-card"
              @click="openBookModal(book)"
            >
              <div class="list-cover-wrap">
                <img
                  v-if="book.cover && !failedCovers.has(book.name + book.author)"
                  :src="book.cover"
                  :alt="book.name"
                  class="list-cover-img"
                  loading="lazy"
                  @error="failedCovers.add(book.name + book.author)"
                />
                <div v-else class="list-cover-img list-cover-fallback" :style="placeholderBg(book.name)">
                  <div class="fb-spine"></div>
                  <span class="fb-text">{{ (book.name || '书').slice(0, 4) }}</span>
                </div>
              </div>

              <div class="list-info-wrap">
                <div class="list-title-row">
                  <h4 class="list-book-name">{{ book.name }}</h4>
                  <span v-if="book.kind" class="list-tag">{{ book.kind.split('')[0] }}</span>
                </div>
                <div class="list-meta-row">
                  <span class="list-author">作者：{{ book.author || '佚名' }}</span>
                  <span v-if="book.word_count" class="list-words">字数：{{ book.word_count }}</span>
                  <span v-if="book.last_chapter" class="list-chapter">最新：{{ book.last_chapter }}</span>
                </div>
                <p class="list-intro">{{ book.intro || '暂无详细作品介绍...' }}</p>
              </div>

              <div class="list-actions-wrap" @click.stop>
                <button class="btn-list-read" @click="startReading(book)">
                  阅读
                </button>
                <button
                  class="btn-list-shelf"
                  :disabled="isBookInShelf(book)"
                  @click="addToShelf(book)"
                >
                  {{ isBookInShelf(book) ? '已入架' : '+ 书架' }}
                </button>
                <button class="btn-list-search" @click="searchGlobal(book)">
                  全网搜
                </button>
              </div>
            </article>
          </div>

          <!-- ── 底部分页与加载更多 ────────────────────────────── -->
          <div v-if="hasMore && !loading" class="explore-footer-more">
            <button class="btn-load-more-explore" @click="loadNextPage">
              加载下一页 (第 {{ page + 1 }} 页)
            </button>
          </div>

          <div v-if="loading && books.length > 0" class="explore-loading-indicator" aria-live="polite">
            <div class="wave-dots">
              <span></span><span></span><span></span>
            </div>
            <span class="tip-text">正在探索更多书籍...</span>
          </div>

          <div v-if="!hasMore && books.length > 0" class="explore-no-more">
            <span>—— 已经到底啦，共探索到 {{ books.length }} 本书籍 ——</span>
          </div>
        </div>
      </section>
    </div>

    <!-- ── 书籍详情精美抽屉/弹窗 ────────────────────────────── -->
    <el-dialog
      v-model="showBookModal"
      width="540px"
      class="explore-detail-dialog"
      destroy-on-close
      append-to-body
    >
      <div v-if="selectedBook" class="book-detail-dialog-inner">
        <div class="dialog-top-row">
          <div class="dialog-cover-wrap">
            <img
              v-if="selectedBook.cover && !failedCovers.has(selectedBook.name + selectedBook.author)"
              :src="selectedBook.cover"
              :alt="selectedBook.name"
              class="dialog-cover"
            />
            <div v-else class="dialog-cover dialog-cover-fallback" :style="placeholderBg(selectedBook.name)">
              <div class="fb-spine"></div>
              <span>{{ (selectedBook.name || '书').slice(0, 4) }}</span>
            </div>
          </div>

          <div class="dialog-meta-info">
            <h3 class="dialog-book-title">{{ selectedBook.name }}</h3>
            <div class="dialog-badges">
              <span v-if="selectedBook.kind" class="diag-badge kind">{{ selectedBook.kind }}</span>
              <span class="diag-badge source">{{ selectedBook.source_name || currentSource?.name }}</span>
            </div>
            <p class="dialog-author">作者：<span>{{ selectedBook.author || '未知' }}</span></p>
            <p v-if="selectedBook.word_count" class="dialog-words">字数：<span>{{ selectedBook.word_count }}</span></p>
            <p v-if="selectedBook.last_chapter" class="dialog-chapter">最新章节：<span>{{ selectedBook.last_chapter }}</span></p>
          </div>
        </div>

        <div v-if="selectedBook.intro" class="dialog-intro-box">
          <h4 class="intro-heading">作品简介</h4>
          <p class="intro-text">{{ selectedBook.intro }}</p>
        </div>

        <div class="dialog-actions-row">
          <button
            class="btn-dialog-read"
            :disabled="actionLoading"
            @click="startReading(selectedBook)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            立即阅读
          </button>

          <button
            class="btn-dialog-shelf"
            :disabled="actionLoading || isBookInShelf(selectedBook)"
            @click="addToShelf(selectedBook)"
          >
            {{ isBookInShelf(selectedBook) ? '✓ 已在书架' : '+ 加入书架' }}
          </button>

          <button
            class="btn-dialog-search"
            @click="searchGlobal(selectedBook)"
          >
            全网多源比价搜书
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

const categorySearchKw = ref('')
const bookFilterKw = ref('')
const viewMode = ref<'grid' | 'list'>('grid')
const showMobileDrawer = ref(false)

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

// ── 智能分类分组 ──────────────────────────────────────────
interface CategoryGroup {
  name: string
  icon: string
  items: ExploreItem[]
}

const groupedCategories = computed<CategoryGroup[]>(() => {
  const kw = categorySearchKw.value.trim().toLowerCase()
  let filtered = validCategories.value
  if (kw) {
    filtered = filtered.filter(it => it.title.toLowerCase().includes(kw))
  }
  if (!filtered.length) return []

  const groups: { [key: string]: CategoryGroup } = {
    hot: { name: '热门榜单', icon: '🏆', items: [] },
    xuanhuan: { name: '玄幻仙侠', icon: '⚔️', items: [] },
    city: { name: '都市言情', icon: '🏙️', items: [] },
    scifi: { name: '科幻游戏', icon: '🚀', items: [] },
    female: { name: '女生频道', icon: '🌸', items: [] },
    other: { name: '分类浏览', icon: '📖', items: [] },
  }

  filtered.forEach(it => {
    const t = it.title
    if (/榜|热|推荐|畅销|点击|收藏|月票|强推|评分|精选/i.test(t)) {
      groups.hot.items.push(it)
    } else if (/玄幻|仙侠|修真|奇幻|武侠|修仙|洪荒|魔幻/i.test(t)) {
      groups.xuanhuan.items.push(it)
    } else if (/都市|职场|青春|豪门|重生|官场|娱乐/i.test(t)) {
      groups.city.items.push(it)
    } else if (/科幻|游戏|网游|历史|军事|悬疑|灵异|无限|末世/i.test(t)) {
      groups.scifi.items.push(it)
    } else if (/女频|现言|古言|耽美|同人|百合|轻小说/i.test(t)) {
      groups.female.items.push(it)
    } else {
      groups.other.items.push(it)
    }
  })

  const result: CategoryGroup[] = []
  for (const k of ['hot', 'xuanhuan', 'city', 'scifi', 'female', 'other']) {
    if (groups[k].items.length > 0) {
      result.push(groups[k])
    }
  }
  return result
})

// ── 结果过滤与头牌展示 ────────────────────────────────────
const displayBooks = computed(() => {
  const kw = bookFilterKw.value.trim().toLowerCase()
  if (!kw) return books.value
  return books.value.filter(b => 
    (b.name && b.name.toLowerCase().includes(kw)) ||
    (b.author && b.author.toLowerCase().includes(kw)) ||
    (b.kind && b.kind.toLowerCase().includes(kw)) ||
    (b.intro && b.intro.toLowerCase().includes(kw))
  )
})

const spotlightBook = computed<ExploreBook | null>(() => {
  if (!displayBooks.value.length) return null
  const found = displayBooks.value.find(b => Boolean(b.cover && b.intro && b.intro.length > 20))
  return found || displayBooks.value[0] || null
})

const gridBooks = computed(() => {
  if (page.value === 1 && spotlightBook.value && !bookFilterKw.value) {
    return displayBooks.value.filter(b => b.name !== spotlightBook.value?.name)
  }
  return displayBooks.value
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
  showMobileDrawer.value = false
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
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg, #f7f6f2);
}

/* ─── 移动端顶部快捷操作条 ──────────────────────────────────── */
.mobile-explore-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--color-surface, #ffffff);
  border-bottom: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
  flex-shrink: 0;
}

.mobile-source-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  background: var(--color-accent-pale, rgba(200, 152, 58, 0.1));
  border: 1px solid rgba(200, 152, 58, 0.2);
  color: var(--color-accent, #c8983a);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.mobile-cat-name {
  color: var(--color-text-secondary, #666);
  font-weight: normal;
}

.mobile-view-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ─── 双栏主体容器 ─────────────────────────────────────────── */
.explore-layout-container {
  display: flex;
  flex: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

/* ─── 左侧分类侧栏 ────────────────────────────────────────── */
.explore-sidebar {
  width: 280px;
  min-width: 280px;
  background: var(--color-surface, #ffffff);
  border-right: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  z-index: 10;
}

.sidebar-header {
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--color-surface, #ffffff);
}

.source-card-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary, #222);
  letter-spacing: -0.01em;
}

.source-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  background: var(--color-accent-pale, rgba(200, 152, 58, 0.12));
  color: var(--color-accent, #c8983a);
  border-radius: 12px;
}

.sidebar-source-select {
  width: 100%;
}

.source-option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  font-size: 13px;
}

.opt-name {
  font-weight: 500;
  color: #333;
}

.opt-badge {
  font-size: 11px;
  color: #999;
}

.category-search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 6px 10px;
  color: #888;
}

.category-search-input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 12.5px;
  width: 100%;
  color: var(--color-text-primary, #222);
}

.btn-clear-kw {
  border: none;
  background: transparent;
  color: #999;
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
}

/* 侧栏分类树列表 */
.sidebar-category-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.category-group-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 700;
  color: #888;
  letter-spacing: 0.02em;
}

.group-icon {
  font-size: 13px;
}

.group-count {
  font-size: 11px;
  color: #aaa;
}

.group-items-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.category-nav-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary, #555);
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all 0.16s ease;
}

.cat-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #ccc;
  transition: all 0.16s ease;
}

.category-nav-btn:hover {
  background: rgba(200, 152, 58, 0.08);
  color: var(--color-accent, #c8983a);
}

.category-nav-btn.is-active {
  background: var(--color-accent-pale, rgba(200, 152, 58, 0.15));
  color: var(--color-accent, #c8983a);
  font-weight: 600;
}

.category-nav-btn.is-active .cat-dot {
  background: var(--color-accent, #c8983a);
  transform: scale(1.4);
}

.sidebar-empty {
  padding: 30px 10px;
  text-align: center;
  font-size: 12px;
  color: #999;
}

.mobile-drawer-footer {
  display: none;
}

/* ─── 右侧内容展示区 ──────────────────────────────────────── */
.explore-content-area {
  flex: 1;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 20px 24px 60px;
  box-sizing: border-box;
}

/* 顶部操作概览栏 */
.content-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.active-category-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.active-cat-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary, #222);
  margin: 0;
}

.active-source-badge {
  font-size: 12px;
  padding: 3px 10px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  color: #666;
}

.books-count-badge {
  font-size: 12px;
  color: #999;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.book-filter-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-surface, #ffffff);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 6px 12px;
  color: #888;
}

.book-filter-input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  width: 150px;
  color: #333;
}

.view-mode-group {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
  padding: 2px;
}

.view-mode-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  background: transparent;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.16s ease;
}

.view-mode-btn.active {
  background: var(--color-surface, #ffffff);
  color: var(--color-accent, #c8983a);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 8px;
  background: var(--color-surface, #ffffff);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #555;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-refresh:hover:not(:disabled) {
  border-color: var(--color-accent, #c8983a);
  color: var(--color-accent, #c8983a);
}

.spin {
  animation: spinRotate 1s linear infinite;
}

@keyframes spinRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ─── 🌟 Spotlight 头牌横幅推荐卡片 ───────────────────────── */
.spotlight-showcase-card {
  position: relative;
  background: linear-gradient(135deg, #ffffff 0%, #fdfbf7 100%);
  border: 1px solid rgba(200, 152, 58, 0.25);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(200, 152, 58, 0.08);
}

.spotlight-badge {
  position: absolute;
  top: -10px;
  left: 20px;
  background: linear-gradient(135deg, #c8983a, #b5852d);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(200, 152, 58, 0.3);
}

.spotlight-main {
  display: flex;
  gap: 24px;
  align-items: center;
  cursor: pointer;
}

.spotlight-cover-wrap {
  width: 120px;
  height: 160px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.spotlight-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.spotlight-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  color: #ffffff;
  font-size: 16px;
  font-weight: 700;
}

.spotlight-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.spotlight-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.spotlight-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary, #222);
  margin: 0;
}

.spotlight-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--color-accent-pale, rgba(200, 152, 58, 0.12));
  color: var(--color-accent, #c8983a);
  border-radius: 6px;
  font-weight: 600;
}

.spotlight-author-row {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 13px;
  color: #666;
}

.spotlight-intro {
  font-size: 13px;
  line-height: 1.6;
  color: #666;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}

.spotlight-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

.btn-spot-read {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 8px;
  background: var(--color-accent, #c8983a);
  color: #ffffff;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-spot-read:hover {
  background: #b5852d;
  transform: translateY(-1px);
}

.btn-spot-shelf,
.btn-spot-search {
  padding: 7px 14px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #444;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.16s ease;
}

.btn-spot-shelf:hover:not(:disabled),
.btn-spot-search:hover {
  background: var(--color-accent-pale, rgba(200, 152, 58, 0.12));
  color: var(--color-accent, #c8983a);
  border-color: rgba(200, 152, 58, 0.3);
}

/* ─── 网格视图卡片 ────────────────────────────────────────── */
.explore-grid-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.explore-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.explore-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-color: rgba(200, 152, 58, 0.35);
}

.card-cover-container {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  background: #eae6df;
}

.card-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.explore-card:hover .card-cover-img {
  transform: scale(1.04);
}

.card-cover-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  color: #ffffff;
  padding: 10px;
  box-sizing: border-box;
}

.fb-spine {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 7px;
  background: linear-gradient(90deg, rgba(255,255,255,0.4), rgba(0,0,0,0.2));
}

.fb-border {
  position: absolute;
  inset: 4px;
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 4px;
}

.fb-text {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 2px;
  z-index: 1;
}

.fb-author {
  font-size: 11px;
  opacity: 0.8;
  margin-top: 4px;
  z-index: 1;
}

.card-kind-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(8px);
  color: #ffffff;
  font-size: 10.5px;
  padding: 2px 7px;
  border-radius: 4px;
  font-weight: 500;
}

/* 悬浮操作浮层 */
.card-hover-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}

.explore-card:hover .card-hover-overlay {
  opacity: 1;
  pointer-events: auto;
}

.hover-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #ffffff;
  color: #333;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  transition: all 0.16s ease;
}

.hover-btn:hover {
  transform: scale(1.1);
  background: var(--color-accent, #c8983a);
  color: #ffffff;
}

.hover-btn.in-shelf {
  background: #4caf50;
  color: #ffffff;
}

.card-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-book-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-primary, #222);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #888;
}

.card-author {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-words {
  font-size: 11px;
  color: #aaa;
}

.card-intro,
.card-chapter {
  font-size: 12px;
  color: #777;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.45;
  margin: 4px 0 0;
}

/* ─── 列表视图 ────────────────────────────────────────────── */
.explore-list-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-item-card {
  display: flex;
  align-items: center;
  gap: 18px;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
  border-radius: 12px;
  padding: 14px 18px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.list-item-card:hover {
  transform: translateX(4px);
  border-color: rgba(200, 152, 58, 0.35);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.list-cover-wrap {
  width: 70px;
  height: 94px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  background: #eae6df;
}

.list-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.list-cover-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  position: relative;
}

.list-info-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.list-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-book-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary, #222);
  margin: 0;
}

.list-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(200, 152, 58, 0.1);
  color: var(--color-accent, #c8983a);
  font-weight: 600;
}

.list-meta-row {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: #777;
}

.list-intro {
  font-size: 12.5px;
  color: #666;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 2px 0 0;
}

.list-actions-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-list-read {
  padding: 6px 14px;
  border-radius: 6px;
  background: var(--color-accent, #c8983a);
  color: #ffffff;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-list-shelf,
.btn-list-search {
  padding: 6px 12px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #444;
  font-size: 12.5px;
  cursor: pointer;
}

.btn-list-shelf:hover:not(:disabled),
.btn-list-search:hover {
  color: var(--color-accent, #c8983a);
  border-color: var(--color-accent, #c8983a);
}

/* ─── 骨架屏与状态 ────────────────────────────────────────── */
.explore-skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.skeleton-book-card {
  background: var(--color-surface, #ffffff);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sk-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  background: linear-gradient(90deg, #f0ede6 25%, #e8e4db 37%, #f0ede6 63%);
  background-size: 400% 100%;
  animation: skeletonShimmer 1.4s ease infinite;
}

.sk-meta {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sk-line {
  height: 12px;
  background: #ece8df;
  border-radius: 4px;
}

.sk-title { width: 70%; height: 14px; }
.sk-author { width: 45%; }
.sk-intro { width: 90%; }

@keyframes skeletonShimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

.explore-empty-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  background: var(--color-surface, #ffffff);
  border-radius: 16px;
  border: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
}

.empty-illustration {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-heading {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary, #222);
  margin: 0 0 6px;
}

.empty-sub {
  font-size: 13px;
  color: #888;
  max-width: 420px;
  line-height: 1.5;
  margin: 0 0 20px;
}

.btn-goto-sources {
  display: inline-flex;
  align-items: center;
  padding: 9px 20px;
  border-radius: 8px;
  background: var(--color-accent, #c8983a);
  color: #ffffff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

/* ─── 底部分页与触底 ──────────────────────────────────────── */
.explore-footer-more {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

.btn-load-more-explore {
  padding: 10px 32px;
  border-radius: 24px;
  background: var(--color-surface, #ffffff);
  border: 1px solid rgba(200, 152, 58, 0.35);
  color: var(--color-accent, #c8983a);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  transition: all 0.18s ease;
}

.btn-load-more-explore:hover {
  background: var(--color-accent, #c8983a);
  color: #ffffff;
  transform: translateY(-2px);
}

.explore-loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 32px;
  color: #888;
  font-size: 13px;
}

.wave-dots {
  display: flex;
  gap: 6px;
}

.wave-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-accent, #c8983a);
  animation: dotWave 1.4s ease-in-out infinite;
}

.wave-dots span:nth-child(2) { animation-delay: 0.2s; }
.wave-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotWave {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.explore-no-more {
  text-align: center;
  color: #bbb;
  font-size: 12px;
  margin-top: 40px;
}

/* ─── 弹窗详情 ────────────────────────────────────────────── */
.book-detail-dialog-inner {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dialog-top-row {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.dialog-cover-wrap {
  width: 110px;
  height: 148px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
}

.dialog-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.dialog-cover-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-weight: 700;
  font-size: 15px;
  position: relative;
}

.dialog-meta-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dialog-book-title {
  font-size: 18px;
  font-weight: 700;
  color: #222;
  margin: 0;
}

.dialog-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.diag-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.diag-badge.kind {
  background: var(--color-accent-pale, rgba(200, 152, 58, 0.12));
  color: var(--color-accent, #c8983a);
}

.diag-badge.source {
  background: rgba(0, 0, 0, 0.05);
  color: #666;
}

.dialog-author,
.dialog-words,
.dialog-chapter {
  font-size: 13px;
  color: #666;
  margin: 0;
}

.dialog-author span,
.dialog-words span,
.dialog-chapter span {
  color: #222;
  font-weight: 500;
}

.dialog-intro-box {
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 14px;
}

.intro-heading {
  font-size: 13px;
  font-weight: 700;
  color: #444;
  margin: 0 0 6px;
}

.intro-text {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  margin: 0;
  max-height: 160px;
  overflow-y: auto;
}

.dialog-actions-row {
  display: flex;
  gap: 10px;
}

.btn-dialog-read {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border-radius: 8px;
  background: var(--color-accent, #c8983a);
  color: #ffffff;
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-dialog-shelf {
  padding: 10px 18px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #333;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
}

.btn-dialog-search {
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #333;
  font-size: 13px;
  cursor: pointer;
}

.btn-dialog-shelf:hover:not(:disabled),
.btn-dialog-search:hover {
  color: var(--color-accent, #c8983a);
  border-color: var(--color-accent, #c8983a);
}

/* ─── 响应式断点 ────────────────────────────────────────── */
@media (max-width: 900px) {
  .mobile-explore-bar {
    display: flex;
  }

  .explore-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 290px;
    transform: translateX(-100%);
    transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 0 24px rgba(0, 0, 0, 0.2);
    z-index: 1000;
  }

  .explore-sidebar.is-mobile-open {
    transform: translateX(0);
  }

  .mobile-drawer-footer {
    display: block;
    padding: 12px;
    border-top: 1px solid var(--color-border-subtle, rgba(0,0,0,0.06));
  }

  .btn-close-drawer {
    width: 100%;
    padding: 10px;
    border-radius: 8px;
    background: var(--color-accent, #c8983a);
    color: #ffffff;
    border: none;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .mobile-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    z-index: 999;
  }

  .explore-content-area {
    padding: 14px 14px 40px;
  }

  .spotlight-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }

  .spotlight-cover-wrap {
    width: 100px;
    height: 133px;
  }

  .explore-grid-view {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }
}
</style>
