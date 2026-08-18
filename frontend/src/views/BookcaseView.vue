<template>
  <div class="bookcase">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索书架中的书籍..."
        clearable
        class="search-input"
        @input="onSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <router-link to="/import">
        <el-button type="primary" :icon="Plus">导入书籍</el-button>
      </router-link>
    </div>

    <el-empty
      v-if="books.length === 0 && !loading"
      description="书架还是空的，点击右上角导入书籍"
    />

    <div v-else class="book-grid">
      <div
        v-for="book in books"
        :key="book.id"
        class="book-card"
        @click="openBook(book)"
      >
        <div class="cover-wrap">
          <img v-if="book.cover" :src="coverUrl(book.id)" class="cover" />
          <div v-else class="cover cover-placeholder">
            <span>{{ book.name.slice(0, 4) }}</span>
          </div>
          <span v-if="book.hasUpdate" class="badge">更新</span>
        </div>
        <div class="info">
          <div class="name" :title="book.name">{{ book.name }}</div>
          <div class="author">{{ book.author || '未知作者' }}</div>
        </div>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="4" animated class="skeleton" />

    <div v-if="total > books.length" class="load-more">
      <el-button text @click="loadMore">加载更多</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { listBooks, coverUrl } from '@/api'
import type { Book } from '@/types'

const router = useRouter()
const keyword = ref('')
const books = ref<Book[]>([])
const total = ref(0)
const page = ref(0)
const loading = ref(false)
let timer: number | undefined

async function fetchBooks(reset = false) {
  if (reset) {
    page.value = 0
    books.value = []
  }
  loading.value = true
  try {
    const res = await listBooks(keyword.value, undefined, page.value, 20)
    total.value = res.total
    books.value = reset ? res.items : [...books.value, ...res.items]
  } catch (e: any) {
    ElMessage.error(e.message || '加载书架失败')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  window.clearTimeout(timer)
  timer = window.setTimeout(() => fetchBooks(true), 300)
}

function loadMore() {
  page.value += 1
  fetchBooks()
}

function openBook(book: Book) {
  router.push({ name: 'read', params: { book: String(book.id) } })
}

onMounted(() => fetchBooks(true))
</script>

<style scoped>
.bookcase {
  padding: 20px 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.search-input {
  max-width: 380px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 20px 16px;
}

.book-card {
  cursor: pointer;
  transition: transform 0.15s;
}

.book-card:hover {
  transform: translateY(-3px);
}

.cover-wrap {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  aspect-ratio: 3 / 4;
}

.cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #7a2ff0, #5b1fbf);
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
}

.badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: #f56c6c;
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
}

.info {
  margin-top: 8px;
}

.name {
  font-size: 14px;
  color: #2c2c2c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.author {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.skeleton {
  margin-top: 12px;
}

.load-more {
  text-align: center;
  margin-top: 20px;
}
</style>