import http from '@/utils/http'
import type {
  Book,
  BookSource,
  Chapter,
  ImportResult,
  Paged,
  SourceSearchRes,
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

// 删除书籍
export async function deleteBook(id: number): Promise<void> {
  await http.delete(`/books/${id}`)
}

// 章节列表
export async function listChapters(bookId: number): Promise<Chapter[]> {
  const res = await http.get(`/books/${bookId}/chapters`)
  return res as unknown as Chapter[]
}

// 封面
export function coverUrl(id: number): string {
  return `/books/${id}/cover`
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

export async function importSourceUrl(
  url: string,
  name?: string,
): Promise<BookSource> {
  const res = await http.post('/sources/import', { url, name })
  return res as unknown as BookSource
}

// 多源搜索
export async function searchAll(
  keyword: string,
  sourceIds?: number[],
): Promise<SourceSearchRes[]> {
  const params: Record<string, any> = { keyword }
  if (sourceIds?.length) params.sourceIds = sourceIds.join(',')
  const res = await http.get('/search/all', { params })
  return res as unknown as SourceSearchRes[]
}

// 设置
export interface AppSettings {
  proxy: string
}

export async function getSettings(): Promise<AppSettings> {
  const res = await http.get('/settings')
  return res as unknown as AppSettings
}

export async function saveSettings(settings: Partial<AppSettings>): Promise<AppSettings> {
  const res = await http.post('/settings', settings)
  return res as unknown as AppSettings
}