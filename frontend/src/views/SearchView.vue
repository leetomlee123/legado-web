<template>
  <section class="search-page" aria-label="书籍搜索">
    <!-- 搜索区域 -->
    <div class="search-hero">
      <h2 class="search-heading">多源流式加权搜索</h2>
      <p class="search-sub">实时并发检索各书源，按相关度权重动态精准排序</p>
      
      <!-- 搜索主输入栏 -->
      <div class="search-bar" role="search">
        <div class="search-field">
          <span class="search-field-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </span>
          <input
            id="search-keyword-input"
            v-model="keyword"
            type="search"
            class="search-input"
            placeholder="输入书名、作者或关键词..."
            aria-label="输入书名或作者"
            @keyup.enter="startStreamSearch"
          />
        </div>
        
        <!-- 搜索 / 停止 按钮 -->
        <button
          v-if="!searching"
          id="search-submit-btn"
          class="btn-search"
          aria-label="搜索"
          @click="startStreamSearch"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          搜索
        </button>

        <button
          v-else
          id="search-stop-btn"
          class="btn-search btn-stop"
          aria-label="停止搜索"
          @click="handleStopSearch"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
            <rect x="5" y="5" width="14" height="14" rx="2"/>
          </svg>
          停止
        </button>
      </div>

      <!-- ── 可折叠书源选择器栏 ──────────────────────────────── -->
      <div v-if="allSources.length" class="source-collapse-container">
        <!-- 紧凑概要条 -->
        <div class="source-summary-bar">
          <div class="summary-left">
            <span class="filter-label">检索书源：</span>
            <button
              class="source-chip main-all-chip"
              :class="{ active: isAllSelected }"
              @click="toggleSelectAll"
            >
              全部 ({{ selectedSourceIds.length }}/{{ allSources.length }})
            </button>

            <!-- 折叠状态下仅展示前几个常用源 -->
            <template v-if="!isSourceFilterExpanded">
              <button
                v-for="s in visibleSourcesCompact"
                :key="s.id"
                class="source-chip"
                :class="{ active: selectedSourceIds.includes(s.id!) }"
                @click="toggleSource(s.id!)"
              >
                {{ s.name }}
              </button>
            </template>
          </div>

          <button
            class="btn-toggle-expand"
            :class="{ expanded: isSourceFilterExpanded }"
            @click="isSourceFilterExpanded = !isSourceFilterExpanded"
          >
            <span>{{ isSourceFilterExpanded ? '收起书源 ▲' : `更多书源 (${allSources.length}) ▼` }}</span>
          </button>
        </div>

        <!-- 展开后的完整书源选择面板 -->
        <div v-if="isSourceFilterExpanded" class="source-expanded-panel">
          <div class="panel-header-tools">
            <input
              v-model="sourceSearchInput"
              type="search"
              class="source-search-input"
              placeholder="🔍 快速过滤书源名称..."
            />
            <div class="panel-action-btns">
              <button class="btn-text" @click="selectAllSources">全选</button>
              <span class="btn-sep">|</span>
              <button class="btn-text" @click="invertSelectSources">反选</button>
              <span class="btn-sep">|</span>
              <button class="btn-text" @click="clearSelectSources">清空</button>
            </div>
          </div>

          <div class="source-chips-grid">
            <button
              v-for="s in filteredSourcesInPanel"
              :key="s.id"
              class="source-chip chip-item"
              :class="{ active: selectedSourceIds.includes(s.id!) }"
              @click="toggleSource(s.id!)"
            >
              <span class="chip-name">{{ s.name }}</span>
            </button>
            <div v-if="!filteredSourcesInPanel.length" class="no-matched-source">
              未找到匹配的书源
            </div>
          </div>
        </div>
      </div>

      <!-- SSE 实时流式搜索进度与统计栏 -->
      <div v-if="searching || searched" class="search-progress-box">
        <div class="progress-info">
          <span class="progress-text">
            <span v-if="searching" class="spin-dot"></span>
            <span v-if="searching">
              正在检索 ({{ completedSources }}/{{ totalSources }})...
            </span>
            <span v-else class="done-text">
              ✓ 检索完成 ({{ completedSources }}/{{ totalSources }} 个书源)
            </span>
          </span>

          <div class="progress-right">
            <span class="found-counter">
              共找到 <strong>{{ totalBooksFound }}</strong> 本书
            </span>

            <!-- 分组模式下的全局折叠/展开按钮 -->
            <div v-if="viewMode === 'grouped' && results.length" class="group-collapse-tools">
              <button class="btn-collapse-all" @click="toggleCollapseAllGroups">
                {{ isAllGroupsCollapsed ? '全部展开 ▼' : '全部折叠 ▲' }}
              </button>
            </div>

            <!-- 排序与视图切换 -->
            <div class="view-mode-toggle" role="tablist">
              <button
                class="btn-mode"
                :class="{ active: viewMode === 'weighted' }"
                title="按相关度加权综合排序"
                @click="viewMode = 'weighted'"
              >
                🎯 综合加权
              </button>
              <button
                class="btn-mode"
                :class="{ active: viewMode === 'grouped' }"
                title="按书源分组折叠展示"
                @click="viewMode = 'grouped'"
              >
                📑 按源分组
              </button>
            </div>
          </div>
        </div>

        <div class="progress-track" v-if="searching">
          <div
            class="progress-bar"
            :style="{ width: `${totalSources ? (completedSources / totalSources) * 100 : 0}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- 模式 1：综合加权排序视图（默认推荐） -->
    <div v-if="results.length && viewMode === 'weighted'" class="weighted-results-container">
      <div class="result-list">
        <article
          v-for="(b, idx) in weightedBooks"
          :key="b.uuid || b.id || (b.name + b.sourceName + idx)"
          class="result-card"
          @click="open(b)"
          :aria-label="`查看《${b.name}》`"
          tabindex="0"
          @keydown.enter="open(b)"
        >
          <!-- 封面 -->
          <div class="thumb-wrap">
            <img
              v-if="b.cover && !failedCovers.has(b.uuid || b.name)"
              :src="b.cover"
              class="thumb"
              :alt="`《${b.name}》封面`"
              loading="lazy"
              @error="handleCoverError(b)"
            />
            <div v-else class="thumb thumb-placeholder" :style="resultPlaceholderStyle(b.name)" aria-hidden="true">
              <span class="thumb-text">{{ (b.name || '书').slice(0, 4) }}</span>
            </div>
          </div>

          <!-- 书籍信息 -->
          <div class="r-info">
            <div class="r-top-row">
              <div class="r-name" v-html="highlightKeyword(b.name)"></div>
              
              <!-- 来源标签与加权标签 -->
              <div class="r-tags">
                <span v-if="b.matchLevel === 'exact'" class="tag-match exact">精准完全匹配</span>
                <span v-else-if="b.matchLevel === 'prefix'" class="tag-match prefix">书名开头匹配</span>
                <span v-else-if="b.matchLevel === 'author'" class="tag-match author">作者匹配</span>
                <span class="source-badge">{{ b.sourceName }}</span>
              </div>
            </div>

            <div class="r-author" v-html="highlightKeyword(b.author || '作者不详')"></div>
            <p v-if="b.intro" class="r-intro">{{ b.intro }}</p>
          </div>

          <div class="r-arrow" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </div>
        </article>
      </div>
    </div>

    <!-- 模式 2：按书源分组折叠视图 -->
    <div v-else-if="results.length && viewMode === 'grouped'" class="results-container">
      <div
        v-for="group in sortedResultsByGroup"
        :key="group.sourceId"
        class="source-group"
        :class="{ collapsed: collapsedGroupIds.has(group.sourceId) }"
      >
        <!-- 可点击折叠/展开的书源标题栏 -->
        <div
          class="source-header clickable-header"
          @click="toggleGroupCollapse(group.sourceId)"
          :title="collapsedGroupIds.has(group.sourceId) ? '点击展开该书源' : '点击折叠该书源'"
        >
          <div class="source-header-left">
            <span class="collapse-caret" :class="{ rotated: !collapsedGroupIds.has(group.sourceId) }">
              ▶
            </span>
            <span class="source-tag">{{ group.sourceName }}</span>
            <span v-if="group.error" class="source-err-badge" :title="group.error">
              抓取异常
            </span>
          </div>
          <div class="source-header-right">
            <span class="source-count">{{ group.books.length }} 本</span>
            <span class="collapse-tip-text">
              {{ collapsedGroupIds.has(group.sourceId) ? '展开' : '折叠' }}
            </span>
          </div>
        </div>

        <!-- 展开内容 -->
        <div v-show="!collapsedGroupIds.has(group.sourceId)">
          <div v-if="group.books.length" class="result-list">
            <article
              v-for="b in group.books"
              :key="b.uuid || b.id || b.name"
              class="result-card"
              @click="open(b)"
              :aria-label="`查看《${b.name}》`"
              tabindex="0"
              @keydown.enter="open(b)"
            >
              <div class="thumb-wrap">
                <img
                  v-if="b.cover && !failedCovers.has(b.uuid || b.name)"
                  :src="b.cover"
                  class="thumb"
                  :alt="`《${b.name}》封面`"
                  loading="lazy"
                  @error="handleCoverError(b)"
                />
                <div v-else class="thumb thumb-placeholder" :style="resultPlaceholderStyle(b.name)" aria-hidden="true">
                  <span class="thumb-text">{{ (b.name || '书').slice(0, 4) }}</span>
                </div>
              </div>
              <div class="r-info">
                <div class="r-name" v-html="highlightKeyword(b.name)"></div>
                <div class="r-author" v-html="highlightKeyword(b.author || '作者不详')"></div>
                <p v-if="b.intro" class="r-intro">{{ b.intro }}</p>
              </div>
              <div class="r-arrow" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </div>
            </article>
          </div>
          <div v-else-if="group.error" class="source-empty-hint">
            {{ group.error }}
          </div>
        </div>
      </div>
    </div>

    <!-- 无结果提示 -->
    <div v-else-if="searched && !searching" class="empty-result" aria-live="polite">
      <div class="empty-icon" aria-hidden="true">
        <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8" stroke="var(--color-accent)" opacity="0.4"/>
          <path d="m21 21-4.35-4.35" stroke="var(--color-accent)" opacity="0.4"/>
          <line x1="8" y1="11" x2="14" y2="11" stroke="var(--color-text-muted)" stroke-width="1.5"/>
        </svg>
      </div>
      <p class="empty-title">未找到「{{ lastKeyword }}」相关内容</p>
      <p class="empty-desc">请检查书源规则或更换关键词再试</p>
    </div>

    <!-- 搜索初始加载骨架屏 -->
    <div v-if="searching && !results.length" class="skeleton-list" aria-hidden="true">
      <div v-for="n in 4" :key="n" class="skeleton-card">
        <div class="skeleton-thumb"></div>
        <div class="skeleton-lines">
          <div class="sk-line"></div>
          <div class="sk-line sk-short"></div>
          <div class="sk-line sk-shorter"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useSearchStore } from '@/stores/search'
import { initBookPreview } from '@/api'
import type { Book } from '@/types'

const router = useRouter()
const route = useRoute()
const searchStore = useSearchStore()

const {
  keyword,
  lastKeyword,
  searching,
  searched,
  results,
  viewMode,
  collapsedGroupIds,
  failedCovers,
  allSources,
  selectedSourceIds,
  isSourceFilterExpanded,
  sourceSearchInput,
  totalSources,
  completedSources,
  isAllSelected,
  visibleSourcesCompact,
  filteredSourcesInPanel,
  totalBooksFound,
  isAllGroupsCollapsed,
  weightedBooks,
  sortedResultsByGroup,
} = storeToRefs(searchStore)

const {
  loadSources,
  toggleSelectAll,
  selectAllSources,
  invertSelectSources,
  clearSelectSources,
  toggleSource,
  toggleGroupCollapse,
  toggleCollapseAllGroups,
  handleCoverError,
  startSearch,
  stopSearch,
  resetSearch,
} = searchStore

function startStreamSearch() {
  const kw = keyword.value.trim()
  if (!kw) {
    ElMessage.warning('请输入搜索关键字')
    return
  }
  const ok = startSearch()
  if (!ok) {
    ElMessage.warning('请输入有效的搜索关键字')
  }
}

function handleStopSearch() {
  stopSearch()
  ElMessage.info('已停止剩余书源检索')
}

function highlightKeyword(text: string): string {
  const kw = (lastKeyword.value || keyword.value).trim()
  if (!kw || !text) return text || ''
  const regex = new RegExp(`(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<span class="kw-hl">$1</span>')
}

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

const GRADIENTS = [
  ['#c0692e', '#8b3a10'],
  ['#2e7d6e', '#1a4a42'],
  ['#b8863a', '#7a5520'],
  ['#5c4a8a', '#3a2e5c'],
  ['#2e6b8a', '#1a3d52'],
  ['#8a4a2e', '#5c2810'],
]

function resultPlaceholderStyle(name: string): Record<string, string> {
  const str = name || '书'
  const idx = str.charCodeAt(0) % GRADIENTS.length
  const [from, to] = GRADIENTS[idx]
  return { background: `linear-gradient(145deg, ${from}, ${to})` }
}

async function open(book: Book) {
  const bookAny = book as any
  const bookUrl: string = bookAny.bookUrl || bookAny.source_url || bookAny.sourceUrl || ''
  const sourceId: number = Number(bookAny.sourceId || bookAny.source_id || 0)

  if (!bookUrl || !sourceId) {
    ElMessage.warning('该书籍缺少地址信息，无法直接阅读')
    return
  }

  const uuid = book.uuid || generateUUID()
  book.uuid = uuid

  try {
    const saved = await initBookPreview({
      uuid,
      name: book.name,
      author: book.author || '',
      cover: book.cover || '',
      intro: book.intro || '',
      bookUrl,
      sourceId,
      inBookcase: false,
    })

    router.push({ name: 'read', params: { book: saved.uuid || uuid } })
  } catch (e: any) {
    router.push({ name: 'read', params: { book: uuid } })
  }
}

onMounted(() => {
  loadSources()
  // 如果 URL 包含 ?q= 并且与当前搜索词不一致，自动触发搜索
  const queryQ = String(route.query.q || '').trim()
  if (queryQ && queryQ !== lastKeyword.value) {
    keyword.value = queryQ
    startStreamSearch()
  }
})

// 离开页面时终止搜索流，但完全保留 Pinia 中的已搜索缓存数据
onBeforeRouteLeave(() => {
  stopSearch()
})

onUnmounted(() => {
  stopSearch()
})
</script>

<style scoped>
/* ─── 页面容器 ────────────────────────────────────────────── */
.search-page {
  max-width: 840px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}

/* ─── 搜索英雄区 ──────────────────────────────────────────── */
.search-hero {
  text-align: center;
  margin-bottom: 28px;
}

.search-heading {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
  margin: 0 0 6px;
}

.search-sub {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0 0 20px;
}

.search-bar {
  display: flex;
  gap: 10px;
  max-width: 660px;
  margin: 0 auto;
}

.search-field {
  position: relative;
  flex: 1;
}

.search-field-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 12px 14px 12px 44px;
  border: 1.5px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-family: var(--font-ui);
  font-size: 15px;
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.search-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-pale);
}

.btn-search {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 24px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-lg);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.02em;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.btn-search:hover {
  background: var(--color-accent-light);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.btn-stop {
  background: #f5222d;
}

.btn-stop:hover {
  background: #ff4d4f;
}

/* ─── 可折叠书源选择器栏 ────────────────────────────────── */
.source-collapse-container {
  max-width: 660px;
  margin: 16px auto 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: all 0.25s ease;
}

.source-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  gap: 8px;
  background: var(--color-surface);
}

.summary-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-label {
  font-size: 12px;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.btn-toggle-expand {
  display: flex;
  align-items: center;
  font-size: 11.5px;
  color: var(--color-accent);
  background: var(--color-accent-pale);
  border: 1px solid rgba(184, 134, 58, 0.2);
  padding: 4px 10px;
  border-radius: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.btn-toggle-expand:hover {
  background: rgba(184, 134, 58, 0.2);
}

.btn-toggle-expand.expanded {
  background: var(--color-accent);
  color: #fff;
}

/* 展开后的面板 */
.source-expanded-panel {
  padding: 12px 14px 14px;
  border-top: 1px dashed var(--color-border-subtle);
  background: var(--color-bg);
  animation: panelSlide 0.2s ease-out;
}

@keyframes panelSlide {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.panel-header-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.source-search-input {
  flex: 1;
  max-width: 260px;
  padding: 5px 10px;
  font-size: 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 6px;
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
}

.source-search-input:focus {
  border-color: var(--color-accent);
}

.panel-action-btns {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
}

.btn-text {
  background: none;
  border: none;
  color: var(--color-accent);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}

.btn-text:hover {
  text-decoration: underline;
}

.btn-sep {
  color: var(--color-text-muted);
  opacity: 0.4;
}

.source-chips-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
  padding: 2px;
}

.source-chip {
  font-size: 11.5px;
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.source-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.source-chip.active {
  background: var(--color-accent);
  color: #ffffff;
  border-color: var(--color-accent);
}

.main-all-chip {
  font-weight: 600;
}

.no-matched-source {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 12px 0;
  width: 100%;
  text-align: center;
}

/* ─── 实时进度条与统计 ─────────────────────────────────────── */
.search-progress-box {
  max-width: 660px;
  margin: 18px auto 0;
  padding: 12px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

.progress-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.progress-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.group-collapse-tools {
  display: flex;
  align-items: center;
}

.btn-collapse-all {
  background: none;
  border: 1px solid var(--color-border-subtle);
  padding: 3px 8px;
  font-size: 11.5px;
  border-radius: 4px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-collapse-all:hover {
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.spin-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-accent);
  margin-right: 6px;
  animation: pulse 1.2s infinite ease-in-out;
}

@keyframes pulse {
  0%, 100% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.3); opacity: 1; }
}

.done-text {
  color: #52c41a;
  font-weight: 500;
}

.found-counter strong {
  color: var(--color-accent);
  font-size: 14px;
}

.view-mode-toggle {
  display: flex;
  background: var(--color-bg);
  padding: 2px;
  border-radius: 6px;
  border: 1px solid var(--color-border-subtle);
  gap: 2px;
}

.btn-mode {
  border: none;
  background: transparent;
  padding: 3px 8px;
  font-size: 11.5px;
  border-radius: 4px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-mode.active {
  background: var(--color-surface);
  color: var(--color-accent);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.progress-track {
  margin-top: 10px;
  height: 4px;
  background: var(--color-bg-subtle);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--color-accent), var(--color-accent-light));
  transition: width 0.3s ease;
}

/* ─── 结果列表 ────────────────────────────────────────────── */
.weighted-results-container,
.results-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.source-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  transition: all 0.2s ease;
  animation: fadeIn 0.3s ease-out forwards;
}

.source-group.collapsed {
  padding: 10px 16px;
  background: var(--color-bg);
  opacity: 0.85;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.clickable-header {
  cursor: pointer;
  user-select: none;
  transition: opacity 0.15s ease;
}

.clickable-header:hover {
  opacity: 0.8;
}

.source-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.source-group.collapsed .source-header {
  padding-bottom: 0;
  border-bottom: none;
}

.source-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-caret {
  font-size: 10px;
  color: var(--color-text-muted);
  transition: transform 0.2s ease;
  display: inline-block;
}

.collapse-caret.rotated {
  transform: rotate(90deg);
}

.source-tag {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent);
  background: var(--color-accent-pale);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
}

.source-err-badge {
  font-size: 11px;
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.source-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-count {
  font-size: 12px;
  color: var(--color-text-muted);
}

.collapse-tip-text {
  font-size: 11px;
  color: var(--color-accent);
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
}

.result-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  cursor: pointer;
  transition: all var(--transition-base);
}

.result-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-md), 0 0 0 1px var(--color-accent-glow);
  transform: translateX(3px);
}

.result-card:active {
  transform: translateX(1px);
}

.thumb-wrap {
  flex-shrink: 0;
}

.thumb {
  width: 52px;
  height: 70px;
  border-radius: var(--radius-sm);
  object-fit: cover;
}

.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 248, 220, 0.9);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.r-info {
  flex: 1;
  min-width: 0;
}

.r-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.r-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.r-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.tag-match {
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.tag-match.exact {
  background: rgba(82, 196, 26, 0.12);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.25);
}

.tag-match.prefix {
  background: var(--color-accent-pale);
  color: var(--color-accent);
}

.tag-match.author {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.source-badge {
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg-subtle);
  padding: 1px 7px;
  border-radius: 4px;
  border: 1px solid var(--color-border-subtle);
}

.r-author {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 4px 0 6px;
}

:deep(.kw-hl) {
  color: #ed424b;
  font-weight: 700;
}

.r-intro {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.5;
  margin: 0;
}

.r-arrow {
  flex-shrink: 0;
  color: var(--color-text-muted);
  transition: color var(--transition-base), transform var(--transition-base);
}

.result-card:hover .r-arrow {
  color: var(--color-accent);
  transform: translateX(2px);
}

.source-empty-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 8px 12px;
  background: var(--color-surface);
  border-radius: var(--radius-sm);
}

/* ─── 空结果 ──────────────────────────────────────────────── */
.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
  gap: 10px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 4px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

/* ─── 骨架屏 ──────────────────────────────────────────────── */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-card {
  display: flex;
  gap: 14px;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  border: 1px solid var(--color-border-subtle);
}

.skeleton-thumb {
  width: 52px;
  height: 70px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  background: linear-gradient(90deg, var(--color-bg-subtle) 25%, var(--color-bg) 50%, var(--color-bg-subtle) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.sk-line {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--color-bg-subtle) 25%, var(--color-bg) 50%, var(--color-bg-subtle) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.sk-short { width: 60%; height: 10px; }
.sk-shorter { width: 80%; height: 9px; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ─── 移动端响应式适配 (<= 768px) ────────────────────────── */
@media (max-width: 768px) {
  .search-hero {
    padding: 16px 12px 20px;
  }

  .search-heading {
    font-size: 18px;
    margin-bottom: 4px;
  }

  .search-sub {
    font-size: 12px;
    margin-bottom: 14px;
  }

  .search-bar {
    max-width: 100%;
  }

  .search-input {
    font-size: 14px;
    padding: 10px 12px 10px 38px;
  }

  .btn-search {
    padding: 10px 16px;
    font-size: 13px;
  }

  .source-summary-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .summary-left {
    overflow-x: auto;
    white-space: nowrap;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
  }

  .progress-panel {
    padding: 12px 14px;
  }

  .progress-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .progress-right {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }

  .weighted-results-container,
  .grouped-results-container {
    padding: 0 12px 24px;
  }

  .result-card {
    padding: 12px 10px;
    gap: 12px;
  }

  .thumb {
    width: 54px;
    height: 72px;
  }

  .r-top-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .r-tags {
    flex-wrap: wrap;
  }

  .r-meta-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .r-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>