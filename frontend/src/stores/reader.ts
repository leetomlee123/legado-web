/**
 * Reader Store — 管理当前正在阅读的书籍状态
 *
 * 两种阅读模式：
 * - 本地书架模式（mode: 'local'）：book.id > 0，通过 /api/books/:id/chapters 获取目录
 * - 预览模式（mode: 'preview'）：无 DB id，通过 /api/preview/toc 和 /api/preview/content
 *   实时抓取章节列表和正文，不写入数据库
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 预览章节（不在 DB 中，用 chapterUrl 区分）
export interface PreviewChapter {
  index: number
  title: string
  chapterUrl: string
}

// 预览书籍信息（来自搜索结果）
export interface PreviewBook {
  name: string
  author?: string
  cover?: string
  intro?: string
  bookUrl: string    // 书籍主页 URL（用于抓取目录）
  sourceId: number   // 书源 ID
  sourceName?: string
}

type ReaderMode = 'local' | 'preview'

export const useReaderStore = defineStore('reader', () => {
  // ── 当前阅读模式 ──────────────────────────────────────
  const mode = ref<ReaderMode>('local')

  // ── 预览模式专用数据 ──────────────────────────────────
  const previewBook = ref<PreviewBook | null>(null)
  const previewChapters = ref<PreviewChapter[]>([])
  const previewChapterIndex = ref(0)

  // ── 通用状态 ──────────────────────────────────────────
  // 本地模式下的书架 bookId（用于路由参数）
  const localBookId = ref<number>(0)

  const isPreview = computed(() => mode.value === 'preview')

  // ── 动作 ──────────────────────────────────────────────
  /**
   * 进入预览模式（从搜索结果点击）
   * @param book 搜索结果中的书籍信息
   */
  function openPreview(book: PreviewBook) {
    mode.value = 'preview'
    previewBook.value = book
    previewChapters.value = []
    previewChapterIndex.value = 0
  }

  /**
   * 进入本地书架模式
   * @param bookId 书架中的书籍 ID
   */
  function openLocal(bookId: number) {
    mode.value = 'local'
    localBookId.value = bookId
    previewBook.value = null
    previewChapters.value = []
  }

  /**
   * 预览模式：缓存目录数据（避免重复抓取）
   */
  function setPreviewChapters(chapters: PreviewChapter[]) {
    previewChapters.value = chapters
  }

  /**
   * 设置当前章节下标
   */
  function setChapterIndex(index: number) {
    previewChapterIndex.value = index
  }

  /**
   * 清除所有状态（离开阅读页时调用）
   */
  function clear() {
    mode.value = 'local'
    previewBook.value = null
    previewChapters.value = []
    previewChapterIndex.value = 0
    localBookId.value = 0
  }

  return {
    mode,
    previewBook,
    previewChapters,
    previewChapterIndex,
    localBookId,
    isPreview,
    openPreview,
    openLocal,
    setPreviewChapters,
    setChapterIndex,
    clear,
  }
})
