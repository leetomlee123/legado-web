<template>
  <section class="settings-page" aria-label="应用设置">
    <div class="page-header">
      <h2 class="page-title">设置</h2>
    </div>

    <!-- 网络代理 -->
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
          <p class="card-desc">
            用于搜索和抓取的外部 HTTP 代理，留空表示直连。
          </p>
        </div>
      </div>

      <div class="field-group">
        <label for="proxy-input" class="field-label">代理地址</label>
        <input
          id="proxy-input"
          v-model="proxy"
          type="url"
          class="field-input"
          placeholder="http://127.0.0.1:7890"
          spellcheck="false"
          autocomplete="off"
        />
        <span class="field-hint">格式：<code>http://host:port</code></span>
      </div>

      <div class="card-actions">
        <button
          id="settings-save-btn"
          class="btn-save"
          :disabled="saving"
          :class="{ 'is-saving': saving }"
          @click="save"
        >
          <svg v-if="!saving" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" class="spin" aria-hidden="true">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
          {{ saving ? '保存中' : '保存设置' }}
        </button>
      </div>
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
          <div class="card-title">关于</div>
          <p class="card-desc">Legado Web — 阅读3.0 浏览器端移植版</p>
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
const saving = ref(false)

async function load() {
  try {
    const s = await getSettings()
    proxy.value = s.proxy || ''
  } catch (e: any) {
    ElMessage.error(e.message || '加载设置失败')
  }
}

async function save() {
  saving.value = true
  try {
    await saveSettings({ proxy: proxy.value.trim() })
    ElMessage.success('设置已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
/* ─── 布局 ────────────────────────────────────────────────── */
.settings-page {
  padding: 32px 28px;
  max-width: 640px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ─── 页头 ────────────────────────────────────────────────── */
.page-header {
  margin-bottom: 8px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
  margin: 0;
}

/* ─── 卡片 ────────────────────────────────────────────────── */
.settings-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  /* 金色左描边 */
  border-left: 3px solid var(--color-accent);
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--transition-base);
}

.settings-card:hover {
  box-shadow: var(--shadow-sm);
}

.about-card {
  border-left-color: var(--color-border-subtle);
  opacity: 0.8;
}

/* ─── 卡片头部 ────────────────────────────────────────────── */
.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.card-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: var(--color-accent-pale);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.about-card .card-icon {
  background: var(--color-bg-subtle);
  color: var(--color-text-secondary);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 3px;
}

.card-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
}

/* ─── 字段 ────────────────────────────────────────────────── */
.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  letter-spacing: 0.01em;
}

.field-input {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-primary);
  font-family: var(--font-ui);
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.field-input::placeholder {
  color: var(--color-text-muted);
  font-family: 'SFMono-Regular', Consolas, monospace;
}

.field-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-pale);
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.field-hint code {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 11px;
  background: var(--color-bg-subtle);
  border: 1px solid var(--color-border-subtle);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--color-text-secondary);
}

/* ─── 操作区 ──────────────────────────────────────────────── */
.card-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-save {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 20px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition:
    background var(--transition-base),
    transform var(--transition-fast),
    box-shadow var(--transition-base);
}

.btn-save:hover:not(:disabled) {
  background: var(--color-accent-light);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.btn-save:active:not(:disabled) {
  transform: translateY(0) scale(0.97);
}

.btn-save:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>