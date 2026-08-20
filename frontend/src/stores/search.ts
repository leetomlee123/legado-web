/**
 * Search Store — 管理小说多源并发搜索状态、缓存与流式控制
 *
 * 核心特性：
 * 1. 状态持久：从阅读页或书架页返回搜索页时，保留搜索词、结果列表、加权视图模式与折叠状态；
 * 2. 离开自停：离开搜索页面时自动终止未完成的流式请求，并完好保留已检索到的书籍；
 * 3. 智能权重：内存中保持所有书源返回结果并支持加权排序与分组折叠切换。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { searchStream, listSources } from '@/api'
import type { SourceSearchRes, Book, BookSource } from '@/types'

export type ViewMode = 'weighted' | 'grouped'
export type MatchLevel = 'exact' | 'prefix' | 'author' | 'contains' | 'other'

export interface ScoredBook extends Book {
  sourceName: string
  score: number
  matchLevel: MatchLevel
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

export function computeRelevance(book: Book, kw: string): { score: number; matchLevel: MatchLevel } {
  if (!book) return { score: 0, matchLevel: 'other' }
  const q = (kw || '').trim().toLowerCase()
  if (!q) return { score: 0, matchLevel: 'other' }

  const name = (book.name || '').trim().toLowerCase()
  const author = (book.author || '').trim().toLowerCase()
  const intro = (book.intro || '').trim().toLowerCase()

  let score = 0
  let matchLevel: MatchLevel = 'other'

  if (name === q) {
    score += 1200
    matchLevel = 'exact'
  } else if (name.startsWith(q)) {
    score += 700
    matchLevel = 'prefix'
    score += Math.max(0, 50 - (name.length - q.length) * 2)
  } else if (name.includes(q)) {
    score += 400
    matchLevel = 'contains'
    score += Math.max(0, 30 - (name.length - q.length) * 2)
  }

  if (author === q) {
    score += 600
    if (matchLevel === 'other') matchLevel = 'author'
  } else if (author.includes(q)) {
    score += 250
    if (matchLevel === 'other') matchLevel = 'author'
  }

  if (intro.includes(q)) {
    score += 50
  }

  if (book.cover) score += 15
  if (book.intro && book.intro.length > 20) score += 10

  return { score, matchLevel }
}

export const useSearchStore = defineStore('search', () => {
  // ── 搜索输入与状态 ──────────────────────────────────────
  const keyword = ref('')
  const lastKeyword = ref('')
  const searching = ref(false)
  const searched = ref(false)

  // ── 搜索结果与界面状态 ──────────────────────────────────
  const results = ref<SourceSearchRes[]>([])
  const viewMode = ref<ViewMode>('weighted')
  const collapsedGroupIds = ref<Set<number>>(new Set())
  const failedCovers = ref<Set<string>>(new Set())

  // ── 书源筛选与配置 ──────────────────────────────────────
  const allSources = ref<BookSource[]>([])
  const selectedSourceIds = ref<number[]>([])
  const isSourceFilterExpanded = ref(false)
  const sourceSearchInput = ref('')

  // ── 流式统计 ────────────────────────────────────────────
  const totalSources = ref(0)
  const completedSources = ref(0)
  let abortFn: (() => void) | null = null

  // ── Computed 计算属性 ───────────────────────────────────
  const isAllSelected = computed(() => {
    const all = allSources.value || []
    const selected = selectedSourceIds.value || []
    return all.length > 0 && selected.length === all.length
  })

  const visibleSourcesCompact = computed(() => {
    const list = Array.isArray(allSources.value) ? allSources.value : []
    return list.slice(0, 5)
  })

  const filteredSourcesInPanel = computed(() => {
    const q = (sourceSearchInput.value || '').trim().toLowerCase()
    const list = Array.isArray(allSources.value) ? allSources.value : []
    if (!q) return list
    return list.filter((s) => s && (s.name || '').toLowerCase().includes(q))
  })

  const totalBooksFound = computed(() => {
    if (!Array.isArray(results.value)) return 0
    return results.value.reduce((acc, cur) => acc + (cur && Array.isArray(cur.books) ? cur.books.length : 0), 0)
  })

  const isAllGroupsCollapsed = computed(() => {
    if (!results.value || !results.value.length) return false
    return results.value.every((g) => g && collapsedGroupIds.value && collapsedGroupIds.value.has(g.sourceId))
  })

  /** 综合加权排序后的所有书籍列表 */
  const weightedBooks = computed<ScoredBook[]>(() => {
    const kw = (lastKeyword.value || keyword.value || '').trim()
    const list: ScoredBook[] = []
    const groupList = Array.isArray(results.value) ? results.value : []

    for (const group of groupList) {
      if (!group) continue
      const books = Array.isArray(group.books) ? group.books : []
      for (const b of books) {
        if (!b) continue
        const { score, matchLevel } = computeRelevance(b, kw)
        list.push({
          ...b,
          sourceName: group.sourceName || '未知书源',
          score,
          matchLevel,
        })
      }
    }

    return list.sort((a, b) => b.score - a.score)
  })

  /** 分组模式下每组内部也按权重排序 */
  const sortedResultsByGroup = computed(() => {
    const kw = (lastKeyword.value || keyword.value || '').trim()
    const arr = Array.isArray(results.value) ? results.value : []
    return arr.map((group) => {
      if (!group) return { sourceId: 0, sourceName: '', books: [] }
      const books = Array.isArray(group.books) ? group.books : []
      const sorted = books.slice().sort((a, b) => {
        return computeRelevance(b, kw).score - computeRelevance(a, kw).score
      })
      return {
        ...group,
        books: sorted,
      }
    })
  })

  // ── Actions 业务方法 ────────────────────────────────────

  async function loadSources() {
    if (allSources.value.length > 0) return
    try {
      const list = await listSources()
      const arr = Array.isArray(list) ? list : []
      allSources.value = arr.filter((s) => s && s.enabled)
      if (!selectedSourceIds.value.length) {
        selectedSourceIds.value = allSources.value.map((s) => s.id!).filter(Boolean)
      }
    } catch (e) {
      console.debug('获取书源列表失败:', e)
    }
  }

  function toggleSelectAll() {
    if (isAllSelected.value) {
      selectedSourceIds.value = []
    } else {
      selectedSourceIds.value = (allSources.value || []).map((s) => s.id!).filter(Boolean)
    }
  }

  function selectAllSources() {
    selectedSourceIds.value = (allSources.value || []).map((s) => s.id!).filter(Boolean)
  }

  function invertSelectSources() {
    const currentSet = new Set(selectedSourceIds.value || [])
    selectedSourceIds.value = (allSources.value || [])
      .map((s) => s.id!)
      .filter((id) => id && !currentSet.has(id))
  }

  function clearSelectSources() {
    selectedSourceIds.value = []
  }

  function toggleSource(id: number) {
    const idx = selectedSourceIds.value.indexOf(id)
    if (idx > -1) {
      selectedSourceIds.value.splice(idx, 1)
    } else {
      selectedSourceIds.value.push(id)
    }
  }

  function toggleGroupCollapse(sourceId: number) {
    if (collapsedGroupIds.value.has(sourceId)) {
      collapsedGroupIds.value.delete(sourceId)
    } else {
      collapsedGroupIds.value.add(sourceId)
    }
  }

  function toggleCollapseAllGroups() {
    if (isAllGroupsCollapsed.value) {
      collapsedGroupIds.value.clear()
    } else {
      ;(results.value || []).forEach((g) => {
        if (g && g.sourceId) collapsedGroupIds.value.add(g.sourceId)
      })
    }
  }

  function handleCoverError(book: Book) {
    if (!book) return
    failedCovers.value.add(book.uuid || book.name)
  }

  /**
   * 启动 SSE 流式多源并发搜索
   */
  function startSearch(kwOverride?: string) {
    const kw = (kwOverride || keyword.value).trim()
    if (!kw) return false

    // 如果先前有正在进行的搜索流，立即中止
    stopSearch()

    searching.value = true
    searched.value = true
    lastKeyword.value = kw
    results.value = []
    collapsedGroupIds.value.clear()
    completedSources.value = 0
    totalSources.value = selectedSourceIds.value.length || allSources.value.length

    const filterIds = selectedSourceIds.value.length ? selectedSourceIds.value : undefined

    abortFn = searchStream(
      kw,
      filterIds,
      (evt) => {
        if (evt.type === 'start') {
          totalSources.value = evt.totalSources || 0
        } else if (evt.type === 'source_result') {
          completedSources.value = evt.completed || (completedSources.value + 1)
          totalSources.value = evt.totalSources || totalSources.value

          const rawBooks = Array.isArray(evt.books) ? evt.books : []
          rawBooks.forEach((b: Book) => {
            if (!b.uuid) {
              b.uuid = generateUUID()
            }
          })

          if (rawBooks.length > 0 || evt.error) {
            results.value.push({
              sourceId: evt.sourceId!,
              sourceName: evt.sourceName || '未知书源',
              books: rawBooks,
              error: evt.error,
            })

            // 遇到异常或空结果时，默认自动收起该书源以节省空间
            if (evt.error || rawBooks.length === 0) {
              collapsedGroupIds.value.add(evt.sourceId!)
            }
          }
        } else if (evt.type === 'done') {
          searching.value = false
        }
      },
      () => {
        searching.value = false
        abortFn = null
      },
      (err) => {
        searching.value = false
        abortFn = null
        console.warn('搜索流结束:', err)
      }
    )

    return true
  }

  /**
   * 中止搜索：停止流式传输，但完全保留已经搜索到的数据
   */
  function stopSearch() {
    if (abortFn) {
      abortFn()
      abortFn = null
    }
    searching.value = false
  }

  /**
   * 清空所有搜索状态与缓存
   */
  function resetSearch() {
    stopSearch()
    keyword.value = ''
    lastKeyword.value = ''
    results.value = []
    searched.value = false
    completedSources.value = 0
    totalSources.value = 0
    collapsedGroupIds.value.clear()
  }

  return {
    // State
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

    // Computed
    isAllSelected,
    visibleSourcesCompact,
    filteredSourcesInPanel,
    totalBooksFound,
    isAllGroupsCollapsed,
    weightedBooks,
    sortedResultsByGroup,

    // Actions
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
  }
})
