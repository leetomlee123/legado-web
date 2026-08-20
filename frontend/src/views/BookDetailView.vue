<template>
  <div class="book-detail-page">
    <!-- 顶部导航 -->
    <header class="detail-header">
      <button class="back-btn" id="detail-back-btn" aria-label="返回" @click="router.back()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <span class="detail-header-title">书籍详情</span>
    </header>

    <!-- 书籍主信息 -->
    <div class="detail-hero">
      <div class="detail-cover-wrap">
        <img
          v-if="book.cover"
          :src="book.cover"
          class="detail-cover"
          :alt="`《${book.name}》封面`"
        />
        <div
          v-else
          class="detail-cover detail-cover-placeholder"
          :style="placeholderStyle(book.name)"
        >
          <span>{{ book.name.slice(0, 2) }}</span>
        </div>
      </div>
      <div class="detail-meta">
        <h1 class="detail-title">{{ book.name }}</h1>
        <div class="detail-author">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
          {{ book.author || '作者不详' }}
        </div>
        <div v-if="book.intro" class="detail-intro">{{ book.intro }}</div>
        <div class="detail-tags">
          <span class="tag tag-web">网络书源</span>
          <span v-if="sourceName" class="tag">{{ sourceName }}</span>
        </div>
      </div>
    </div>

    <!-- 操作按钮区 -->
    <div class="detail-actions">
      <button
        id="detail-read-btn"
        class="btn-primary btn-read"
        :disabled="adding"
        @click="addAndRead"
      >
        <svg v-if="!adding" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
        </svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" class="spin" aria-hidden="true">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
        </svg>
        {{ adding ? '加入中...' : '加入书架并阅读' }}
      </button>
      <button class="btn-ghost" id="detail-back-shelf-btn" @click="router.push('/')">
        返回书架
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMsg" class="error-banner" role="alert">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      {{ errorMsg }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Book } from '@/types'

const route = useRoute()
const router = useRouter()

// 从 query 解析书籍数据
const book = ref<Book>({ id: 0, name: '' })
const adding = ref(false)
const errorMsg = ref('')

const sourceName = computed(() => {
  const b = book.value as any
  return b.sourceName || b.source_name || ''
})

onMounted(() => {
  try {
    const raw = route.query.data as string
    if (!raw) {
      errorMsg.value = '无效的书籍信息'
      return
    }
    book.value = JSON.parse(raw)
  } catch {
    errorMsg.value = '解析书籍信息失败'
  }
})

const GRADIENTS = [
  ['#c0692e', '#8b3a10'],
  ['#2e7d6e', '#1a4a42'],
  ['#b8863a', '#7a5520'],
  ['#5c4a8a', '#3a2e5c'],
  ['#2e6b8a', '#1a3d52'],
  ['#8a4a2e', '#5c2810'],
]

function placeholderStyle(name: string): Record<string, string> {
  const idx = (name || '').charCodeAt(0) % GRADIENTS.length
  const [from, to] = GRADIENTS[idx]
  return { background: `linear-gradient(145deg, ${from}, ${to})` }
}

async function addAndRead() {
  if (adding.value) return
  errorMsg.value = ''
  adding.value = true
  try {
    const res = await fetch('/api/books/from-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(book.value),
    })
    const data = await res.json()
    if (data.id) {
      router.push({ name: 'read', params: { book: String(data.id) } })
    } else {
      errorMsg.value = data.message || '加入书架失败，请检查书源是否有效'
    }
  } catch (e: any) {
    errorMsg.value = e.message || '网络错误，请重试'
  } finally {
    adding.value = false
  }
}
</script>

<style scoped>
.book-detail-page {
  min-height: 100dvh;
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
}

/* ─── 顶栏 ────────────────────────────────────────────────── */
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-subtle);
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.back-btn:hover {
  background: var(--color-accent-pale);
  color: var(--color-accent);
}

.detail-header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* ─── 书籍信息主区域 ──────────────────────────────────────── */
.detail-hero {
  display: flex;
  gap: 24px;
  padding: 28px 24px;
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.detail-cover-wrap {
  flex-shrink: 0;
}

.detail-cover {
  width: 110px;
  height: 147px; /* 3:4 */
  border-radius: var(--radius-md);
  object-fit: cover;
  box-shadow: var(--shadow-lg);
  display: block;
}

.detail-cover-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  color: rgba(255, 248, 220, 0.9);
  letter-spacing: 0.04em;
}

.detail-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
  line-height: 1.3;
  margin: 0;
  text-wrap: balance;
}

.detail-author {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.detail-intro {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-wrap: pretty;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  font-size: 11px;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--color-bg-subtle);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border-subtle);
  letter-spacing: 0.03em;
}

.tag-web {
  background: var(--color-accent-pale);
  color: var(--color-accent);
  border-color: rgba(184, 134, 58, 0.25);
}

/* ─── 操作按钮 ────────────────────────────────────────────── */
.detail-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 24px 28px;
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px 20px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-lg);
  font-family: var(--font-ui);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition:
    background var(--transition-base),
    transform var(--transition-fast),
    box-shadow var(--transition-base);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-light);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.btn-primary:active:not(:disabled) {
  transform: scale(0.98);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 12px 20px;
  background: transparent;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color var(--transition-base), color var(--transition-base), background var(--transition-base);
}

.btn-ghost:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-pale);
}

/* ─── 错误提示 ────────────────────────────────────────────── */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 24px;
  padding: 12px 16px;
  background: rgba(192, 105, 46, 0.07);
  border: 1px solid rgba(192, 105, 46, 0.25);
  border-radius: var(--radius-md);
  color: #c0692e;
  font-size: 13px;
  max-width: 712px;
  width: calc(100% - 48px);
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
}

/* ─── spin ──────────────────────────────────────────────────── */
.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
