export interface Book {
  id?: number
  uuid?: string
  name: string
  author?: string
  cover?: string
  intro?: string
  source_type?: string
  sourceType?: string
  source_url?: string
  sourceUrl?: string
  bookUrl?: string
  source_id?: number
  sourceId?: number
  source_name?: string
  sourceName?: string
  local_path?: string
  book_group?: string
  in_bookcase?: number
  inBookcase?: number | boolean
  last_read_time?: number
  create_time?: number
  has_update?: number
  hasUpdate?: number
}

export interface BookSource {
  id?: number
  name: string
  url: string
  rule: string
  enabled?: boolean | number
}

export interface Chapter {
  id: number
  bookId: number
  title: string
  index: number
  contentUrl?: string
}

export interface ImportResult {
  success: number
  failed: number
  bookId?: number
  chapterCount?: number
  cover?: string
  message?: string
}

export interface Paged<T> {
  items: T[]
  total: number
}

export interface SourceSearchRes {
  sourceId: number
  sourceName: string
  books: Book[]
  error?: string
}

export interface ReadProgress {
  bookId: number
  chapterId: number
  chapterIndex: number
  pos?: number
  updateTime?: number
}
