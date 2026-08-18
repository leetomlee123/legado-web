<template>
  <div class="reader" :class="{ 'night-mode': night }">
    <div class="reader-top">
      <div class="back" @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </div>
      <div class="reader-title">{{ book?.name }} · {{ current?.title }}</div>
    </div>

    <div class="reader-body" @click="onTapBody">
      <div class="chapter-title">{{ current?.title }}</div>
      <div v-if="loadingChapter" class="reading-loading">
        <el-skeleton :rows="8" animated />
      </div>
      <div v-else class="content" v-html="renderContent()"></div>
    </div>

    <div class="reader-bottom">
      <span class="page-info">
        {{ chapterIndex + 1 }} / {{ chapters.length }}
      </span>
      <div class="nav-btns">
        <el-button link @click="prevChapter" :disabled="chapterIndex <= 0">
          <el-icon><ArrowLeft /></el-icon>上一章
        </el-button>
        <el-button link @click="nextChapter" :disabled="chapterIndex >= chapters.length - 1">
          下一章<el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { listBooks, listChapters } from '@/api'
import type { Book, Chapter } from '@/types'

const route = useRoute()
const router = useRouter()
const bookId = Number(route.params.book)

const book = ref<Book | null>(null)
const chapters = ref<Chapter[]>([])
const current = ref<Chapter | null>(null)
const content = ref('')
const loadingChapter = ref(false)
const night = ref(false)

const chapterIndex = computed(() => {
  const idx = chapters.value.findIndex((c) => c.id === current.value?.id)
  return idx === -1 ? 0 : idx
})

async function loadBook() {
  const res = await listBooks(undefined, undefined, 0, 50)
  const found = res.items.find((b) => b.id === bookId)
  book.value = found || {
    id: bookId,
    name: '阅读',
    sourceType: 'web',
  }
}

async function loadChapters() {
  chapters.value = await listChapters(bookId)
  if (chapters.value.length) {
    await openChapter(chapters.value[0].id)
  }
}

async function openChapter(id: number) {
  current.value = chapters.value.find((c) => c.id === id) || null
  loadingChapter.value = true
  try {
    const res = await fetch(`/api/books/${bookId}/chapters/${id}/content`)
    const data = await res.json()
    content.value = data.content || ''
  } catch {
    content.value = '（章节内容加载失败）'
  } finally {
    loadingChapter.value = false
  }
}

function renderContent() {
  if (!content.value) return ''
  return content.value
    .split('\n')
    .map((p) => `<p>${p}</p>`)
    .join('')
}

function prevChapter() {
  if (chapterIndex.value > 0) openChapter(chapters.value[chapterIndex.value - 1].id)
}
function nextChapter() {
  if (chapterIndex.value < chapters.value.length - 1)
    openChapter(chapters.value[chapterIndex.value + 1].id)
}

function onTapBody(e: MouseEvent) {
  // 点中间隐藏/显示顶部
}

onMounted(() => {
  loadBook()
  loadChapters()
})
</script>

<style scoped>
.reader {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fcfaf7;
  transition: background 0.3s;
}

.reader.night-mode {
  background: #1a1a1a;
  color: #ccc;
}

.reader-top {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 12px;
  border-bottom: 1px solid #eee;
}

.reader.night-mode .reader-top {
  border-color: #333;
}

.back {
  cursor: pointer;
}

.reader-title {
  font-size: 15px;
  font-weight: 500;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.reader-body {
  flex: 1;
  overflow: auto;
  padding: 24px 18px;
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.chapter-title {
  font-size: 20px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 24px;
}

.content {
  font-size: 17px;
  line-height: 1.9;
  letter-spacing: 0.02em;
}

.content :deep(p) {
  margin: 0 0 14px;
  text-indent: 2em;
}

.reading-loading {
  padding: 20px 0;
}

.reader-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-top: 1px solid #eee;
}

.reader.night-mode .reader-bottom {
  border-color: #333;
}

.page-info {
  color: #aaa;
  font-size: 13px;
}

.nav-btns {
  display: flex;
  align-items: center;
}
</style>