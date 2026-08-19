<template>
  <div class="search-page">
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="输入书名 / 作者，回车搜索"
        clearable
        size="large"
        @keyup.enter="doSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button
        type="primary"
        size="large"
        :loading="searching"
        @click="doSearch"
      >
        搜索
      </el-button>
    </div>

    <div v-if="keyword && !searching" class="hint">
      按下回车或点击搜索，将在已启用的书源中查找「{{ keyword }}」
    </div>

    <template v-if="results.length">
      <div
        v-for="group in results"
        :key="group.sourceId"
        class="source-group"
      >
        <div class="source-label">
          {{ group.sourceName }}
          <span class="count">{{ group.books.length }} 本</span>
        </div>
        <div class="result-grid">
          <div
            v-for="b in group.books"
            :key="b.id"
            class="result-card"
            @click="open(b)"
          >
            <img v-if="b.cover" :src="b.cover" class="thumb" />
            <div v-else class="thumb thumb-placeholder">{{ b.name.slice(0, 3) }}</div>
            <div class="r-info">
              <div class="r-name">{{ b.name }}</div>
              <div class="r-author">{{ b.author || '未知' }}</div>
              <div class="r-intro" v-if="b.intro">{{ b.intro }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <el-empty v-else-if="searched && !searching" description="没有找到相关书籍" />

    <el-skeleton v-if="searching" :rows="5" animated />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { searchAll, listSources } from '@/api'
import type { SourceSearchRes, Book } from '@/types'

const router = useRouter()
const keyword = ref('')
const results = ref<SourceSearchRes[]>([])
const searching = ref(false)
const searched = ref(false)

async function doSearch() {
  const kw = keyword.value.trim()
  if (!kw) return
  searching.value = true
  searched.value = true
  results.value = []
  try {
    // 获取所有启用书源
    const sources = await listSources()
    const enabled = sources.filter((s) => s.enabled).map((s) => s.id)
    const res = await searchAll(kw, enabled)
    results.value = Array.isArray(res) ? res : res?.data || []
  } catch (e: any) {
    ElMessage.error(e.message || '搜索失败')
  } finally {
    searching.value = false
  }
}

async function open(book: Book) {
  if (book.id) {
    router.push({ name: 'read', params: { book: String(book.id) } })
    return
  }
  // 网络书源结果需先加入书架，再跳转到阅读页
  try {
    const res = await fetch('/api/books/from-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(book),
    })
    const data = await res.json()
    if (data.id) {
      router.push({ name: 'read', params: { book: String(data.id) } })
    } else {
      ElMessage.error(data.message || '加入书架失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加入书架失败')
  }
}
</script>

<style scoped>
.search-page {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
}

.hint {
  color: #aaa;
  font-size: 13px;
  margin-bottom: 16px;
}

.source-group {
  margin-top: 24px;
}

.source-label {
  font-size: 14px;
  font-weight: 600;
  color: #7a2ff0;
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid #7a2ff0;
}

.count {
  font-weight: 400;
  color: #bbb;
  font-size: 12px;
  margin-left: 6px;
}

.result-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  display: flex;
  gap: 14px;
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.15s;
}

.result-card:hover {
  box-shadow: 0 4px 16px rgba(122, 47, 240, 0.18);
}

.thumb {
  width: 56px;
  height: 76px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #7a2ff0, #5b1fbf);
  color: #fff;
  font-size: 13px;
}

.r-name {
  font-size: 15px;
  font-weight: 600;
  color: #2c2c2c;
}

.r-author {
  font-size: 12px;
  color: #999;
  margin: 4px 0;
}

.r-intro {
  font-size: 12px;
  color: #bbbbbb;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>