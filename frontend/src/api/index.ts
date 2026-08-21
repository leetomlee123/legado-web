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

// 切换书源
export async function changeBookSource(
  identifier: number | string,
  data: {
    sourceId: number
    bookUrl: string
    name?: string
    author?: string
    cover?: string
    intro?: string
    currentChapterTitle?: string
    currentChapterIndex?: number
  }
): Promise<{
  ok: boolean
  book: Book
  newChapterIndex: number
  newChapterId: number
  newChapterTitle: string
  totalChapters: number
  sourceName?: string
  message?: string
}> {
  const res = await http.post(`/books/${identifier}/change-source`, data)
  return res as any
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
  timeout?: number,
): Promise<any> {
  const res = await http.post('/sources/import', { url, name, timeout })
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

export interface SourceDelayResult {
  sourceId: number
  sourceName?: string
  success: boolean
  delay: number
  status?: number
  error?: string | null
}

export async function testSourceDelay(sourceId: number): Promise<SourceDelayResult> {
  const res = await http.post(`/sources/${sourceId}/test-delay`)
  return res as unknown as SourceDelayResult
}

export async function batchTestSourceDelay(sourceIds?: number[]): Promise<SourceDelayResult[]> {
  const res = await http.post('/sources/batch-test-delay', { sourceIds })
  return res as unknown as SourceDelayResult[]
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

export async function stopBackendSearch(searchId?: string): Promise<{ ok: boolean; stoppedCount: number }> {
  const res = await http.post('/search/stop', { searchId })
  return res as unknown as { ok: boolean; stoppedCount: number }
}

// SSE 流式多源搜索（逐源即时推送，先搜先出，支持客户端断开立即取消后台检索）
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
    searchId?: string
  }) => void,
  onDone?: () => void,
  onError?: (err: any) => void
): () => void {
  const controller = new AbortController()
  const searchId = `search_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
  const params = new URLSearchParams({ keyword, searchId })
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

  return () => {
    controller.abort()
    // 双重保底：发送显式停止请求通知后端彻底中止后台线程池
    http.post('/search/stop', { searchId }).catch(() => {})
  }
}

// 设置
export interface AppSettings {
  proxy: string
  timeout?: number
  max_workers?: number
  health_check_enabled?: boolean
  health_check_interval?: number
  auto_disable_dead?: boolean
}

export async function getSettings(): Promise<AppSettings> {
  const res = await http.get('/settings')
  return res as unknown as AppSettings
}

export async function saveSettings(settings: AppSettings): Promise<AppSettings> {
  const res = await http.post('/settings', settings)
  return res as unknown as AppSettings
}

export interface ProxyTestResult {
  ok: boolean
  delay: number
  ip?: string
  status?: number
  error?: string
  proxy?: string
}

export async function testProxy(proxy?: string): Promise<ProxyTestResult> {
  const res = await http.post('/settings/test-proxy', { proxy })
  return res as unknown as ProxyTestResult
}

// ─── 书源健康度巡检 API ────────────────────────────────

export interface HealthSourceResult {
  sourceId: number
  sourceName: string
  category: 'healthy' | 'slow' | 'dead'
  delay: number
  status?: number
  error?: string | null
  checkTime: string
}

export interface HealthStatusRes {
  scanning: boolean
  enabled: boolean
  intervalHours: number
  autoDisableDead: boolean
  lastScanTime: string
  total: number
  healthy: number
  slow: number
  dead: number
  results: Record<number, HealthSourceResult>
}

export async function getHealthStatus(): Promise<HealthStatusRes> {
  const res = await http.get('/sources/health/status')
  return res as unknown as HealthStatusRes
}

export async function runHealthCheck(): Promise<{ ok: boolean; message: string }> {
  const res = await http.post('/sources/health/run')
  return res as unknown as { ok: boolean; message: string }
}

export async function disableDeadSources(): Promise<{ ok: boolean; disabledCount: number; message: string }> {
  const res = await http.post('/sources/health/disable-dead')
  return res as unknown as { ok: boolean; disabledCount: number; message: string }
}

export async function deleteDeadSources(): Promise<{ ok: boolean; deletedCount: number; message: string }> {
  const res = await http.post('/sources/health/delete-dead')
  return res as unknown as { ok: boolean; deletedCount: number; message: string }
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

// ─── 系统日志 API ──────────────────────────────────────

export interface LogItem {
  id: number
  time: string
  created: number
  level: string
  logger: string
  message: string
  module: string
  line: number
}

export interface LogsResult {
  total: number
  items: LogItem[]
  maxBuffer: number
}

export async function getLogs(params?: {
  level?: string
  keyword?: string
  limit?: number
  offset?: number
}): Promise<LogsResult> {
  const res = await http.get('/logs', { params })
  return res as unknown as LogsResult
}

export async function clearLogs(): Promise<{ ok: boolean; message: string }> {
  const res = await http.post('/logs/clear')
  return res as unknown as { ok: boolean; message: string }
}

export function subscribeLogsStream(
  onLog: (item: LogItem) => void,
  onError?: (err: any) => void
): () => void {
  const controller = new AbortController()

  fetch('/api/logs/stream', {
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
            if (data.type === 'log' && data.data) {
              onLog(data.data)
            }
          } catch (e) {
            // ignore
          }
        }
      }
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError?.(err)
    })

  return () => controller.abort()
}