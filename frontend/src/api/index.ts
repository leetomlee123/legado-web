import http from '@/utils/http'
import type {
  Book,
  BookSource,
  Chapter,
  ImportResult,
  Paged,
  SourceSearchRes,
  ReadProgress,
} from '@/types'

// 书架
export async function listBooks(
  keyword?: string,
  group?: string,
  page = 0,
  size = 20,
): Promise<Paged<Book>> {
  const params: Record<string, any> = { page, size }
  if (keyword) params.keyword = keyword
  if (group) params.group = group
  const res = await http.get('/books', { params })
  return res as unknown as Paged<Book>
}

// 导入 TXT
export async function importTxt(file: File): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await http.post('/books/import/txt', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res as unknown as ImportResult
}

// 导入 EPUB
export async function importEpub(file: File): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await http.post('/books/import/epub', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res as unknown as ImportResult
}

// 导入 PDF
export async function importPdf(file: File): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await http.post('/books/import/pdf', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res as unknown as ImportResult
}

// 获取书籍详情
export async function getBook(identifier: number | string): Promise<Book> {
  const res = await http.get(`/books/${identifier}`)
  return res as unknown as Book
}

// 删除书籍
export async function deleteBook(identifier: number | string): Promise<void> {
  await http.delete(`/books/${identifier}`)
}

// 批量删除书籍
export async function batchDeleteBooks(identifiers: (number | string)[]): Promise<{ count: number }> {
  const res = await http.post('/books/batch-delete', { identifiers })
  return res as unknown as { count: number }
}

// 章节列表
export async function listChapters(identifier: number | string): Promise<Chapter[]> {
  const res = await http.get(`/books/${identifier}/chapters`)
  return res as unknown as Chapter[]
}

// 获取章节内容
export async function getChapterContent(
  identifier: number | string,
  cid: number
): Promise<{ content: string }> {
  const res = await http.get(`/books/${identifier}/chapters/${cid}/content`)
  return res as unknown as { content: string }
}

// 预初始化书籍（通过 UUID 注册为非书架或书架书籍）
export async function initBookPreview(book: Partial<Book>): Promise<Book> {
  const res = await http.post('/books/init-preview', book)
  return res as unknown as Book
}

// 加入书架
export async function addBookToShelf(identifier: number | string): Promise<Book> {
  const res = await http.post(`/books/${identifier}/add-to-shelf`)
  return res as unknown as Book
}

// 获取阅读进度
export async function getReadProgress(identifier: number | string): Promise<ReadProgress> {
  const res = await http.get(`/books/${identifier}/progress`)
  return res as unknown as ReadProgress
}

// 保存阅读进度
export async function saveReadProgress(
  identifier: number | string,
  data: { chapterId: number; chapterIndex: number; pos?: number }
): Promise<void> {
  await http.post(`/books/${identifier}/progress`, data)
}

// 封面
export function coverUrl(identifier: number | string): string {
  return `/books/${identifier}/cover`
}

// 书源管理
export async function listSources(): Promise<BookSource[]> {
  const res = await http.get('/sources')
  return res as unknown as BookSource[]
}

export async function saveSource(source: BookSource): Promise<BookSource> {
  const res = source.id
    ? await http.put(`/sources/${source.id}`, source)
    : await http.post('/sources', source)
  return res as unknown as BookSource
}

export async function deleteSource(id: number): Promise<void> {
  await http.delete(`/sources/${id}`)
}

export async function batchDeleteSources(ids: number[]): Promise<{ ok: boolean; deletedCount: number }> {
  const res = await http.post('/sources/batch-delete', { ids })
  return res as unknown as { ok: boolean; deletedCount: number }
}

export async function batchToggleSources(ids: number[], enabled: boolean): Promise<{ ok: boolean; updatedCount: number }> {
  const res = await http.post('/sources/batch-toggle', { ids, enabled: enabled ? 1 : 0 })
  return res as unknown as { ok: boolean; updatedCount: number }
}

export async function importSourceUrl(
  url: string,
  name?: string,
): Promise<any> {
  const res = await http.post('/sources/import', { url, name })
  return res
}

export async function importSourceText(
  text: string,
  name?: string,
): Promise<any> {
  const res = await http.post('/sources/import', { text, name })
  return res
}

export async function importSourceFile(file: File): Promise<any> {
  const form = new FormData()
  form.append('file', file)
  const res = await http.post('/sources/import/file', form)
  return res
}

export async function getSourcePresets(): Promise<{ name: string; url: string; desc: string }[]> {
  const res = await http.get('/sources/presets')
  return res as unknown as { name: string; url: string; desc: string }[]
}

// 多源搜索 (标准并发)
export async function searchAll(
  keyword: string,
  sourceIds?: number[],
): Promise<SourceSearchRes[]> {
  const params: Record<string, any> = { keyword }
  if (sourceIds?.length) params.sourceIds = sourceIds.join(',')
  const res = await http.get('/search/all', { params })
  return res as unknown as SourceSearchRes[]
}

// SSE 流式多源搜索（逐源即时推送，先搜先出）
export function searchStream(
  keyword: string,
  sourceIds?: number[],
  onEvent?: (event: {
    type: string
    sourceId?: number
    sourceName?: string
    books?: Book[]
    error?: string
    completed?: number
    totalSources?: number
    totalBooks?: number
  }) => void,
  onDone?: () => void,
  onError?: (err: any) => void
): () => void {
  const controller = new AbortController()
  const params = new URLSearchParams({ keyword })
  if (sourceIds?.length) {
    params.set('sourceIds', sourceIds.join(','))
  }

  fetch(`/api/search/stream?${params.toString()}`, {
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const block of lines) {
          const trimmed = block.trim()
          if (!trimmed.startsWith('data:')) continue
          try {
            const data = JSON.parse(trimmed.slice(5).trim())
            onEvent?.(data)
            if (data.type === 'done') {
              onDone?.()
            }
          } catch (e) {
            console.debug('[sse parse err]', e)
          }
        }
      }
      onDone?.()
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError?.(err)
    })

  return () => controller.abort()
}

// 设置
export interface AppSettings {
  proxy: string
  timeout?: number
  max_workers?: number
}

export async function getSettings(): Promise<AppSettings> {
  const res = await http.get('/settings')
  return res as unknown as AppSettings
}

export async function saveSettings(settings: Partial<AppSettings>): Promise<AppSettings> {
  const res = await http.post('/settings', settings)
  return res as unknown as AppSettings
}

// ─── 预览模式（免入书架实时抓取）────────────────────────

export interface PreviewChapterItem {
  index: number
  title: string
  chapterUrl: string
}

/**
 * 通过 bookUrl + sourceId 实时抓取章节目录（不写 DB）
 */
export async function previewToc(bookUrl: string, sourceId: number): Promise<PreviewChapterItem[]> {
  const res = await http.post('/preview/toc', { bookUrl, sourceId })
  return res as unknown as PreviewChapterItem[]
}

/**
 * 通过 chapterUrl + sourceId 实时抓取章节正文（不写 DB）
 */
export async function previewContent(chapterUrl: string, sourceId: number): Promise<string> {
  const res = await http.post('/preview/content', { chapterUrl, sourceId })
  return (res as any)?.content || ''
}