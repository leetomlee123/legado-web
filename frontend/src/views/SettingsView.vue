<template>
  <section class="settings-page" aria-label="应用系统设置">
    <div class="page-header">
      <h2 class="page-title">系统与爬虫设置</h2>
      <p class="page-subtitle">配置网络代理、单源请求超时时间与多源并发搜索线程数</p>
    </div>

    <!-- ── 性能与并发参数配置 ──────────────────────────────── -->
    <div class="settings-card">
      <div class="card-header">
        <div class="card-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
        <div>
          <div class="card-title">多源并发与超时控制</div>
          <p class="card-desc">控制多书源并发检索的线程池规模以及单源网络请求超时阈值。</p>
        </div>
      </div>

      <!-- 超时配置 -->
      <div class="field-group">
        <div class="field-title-row">
          <label for="timeout-input" class="field-label">请求超时时间 (秒)</label>
          <span class="field-tag">当前: {{ timeout }} 秒</span>
        </div>
        <div class="field-control-row">
          <el-input-number
            id="timeout-input"
            v-model="timeout"
            :min="2"
            :max="120"
            :step="1"
            controls-position="right"
            style="width: 140px;"
          />
          <div class="preset-chips">
            <button class="chip-btn" :class="{ active: timeout === 5 }" @click="timeout = 5">5秒 (极速)</button>
            <button class="chip-btn" :class="{ active: timeout === 15 }" @click="timeout = 15">15秒 (推荐)</button>
            <button class="chip-btn" :class="{ active: timeout === 30 }" @click="timeout = 30">30秒 (深度)</button>
          </div>
        </div>
        <span class="field-hint">单个书源超过此时长未响应时自动跳过，防止个别慢源拖慢整体搜索速度。</span>
      </div>

      <!-- 线程数配置 -->
      <div class="field-group">
        <div class="field-title-row">
          <label for="workers-input" class="field-label">并发搜索线程数</label>
          <span class="field-tag">当前: {{ maxWorkers }} 线程</span>
        </div>
        <div class="field-control-row">
          <el-input-number
            id="workers-input"
            v-model="maxWorkers"
            :min="1"
            :max="64"
            :step="2"
            controls-position="right"
            style="width: 140px;"
          />
          <div class="preset-chips">
            <button class="chip-btn" :class="{ active: maxWorkers === 4 }" @click="maxWorkers = 4">4 (低负载)</button>
            <button class="chip-btn" :class="{ active: maxWorkers === 12 }" @click="maxWorkers = 12">12 (标准推荐)</button>
            <button class="chip-btn" :class="{ active: maxWorkers === 24 }" @click="maxWorkers = 24">24 (高速并发)</button>
            <button class="chip-btn" :class="{ active: maxWorkers === 36 }" @click="maxWorkers = 36">36 (极速)</button>
          </div>
        </div>
        <span class="field-hint">多源搜索时同时并发请求的书源数量。线程数越多并发检索越快。</span>
      </div>
    </div>

    <!-- ── 网络代理配置 ──────────────────────────────────── -->
    <div class="settings-card">
      <div class="card-header">
        <div class="card-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="2" y1="12" x2="22" y2="12"/>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
          </svg>
        </div>
        <div>
          <div class="card-title">网络代理</div>
          <p class="card-desc">用于搜索和抓取的外部 HTTP/SOCKS 代理，留空表示直连。</p>
        </div>
      </div>

      <div class="field-group">
        <label for="proxy-input" class="field-label">代理地址</label>
        <input
          id="proxy-input"
          v-model="proxy"
          type="url"
          class="field-input"
          placeholder="http://127.0.0.1:7890 或 socks5://127.0.0.1:10808"
          spellcheck="false"
          autocomplete="off"
        />
        <span class="field-hint">格式支持：<code>http://host:port</code> 或 <code>socks5://host:port</code></span>
      </div>
    </div>

    <!-- ── 底部保存栏 ──────────────────────────────────── -->
    <div class="settings-bottom-bar">
      <button class="btn-reset" @click="resetDefaults">
        恢复默认参数
      </button>

      <button
        id="settings-save-btn"
        class="btn-save"
        :disabled="saving"
        :class="{ 'is-saving': saving }"
        @click="save"
      >
        <svg v-if="!saving" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
        </svg>
        <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" class="spin" aria-hidden="true">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
        </svg>
        {{ saving ? '正在保存...' : '保存配置' }}
      </button>
    </div>

    <!-- 关于 -->
    <div class="settings-card about-card">
      <div class="card-header">
        <div class="card-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div>
          <div class="card-title">关于系统</div>
          <p class="card-desc">Legado Web — 开源阅读 3.0 浏览器端现代化重构版</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, saveSettings } from '@/api'

const proxy = ref('')
const timeout = ref(15)
const maxWorkers = ref(12)
const saving = ref(false)

async function load() {
  try {
    const s = await getSettings()
    proxy.value = s.proxy || ''
    timeout.value = typeof s.timeout === 'number' ? s.timeout : 15
    maxWorkers.value = typeof s.max_workers === 'number' ? s.max_workers : 12
  } catch (e: any) {
    ElMessage.error(e.message || '加载设置失败')
  }
}

function resetDefaults() {
  timeout.value = 15
  maxWorkers.value = 12
  ElMessage.info('已重置为系统推荐参数（需点击保存生效）')
}

async function save() {
  saving.value = true
  try {
    const res = await saveSettings({
      proxy: proxy.value.trim(),
      timeout: Number(timeout.value) || 15,
      max_workers: Number(maxWorkers.value) || 12,
    })
    timeout.value = res.timeout || timeout.value
    maxWorkers.value = res.max_workers || maxWorkers.value
    ElMessage.success('设置已成功保存并实时生效')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.settings-page {
  padding: 32px 28px 64px;
  max-width: 680px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  margin-bottom: 6px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 13.5px;
  color: var(--color-text-secondary);
  margin: 0;
}

.settings-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  border-left: 3.5px solid var(--color-accent);
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.card-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-accent-pale);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.card-desc {
  font-size: 12.5px;
  color: var(--color-text-muted);
  margin: 2px 0 0;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 0;
  border-top: 1px dashed var(--color-border-subtle);
}

.field-group:first-of-type {
  border-top: none;
  padding-top: 0;
}

.field-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.field-tag {
  font-size: 12px;
  color: var(--color-accent);
  background: var(--color-accent-pale);
  padding: 1px 8px;
  border-radius: 10px;
}

.field-control-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 4px 0;
}

.preset-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.chip-btn {
  font-size: 11.5px;
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.chip-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.chip-btn.active {
  background: var(--color-accent-pale);
  border-color: var(--color-accent);
  color: var(--color-accent);
  font-weight: 600;
}

.field-input {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-primary);
  font-size: 13.5px;
  outline: none;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: var(--color-accent);
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.settings-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}

.btn-reset {
  background: none;
  border: 1px solid var(--color-border-subtle);
  color: var(--color-text-muted);
  padding: 9px 16px;
  font-size: 13px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-reset:hover {
  color: var(--color-text-primary);
  border-color: var(--color-text-secondary);
}

.btn-save {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 24px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-save:hover {
  background: var(--color-accent-light);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.about-card {
  border-left-color: var(--color-border-subtle);
  opacity: 0.85;
}
</style>