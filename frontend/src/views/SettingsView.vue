<template>
  <section class="settings-page" aria-label="应用系统设置">
    <div class="page-header">
      <h2 class="page-title">系统与爬虫设置</h2>
      <p class="page-subtitle">配置网络代理、并发参数、搜索超时及书源健康度自动巡检</p>
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

    <!-- ── 书源健康度定时巡检 ──────────────────────────────── -->
    <div class="settings-card">
      <div class="card-header">
        <div class="card-icon" style="background: rgba(39, 201, 63, 0.15); color: #27c93f;" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <div style="flex: 1;">
          <div class="card-title-row">
            <div class="card-title">书源健康度定时巡检</div>
            <el-tag size="small" :type="healthStatus?.scanning ? 'warning' : (healthCheckEnabled ? 'success' : 'info')">
              {{ healthStatus?.scanning ? '正在巡检中...' : (healthCheckEnabled ? '定时巡检已启用' : '已暂停') }}
            </el-tag>
          </div>
          <p class="card-desc">后台自动静默探测书源连通性、响应速度并标记失效源，保障全网搜索始终流畅。</p>
        </div>
      </div>

      <!-- 巡检开关 -->
      <div class="field-group-inline">
        <div>
          <div class="field-label">启用后台自动巡检</div>
          <span class="field-hint">按设定周期在后台异步探测所有书源的健康状态。</span>
        </div>
        <el-switch v-model="healthCheckEnabled" />
      </div>

      <!-- 巡检周期 -->
      <div class="field-group" v-if="healthCheckEnabled">
        <div class="field-title-row">
          <label class="field-label">巡检执行周期</label>
          <span class="field-tag">每 {{ healthCheckInterval }} 小时一次</span>
        </div>
        <div class="field-control-row">
          <div class="preset-chips">
            <button class="chip-btn" :class="{ active: healthCheckInterval === 1 }" @click="healthCheckInterval = 1">每 1 小时</button>
            <button class="chip-btn" :class="{ active: healthCheckInterval === 6 }" @click="healthCheckInterval = 6">每 6 小时 (推荐)</button>
            <button class="chip-btn" :class="{ active: healthCheckInterval === 12 }" @click="healthCheckInterval = 12">每 12 小时</button>
            <button class="chip-btn" :class="{ active: healthCheckInterval === 24 }" @click="healthCheckInterval = 24">每 24 小时 (每天一次)</button>
          </div>
        </div>
      </div>

      <!-- 自动隔离失效源 -->
      <div class="field-group-inline">
        <div>
          <div class="field-label">自动隔离失效书源</div>
          <span class="field-hint">巡检发现超时、关站或报错的书源时，自动将其置为「禁用」状态。</span>
        </div>
        <el-switch v-model="autoDisableDead" />
      </div>

      <!-- 巡检状态概览卡片 -->
      <div class="health-summary-box">
        <div class="summary-header">
          <span class="summary-title">最近体检结果</span>
          <span class="summary-time">{{ healthStatus?.lastScanTime ? `完成于 ${healthStatus.lastScanTime}` : '暂未执行过全量体检' }}</span>
        </div>
        <div class="health-stats-row">
          <div class="stat-item total">
            <span class="stat-val">{{ healthStatus?.total || 0 }}</span>
            <span class="stat-lbl">书源总数</span>
          </div>
          <div class="stat-item healthy">
            <span class="stat-val">{{ healthStatus?.healthy || 0 }}</span>
            <span class="stat-lbl">🟢 健康 (<1.2s)</span>
          </div>
          <div class="stat-item slow">
            <span class="stat-val">{{ healthStatus?.slow || 0 }}</span>
            <span class="stat-lbl">🟡 迟缓 (>1.2s)</span>
          </div>
          <div class="stat-item dead">
            <span class="stat-val">{{ healthStatus?.dead || 0 }}</span>
            <span class="stat-lbl">🔴 失效/异常</span>
          </div>
        </div>
        <div class="health-actions-row">
          <el-button
            type="primary"
            class="btn-gold"
            size="small"
            :loading="healthStatus?.scanning || runningCheck"
            @click="handleRunHealthCheck"
          >
            ⚡ 立即执行全面体检
          </el-button>
          <el-button
            v-if="healthStatus?.dead"
            type="danger"
            size="small"
            plain
            @click="handleDisableDead"
          >
            一键禁用 {{ healthStatus.dead }} 个失效书源
          </el-button>
        </div>
      </div>
    </div>

    <!-- ── 网络代理配置 ──────────────────────────────────── -->
    <div class="settings-card">
      <div class="card-header">
        <div class="card-icon" :style="proxyEnabled ? 'background: rgba(39, 201, 63, 0.15); color: #27c93f;' : ''" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="2" y1="12" x2="22" y2="12"/>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
          </svg>
        </div>
        <div style="flex: 1;">
          <div class="card-title-row">
            <div class="card-title">网络代理</div>
            <el-tag size="small" :type="proxyEnabled ? 'success' : 'info'">
              {{ proxyEnabled ? '🟢 代理通道已开启' : '⚪ 直连模式 (代理已关闭)' }}
            </el-tag>
          </div>
          <p class="card-desc">用于全网搜索、正文抓取及订阅更新的外部 HTTP/SOCKS 代理通道。</p>
        </div>
      </div>

      <!-- 代理总开关 -->
      <div class="field-group-inline">
        <div>
          <div class="field-label">启用网络代理</div>
          <span class="field-hint">开启后所有书源网络请求将经由此代理通道发出；关闭则完全直连。</span>
        </div>
        <el-switch v-model="proxyEnabled" />
      </div>

      <div class="field-group">
        <div class="field-title-row">
          <label for="proxy-input" class="field-label">代理服务器地址</label>
          <span v-if="proxyEnabled && proxy.trim()" class="field-tag">代理生效中</span>
          <span v-else-if="!proxyEnabled && proxy.trim()" class="field-tag" style="opacity: 0.7;">已配置 (未激活)</span>
        </div>
        <div class="proxy-input-group">
          <input
            id="proxy-input"
            v-model="proxy"
            type="url"
            class="field-input"
            placeholder="http://127.0.0.1:7890 或 socks5://127.0.0.1:10808"
            spellcheck="false"
            autocomplete="off"
            @input="proxyTestResult = null"
          />
          <el-button
            type="primary"
            class="btn-gold"
            :loading="testingProxy"
            :disabled="!proxy.trim()"
            @click="handleTestProxy"
          >
            ⚡ 测试代理连接
          </el-button>
        </div>
        <span class="field-hint">格式支持：<code>http://host:port</code>、<code>socks5://host:port</code> 或 <code>http://user:pass@host:port</code></span>

        <!-- 代理测试结果卡片 -->
        <div v-if="proxyTestResult" class="proxy-test-card" :class="proxyTestResult.ok ? 'success' : 'failed'">
          <div class="test-header">
            <span class="test-icon">{{ proxyTestResult.ok ? '✓' : '✕' }}</span>
            <span class="test-title">{{ proxyTestResult.ok ? '代理连通正常' : '代理测试失败' }}</span>
            <span v-if="proxyTestResult.delay >= 0" class="test-delay">{{ proxyTestResult.delay }}ms</span>
          </div>
          <div class="test-body">
            <div v-if="proxyTestResult.ok" class="test-detail">
              <span>出口公网 IP: <strong>{{ proxyTestResult.ip || '已连接' }}</strong></span>
              <span v-if="proxyTestResult.status">状态: HTTP {{ proxyTestResult.status }}</span>
            </div>
            <div v-else class="test-error">
              {{ proxyTestResult.error || '无法连接到指定的代理服务器，请检查地址、端口或鉴权密码' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 域名自动转换 (m. -> www.) ───────────────────────── -->
    <div class="settings-card">
      <div class="card-header">
        <div class="card-icon" :style="mToWww ? 'background: rgba(39, 201, 63, 0.15); color: #27c93f;' : ''" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
          </svg>
        </div>
        <div style="flex: 1;">
          <div class="card-title-row">
            <div class="card-title">域名自动转换 (m. → www.)</div>
            <el-tag size="small" :type="mToWww ? 'success' : 'info'">
              {{ mToWww ? '🟢 已启用 (自动将 m. 转换为 www.)' : '⚪ 已关闭 (保持原始书源域名)' }}
            </el-tag>
          </div>
          <p class="card-desc">自动将小说网站的移动端网址（如 https://m.xxx.com/）转换为桌面端网址（如 https://www.xxx.com/）。</p>
        </div>
      </div>

      <div class="field-group-inline">
        <div>
          <div class="field-label">启用移动端转桌面端 (m. → www.)</div>
          <span class="field-hint">开启后，全网搜索、目录抓取及正文解析时将优先请求 <code>www.</code> 桌面端网址；若桌面端不存在或访问失败（如 404、域名不可达），系统将<strong>自动无缝回退</strong>至原始移动端地址，保障阅读稳定可用。</span>
        </div>
        <el-switch v-model="mToWww" />
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
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  getSettings,
  saveSettings,
  getHealthStatus,
  runHealthCheck,
  disableDeadSources,
  testProxy,
  type HealthStatusRes,
  type ProxyTestResult,
} from '@/api'

const proxy = ref('')
const proxyEnabled = ref(false)
const mToWww = ref(false)
const timeout = ref(15)
const maxWorkers = ref(12)
const healthCheckEnabled = ref(true)
const healthCheckInterval = ref(6)
const autoDisableDead = ref(false)

const saving = ref(false)
const testingProxy = ref(false)
const proxyTestResult = ref<ProxyTestResult | null>(null)
const runningCheck = ref(false)
const healthStatus = ref<HealthStatusRes | null>(null)
let pollTimer: number | null = null

async function loadSettings() {
  try {
    const s = await getSettings()
    proxy.value = s.proxy || ''
    proxyEnabled.value = s.proxy_enabled ?? (s.proxyEnabled ?? Boolean(s.proxy))
    mToWww.value = s.m_to_www ?? (s.mToWww ?? (s.convertMToWww ?? false))
    timeout.value = s.timeout ?? 15
    maxWorkers.value = s.max_workers ?? (s.maxWorkers ?? 12)
    healthCheckEnabled.value = s.health_check_enabled ?? (s.healthCheckEnabled ?? true)
    healthCheckInterval.value = s.health_check_interval ?? (s.healthCheckInterval ?? 6)
    autoDisableDead.value = s.auto_disable_dead ?? (s.autoDisableDead ?? false)
  } catch (e: any) {
    ElMessage.error(e.message || '加载配置失败')
  }
}

async function loadHealthStatus() {
  try {
    healthStatus.value = await getHealthStatus()
  } catch (e) {
    // ignore
  }
}

async function handleRunHealthCheck() {
  runningCheck.value = true
  try {
    const res = await runHealthCheck()
    ElMessage.success(res.message || '已在后台启动全面体检')
    await loadHealthStatus()
  } catch (e: any) {
    ElMessage.error(e.message || '启动体检失败')
  } finally {
    runningCheck.value = false
  }
}

async function handleDisableDead() {
  try {
    const res = await disableDeadSources()
    ElMessage.success(res.message || `已禁用 ${res.disabledCount} 个失效书源`)
    await loadHealthStatus()
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function handleTestProxy() {
  const p = proxy.value.trim()
  if (!p) {
    ElMessage.warning('请输入要测试的代理地址')
    return
  }
  testingProxy.value = true
  proxyTestResult.value = null
  try {
    const res = await testProxy(p)
    proxyTestResult.value = res
    if (res.ok) {
      ElMessage.success(`代理连通测试成功！响应延迟 ${res.delay}ms，出口 IP: ${res.ip || '已连接'}`)
    } else {
      ElMessage.error(`代理连通测试失败: ${res.error || '无法连通'}`)
    }
  } catch (e: any) {
    proxyTestResult.value = { ok: false, delay: -1, error: e.message }
    ElMessage.error(`测试失败: ${e.message}`)
  } finally {
    testingProxy.value = false
  }
}

function resetDefaults() {
  proxyEnabled.value = false
  mToWww.value = false
  timeout.value = 15
  maxWorkers.value = 12
  healthCheckEnabled.value = true
  healthCheckInterval.value = 6
  autoDisableDead.value = false
  ElMessage.info('已重置为系统默认推荐参数，请点击「保存配置」生效')
}

async function save() {
  saving.value = true
  try {
    await saveSettings({
      proxy: proxy.value.trim(),
      proxy_enabled: proxyEnabled.value,
      proxyEnabled: proxyEnabled.value,
      m_to_www: mToWww.value,
      mToWww: mToWww.value,
      timeout: timeout.value,
      max_workers: maxWorkers.value,
      health_check_enabled: healthCheckEnabled.value,
      health_check_interval: healthCheckInterval.value,
      auto_disable_dead: autoDisableDead.value,
    })
    ElNotification({
      title: '设置保存成功',
      message: '系统参数已全量更新并实时生效',
      type: 'success',
      duration: 3000,
    })
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
  loadHealthStatus()
  pollTimer = window.setInterval(loadHealthStatus, 8000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.settings-page {
  padding: 28px 36px 60px;
  max-width: 780px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 代理输入组与测试卡片 */
.proxy-input-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.proxy-test-card {
  margin-top: 6px;
  border-radius: var(--radius-md);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12.5px;
  transition: all 0.2s ease;
}

.proxy-test-card.success {
  background: rgba(39, 201, 63, 0.1);
  border: 1px solid rgba(39, 201, 63, 0.3);
}

.proxy-test-card.failed {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.test-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.proxy-test-card.success .test-icon,
.proxy-test-card.success .test-title {
  color: #27c93f;
  font-weight: 700;
}

.proxy-test-card.failed .test-icon,
.proxy-test-card.failed .test-title {
  color: #ef4444;
  font-weight: 700;
}

.test-delay {
  font-size: 11.5px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.08);
}

.proxy-test-card.success .test-delay {
  color: #27c93f;
  background: rgba(39, 201, 63, 0.2);
}

.test-detail {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-text-secondary);
}

.test-detail strong {
  color: var(--color-text-primary);
}

.test-error {
  color: #ef4444;
  word-break: break-all;
  line-height: 1.4;
}

.page-header {
  margin-bottom: 4px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 6px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

.settings-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: var(--shadow-xs);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding-bottom: 4px;
}

.card-icon {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background: var(--color-accent-pale);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 3px;
}

.card-desc {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-group-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-top: 1px dashed var(--color-border-subtle);
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
  font-weight: 500;
  color: var(--color-accent);
  background: var(--color-accent-pale);
  padding: 2px 8px;
  border-radius: 10px;
}

.field-control-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.preset-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.chip-btn {
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: var(--radius-md);
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
  padding: 9px 14px;
  font-size: 13.5px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-primary);
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
  transition: border-color 0.15s ease;
}

.field-input:focus {
  border-color: var(--color-accent);
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.field-hint code {
  background: var(--color-bg);
  padding: 2px 5px;
  border-radius: 4px;
  font-family: monospace;
}

/* 巡检概览卡片 */
.health-summary-box {
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.summary-title {
  font-weight: 600;
  color: var(--color-text-primary);
}

.summary-time {
  color: var(--color-text-muted);
}

.health-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 4px;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
}

.stat-val {
  font-size: 16px;
  font-weight: 700;
}

.stat-lbl {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.stat-item.healthy .stat-val { color: #27c93f; }
.stat-item.slow .stat-val { color: #f59e0b; }
.stat-item.dead .stat-val { color: #ef4444; }

.health-actions-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

/* 底部操作条 */
.settings-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}

.btn-reset {
  padding: 8px 16px;
  font-size: 13px;
  color: var(--color-text-muted);
  background: none;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-reset:hover {
  border-color: var(--color-text-secondary);
  color: var(--color-text-primary);
}

.btn-save {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 600;
  border-radius: var(--radius-md);
  border: none;
  background: var(--color-accent);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(184, 134, 11, 0.28);
  transition: all 0.15s ease;
}

.btn-save:hover:not(:disabled) {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.btn-save:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.about-card {
  opacity: 0.85;
}

/* ─── 移动端响应式适配 (<= 768px) ────────────────────────── */
@media (max-width: 768px) {
  .settings-page {
    padding: 16px 12px 30px;
    gap: 14px;
  }

  .settings-card {
    padding: 16px 14px;
    gap: 14px;
  }

  .proxy-input-group {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .proxy-input-group .el-button {
    width: 100%;
  }

  .field-group-inline {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .field-group-inline .el-switch {
    align-self: flex-end;
  }

  .health-actions-row {
    flex-direction: column;
    gap: 8px;
  }

  .health-actions-row .el-button {
    width: 100%;
    margin-left: 0 !important;
  }

  .settings-bottom-bar {
    flex-direction: column;
    gap: 10px;
  }

  .btn-reset, .btn-save {
    width: 100%;
    justify-content: center;
  }
}
</style>