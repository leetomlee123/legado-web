<template>
  <div class="logs-page" aria-label="系统日志控制台">
    <!-- 顶部控制条 -->
    <header class="logs-header">
      <div class="header-left">
        <div class="terminal-dots">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <h2 class="terminal-title">系统实时日志</h2>
        <span class="log-badge" :class="{ live: isLive }">
          <span class="pulse-dot" v-if="isLive"></span>
          {{ isLive ? '实时监听中' : '离线/已暂停' }}
        </span>
        <span class="log-counter">共 {{ filteredLogs.length }} 条记录</span>
      </div>

      <div class="header-right">
        <!-- 自动滚动开关 -->
        <button
          class="ctrl-btn"
          :class="{ active: autoScroll }"
          @click="autoScroll = !autoScroll"
          title="新日志产生时自动滚动到底部"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="7 13 12 18 17 13"/><polyline points="7 6 12 11 17 6"/>
          </svg>
          自动置底
        </button>

        <!-- 实时推流开关 -->
        <button
          class="ctrl-btn"
          :class="{ active: isLive }"
          @click="toggleLive"
          title="开启或关闭 SSE 实时推流"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          {{ isLive ? '暂停推流' : '开始监听' }}
        </button>

        <!-- 手动刷新 -->
        <button class="ctrl-btn" :disabled="loading" @click="fetchLogs" title="刷新全部历史日志">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ spin: loading }">
            <path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          刷新
        </button>

        <!-- 导出日志 -->
        <button class="ctrl-btn" @click="exportLogs" title="导出为文本文件">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导出
        </button>

        <!-- 清空日志 -->
        <button class="ctrl-btn danger" @click="handleClearLogs" title="清空服务端内存缓冲日志">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          清空
        </button>
      </div>
    </header>

    <!-- 筛选过滤栏 -->
    <div class="logs-filter-bar">
      <div class="level-tabs">
        <button
          v-for="lvl in levels"
          :key="lvl.value"
          class="level-tab"
          :class="[lvl.value.toLowerCase(), { active: currentLevel === lvl.value }]"
          @click="currentLevel = lvl.value"
        >
          {{ lvl.label }}
          <span class="count-tag" v-if="getLevelCount(lvl.value)">{{ getLevelCount(lvl.value) }}</span>
        </button>
      </div>

      <div class="search-box">
        <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          v-model="searchKeyword"
          type="text"
          class="search-input"
          placeholder="快速搜索日志内容、模块、书源..."
        />
        <button v-if="searchKeyword" class="clear-search-btn" @click="searchKeyword = ''">✕</button>
      </div>
    </div>

    <!-- 日志终端主体 -->
    <div ref="terminalBodyRef" class="terminal-body">
      <div v-if="filteredLogs.length === 0" class="empty-logs">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        <p>暂无符合条件的系统日志</p>
        <span>当发起搜索、阅读翻页、导入书源时，实时事件将在此处显示</span>
      </div>

      <div
        v-for="(log, idx) in filteredLogs"
        :key="log.id || idx"
        class="log-row"
        :class="log.level ? log.level.toLowerCase() : ''"
        @click="copyLogLine(log)"
      >
        <span class="col-num">{{ idx + 1 }}</span>
        <span class="col-time">{{ log.time }}</span>
        <span class="col-level" :class="log.level ? log.level.toLowerCase() : ''">
          {{ log.level }}
        </span>
        <span class="col-module">[{{ log.module || log.logger }}]</span>
        <span class="col-msg">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLogs, clearLogs, subscribeLogsStream, type LogItem } from '@/api'

const logs = ref<LogItem[]>([])
const loading = ref(false)
const isLive = ref(true)
const autoScroll = ref(true)
const searchKeyword = ref('')
const currentLevel = ref('ALL')
const terminalBodyRef = ref<HTMLElement | null>(null)

let unsubStream: (() => void) | null = null

const levels = [
  { label: '全部', value: 'ALL' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' },
]

const filteredLogs = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  const lvl = currentLevel.value
  return logs.value.filter((item) => {
    if (lvl !== 'ALL' && item.level !== lvl) {
      return false
    }
    if (kw) {
      const msg = (item.message || '').toLowerCase()
      const mod = (item.module || item.logger || '').toLowerCase()
      if (!msg.includes(kw) && !mod.includes(kw)) {
        return false
      }
    }
    return true
  })
})

function getLevelCount(val: string) {
  if (val === 'ALL') return logs.value.length
  return logs.value.filter((i) => i.level === val).length
}

async function fetchLogs() {
  loading.value = true
  try {
    const res = await getLogs({ limit: 1000 })
    // 后端返回倒序（最新在前），前端展示按时间升序（从旧到新从上往下刷）
    logs.value = (res.items || []).reverse()
    if (autoScroll.value) {
      scrollToBottom()
    }
  } catch (e: any) {
    ElMessage.error(e.message || '获取日志失败')
  } finally {
    loading.value = false
  }
}

function startStream() {
  if (unsubStream) {
    unsubStream()
    unsubStream = null
  }
  isLive.value = true
  unsubStream = subscribeLogsStream(
    (newLog) => {
      // 检查是否已存在同 id
      if (!logs.value.some((l) => l.id === newLog.id)) {
        logs.value.push(newLog)
        if (logs.value.length > 1000) {
          logs.value.shift()
        }
        if (autoScroll.value) {
          scrollToBottom()
        }
      }
    },
    (err) => {
      console.debug('[logs stream error]', err)
    }
  )
}

function stopStream() {
  if (unsubStream) {
    unsubStream()
    unsubStream = null
  }
  isLive.value = false
}

function toggleLive() {
  if (isLive.value) {
    stopStream()
    ElMessage.info('已暂停实时日志推流')
  } else {
    startStream()
    ElMessage.success('已恢复实时日志监听')
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (terminalBodyRef.value) {
      terminalBodyRef.value.scrollTop = terminalBodyRef.value.scrollHeight
    }
  })
}

async function handleClearLogs() {
  try {
    await ElMessageBox.confirm('确定要清空内存中的所有日志吗？', '提示', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await clearLogs()
    logs.value = []
    ElMessage.success('日志已清空')
  } catch {
    // user canceled
  }
}

function copyLogLine(log: LogItem) {
  const line = `[${log.time}] [${log.level}] [${log.module || log.logger}:${log.line}] - ${log.message}`
  navigator.clipboard.writeText(line).then(() => {
    ElMessage.success('日志行已复制到剪贴板')
  })
}

function exportLogs() {
  if (logs.value.length === 0) {
    ElMessage.warning('当前暂无日志可导出')
    return
  }
  const content = filteredLogs.value
    .map((l) => `[${l.time}] [${l.level}] [${l.module || l.logger}:${l.line}] - ${l.message}`)
    .join('\n')
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `legado-logs-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('日志文件已开始下载')
}

onMounted(async () => {
  await fetchLogs()
  startStream()
})

onUnmounted(() => {
  stopStream()
})
</script>

<style scoped>
.logs-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  padding: 16px 24px 20px;
  background: var(--color-bg);
  box-sizing: border-box;
  gap: 12px;
}

/* 顶部控制栏 */
.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: 12px 18px;
  box-shadow: var(--shadow-xs);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.terminal-dots {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot.red { background: #ff5f56; }
.dot.yellow { background: #ffbd2e; }
.dot.green { background: #27c93f; }

.terminal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.log-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.log-badge.live {
  background: rgba(39, 201, 63, 0.15);
  color: #27c93f;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #27c93f;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.7; }
  50% { transform: scale(1.4); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.7; }
}

.log-counter {
  font-size: 12px;
  color: var(--color-text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ctrl-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.ctrl-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.ctrl-btn.active {
  background: var(--color-accent-pale);
  border-color: var(--color-accent);
  color: var(--color-accent);
  font-weight: 600;
}

.ctrl-btn.danger:hover {
  border-color: #f56c6c;
  color: #f56c6c;
}

/* 过滤栏 */
.logs-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.level-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
}

.level-tab {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.level-tab:hover {
  border-color: var(--color-accent);
}

.level-tab.active {
  background: var(--color-text-primary);
  color: var(--color-bg);
  border-color: var(--color-text-primary);
}

.level-tab.info.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}
.level-tab.warning.active {
  background: #f59e0b;
  border-color: #f59e0b;
  color: #fff;
}
.level-tab.error.active {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}

.count-tag {
  font-size: 10px;
  padding: 0 5px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.2);
}

.search-box {
  position: relative;
  width: 320px;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 6px 28px 6px 30px;
  font-size: 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  outline: none;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: var(--color-accent);
}

.clear-search-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 11px;
}

/* 日志控制台主体 (Dark Terminal) */
.terminal-body {
  flex: 1;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, Menlo, Monaco, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #c9d1d9;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.4);
}

.empty-logs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #484f58;
  gap: 8px;
}

.empty-logs p {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.empty-logs span {
  font-size: 11px;
}

.log-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.1s ease;
  word-break: break-all;
  white-space: pre-wrap;
}

.log-row:hover {
  background: #161b22;
}

.col-num {
  color: #484f58;
  width: 36px;
  flex-shrink: 0;
  text-align: right;
  user-select: none;
}

.col-time {
  color: #8b949e;
  flex-shrink: 0;
}

.col-level {
  font-weight: 700;
  padding: 0 4px;
  border-radius: 3px;
  flex-shrink: 0;
  font-size: 11px;
}

.col-level.info {
  color: #58a6ff;
  background: rgba(56, 139, 253, 0.15);
}

.col-level.warning {
  color: #d29922;
  background: rgba(210, 153, 34, 0.15);
}

.col-level.error {
  color: #f85149;
  background: rgba(248, 81, 73, 0.18);
}

.col-module {
  color: #7ee787;
  flex-shrink: 0;
}

.col-msg {
  color: #e6edf3;
  flex: 1;
}

.log-row.error .col-msg {
  color: #ff7b72;
}

.log-row.warning .col-msg {
  color: #e3b341;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
