<template>
  <div class="source-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h3 class="page-title">书源管理中心</h3>
        <p class="desc">支持多种形式书源导入（URL 订阅、文件上传、文本粘贴、精品源一键安装），支持分页浏览、批量管理与实时测速。</p>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" class="btn-gold" @click="openImportDialog">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导入书源
        </el-button>
        <el-button @click="openEdit()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新建书源
        </el-button>
      </div>
    </div>

    <!-- ── 书源检索与批量控制条 ────────────────────────────── -->
    <div class="source-sub-bar" v-if="sources.length">
      <div class="source-stat">
        共 <strong>{{ sources.length }}</strong> 个书源，已启用 <strong class="text-success">{{ enabledCount }}</strong> 个
      </div>

      <div class="source-filter-tools">
        <el-input
          v-model="searchFilter"
          placeholder="快速查找书源名称或地址..."
          clearable
          size="small"
          style="width: 180px;"
          @input="currentPage = 1"
        />
        <el-button size="small" :loading="testingDelay" @click="batchTestAllDelay" title="探测所有书源的连接与响应延迟">
          ⚡ 批量测速
        </el-button>
        <el-button size="small" :type="isManageMode ? 'primary' : 'default'" @click="toggleManageMode">
          {{ isManageMode ? '退出批量' : '批量管理' }}
        </el-button>
        <el-button size="small" @click="toggleAllGlobal(true)">全部启用</el-button>
        <el-button size="small" @click="toggleAllGlobal(false)">全部禁用</el-button>
        <el-button size="small" @click="exportAllSources">导出全部 JSON</el-button>
      </div>
    </div>

    <!-- ── 健康度分类筛选与快捷清理栏 ────────────────────────── -->
    <div class="health-filter-bar" v-if="sources.length">
      <div class="health-tabs">
        <button
          class="h-tab"
          :class="{ active: selectedHealthTab === 'all' }"
          @click="selectedHealthTab = 'all'; currentPage = 1"
        >
          全部书源 ({{ sources.length }})
        </button>
        <button
          class="h-tab healthy"
          :class="{ active: selectedHealthTab === 'healthy' }"
          @click="selectedHealthTab = 'healthy'; currentPage = 1"
        >
          🟢 健康可用 ({{ healthyCount }})
        </button>
        <button
          class="h-tab slow"
          :class="{ active: selectedHealthTab === 'slow' }"
          @click="selectedHealthTab = 'slow'; currentPage = 1"
        >
          🟡 响应较慢 ({{ slowCount }})
        </button>
        <button
          class="h-tab dead"
          :class="{ active: selectedHealthTab === 'dead' }"
          @click="selectedHealthTab = 'dead'; currentPage = 1"
        >
          🔴 异常/失效 ({{ deadCount }})
        </button>
      </div>

      <div class="health-quick-actions" v-if="deadCount > 0">
        <el-button size="small" type="warning" plain @click="handleDisableAllDead">
          ⊘ 一键禁用全部失效源 ({{ deadCount }})
        </el-button>
        <el-button size="small" type="danger" plain @click="handleDeleteAllDead">
          🗑 一键清理全部失效源 ({{ deadCount }})
        </el-button>
      </div>
    </div>

    <!-- ── 批量操作悬浮 Dock（选中项目时亮显）────────────────── -->
    <transition name="fade">
      <div v-if="selectedRows.length > 0" class="batch-action-dock">
        <div class="batch-dock-left">
          <span class="badge-select-count">已跨页选中 {{ selectedRows.length }} 个书源</span>
        </div>
        <div class="batch-dock-actions">
          <button class="dock-action-btn btn-action-ping" :disabled="testingDelay" @click="batchTestSelectedDelay">
            ⚡ 批量测速 ({{ selectedRows.length }})
          </button>
          <button class="dock-action-btn btn-action-enable" @click="batchEnable(true)">
            ✓ 批量启用
          </button>
          <button class="dock-action-btn btn-action-disable" @click="batchEnable(false)">
            ⊘ 批量禁用
          </button>
          <button class="dock-action-btn btn-action-export" @click="exportSelectedSources">
            📥 导出选中 JSON
          </button>
          <button class="dock-action-btn btn-action-delete" @click="batchDelete">
            🗑 批量删除 ({{ selectedRows.length }})
          </button>
          <button class="dock-action-btn btn-action-cancel" @click="clearSelection">
            取消选择
          </button>
        </div>
      </div>
    </transition>

    <!-- 空状态 -->
    <div v-if="!loading && sources.length === 0" class="empty-box">
      <div class="empty-icon">📚</div>
      <p class="empty-title">当前暂无任何书源</p>
      <p class="empty-desc">支持输入网址订阅、上传 JSON 文件或一键导入精选预设源</p>
      <el-button type="primary" class="btn-gold" @click="openImportDialog">立即导入书源</el-button>
    </div>

    <!-- 书源列表表格卡片 -->
    <div v-else class="table-card">
      <el-table
        ref="tableRef"
        :data="pagedSources"
        row-key="id"
        v-loading="loading"
        class="table"
        stripe
        @selection-change="handleSelectionChange"
      >
        <!-- 批量选择列（跨页保持） -->
        <el-table-column
          v-if="isManageMode || selectedRows.length > 0"
          type="selection"
          :reserve-selection="true"
          width="50"
          align="center"
        />

        <el-table-column prop="name" label="书源名称" min-width="150">
          <template #default="{ row }">
            <span class="source-name-cell">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="url" label="书源地址" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="source-url-cell">{{ row.url || '内置 / 动态解析' }}</span>
          </template>
        </el-table-column>

        <!-- 响应延迟 / 测速状态 -->
        <el-table-column label="响应延迟" width="115" align="center">
          <template #default="{ row }">
            <span
              v-if="delayMap[row.id] !== undefined"
              class="delay-badge"
              :class="getDelayClass(delayMap[row.id])"
              :title="delayErrorMap[row.id] || (delayMap[row.id] >= 0 ? `${delayMap[row.id]}ms 正常响应` : '请求超时或不可达')"
            >
              ⚡ {{ delayMap[row.id] >= 0 ? delayMap[row.id] + 'ms' : '超时' }}
            </span>
            <span v-else class="delay-badge-empty">未测速</span>
          </template>
        </el-table-column>

        <el-table-column label="规则状态" width="95" align="center">
          <template #default="{ row }">
            <span class="badge" :class="row.rule ? 'badge-configured' : 'badge-empty'">
              {{ row.rule ? '已配置' : '待完善' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="启用" width="85" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="isEnabled(row)"
              @change="(v: boolean) => toggleEnabled(row, v)"
            />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="165" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="warning" :loading="testingSingleId === row.id" @click="testSingleDelay(row)">
              测速
            </el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- ── 分页导航栏 ────────────────────────────────────── -->
      <div class="pagination-footer" v-if="filteredSources.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[15, 25, 50, 100, 200]"
          :total="filteredSources.length"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </div>

    <!-- ── 多形式书源导入弹窗 ────────────────────────────────── -->
    <el-dialog
      v-model="importDialogVisible"
      title="多形式书源导入中心"
      width="640px"
      destroy-on-close
      class="import-modal"
    >
      <el-tabs v-model="activeImportTab" class="import-tabs">
        <!-- Tab 1: 网络 URL / 订阅源导入 -->
        <el-tab-pane label="🌐 网络订阅 URL" name="url">
          <div class="tab-pane-content">
            <p class="tab-tip">输入书源订阅 URL、JSON 规则地址，或书源合集网站（如 yckceo 等）：</p>
            <el-input
              v-model="importUrlInput"
              type="textarea"
              :rows="3"
              placeholder="例如：https://www.yckceo.com/yuedu/rss/index.html 或 raw JSON 规则链接"
            />
            <div class="preset-links">
              <span class="preset-label">快捷填入：</span>
              <span class="preset-tag" @click="importUrlInput = 'https://www.yckceo.com/yuedu/rss/index.html'">yckceo 精品合集</span>
              <span class="preset-tag" @click="importUrlInput = 'https://www.yckceo.com/yuedu/rss/json/id/864.json'">yckceo 全版本源</span>
              <span class="preset-tag" @click="importUrlInput = 'https://raw.githubusercontent.com/gedoor/legado/master/README.md'">源仓库官方订阅</span>
            </div>

            <!-- 超时与延迟参数配置 -->
            <div class="import-timeout-control">
              <span class="timeout-label">导入下载超时：</span>
              <el-input-number
                v-model="importTimeout"
                :min="5"
                :max="180"
                :step="5"
                size="small"
                style="width: 110px;"
              />
              <span class="timeout-unit">秒</span>
              <div class="timeout-chips">
                <span class="t-chip" :class="{ active: importTimeout === 15 }" @click="importTimeout = 15">15s</span>
                <span class="t-chip" :class="{ active: importTimeout === 30 }" @click="importTimeout = 30">30s (推荐)</span>
                <span class="t-chip" :class="{ active: importTimeout === 60 }" @click="importTimeout = 60">60s (弱网)</span>
                <span class="t-chip" :class="{ active: importTimeout === 120 }" @click="importTimeout = 120">120s (超大合集)</span>
              </div>
            </div>

            <div class="import-action-row">
              <el-button type="primary" class="btn-gold" :loading="importing" @click="doImportByUrl">
                {{ importing ? '正在下载解析 (请稍候)...' : '开始解析并导入' }}
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 本地文件上传导入 -->
        <el-tab-pane label="📁 本地文件上传" name="file">
          <div class="tab-pane-content">
            <el-upload
              drag
              :auto-upload="false"
              :show-file-list="false"
              accept=".json,.txt,application/json,text/plain"
              :on-change="onFileSelected"
              class="upload-dropzone"
            >
              <div class="upload-drag-inner">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" stroke-width="1.8">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <div class="el-upload__text">
                  将书源 <em>.json</em> 或 <em>.txt</em> 文件拖拽至此处，或 <em>点击上传</em>
                </div>
                <p class="el-upload__tip">支持 Legado 3.0 / 2.0 书源数组文件，一次性批量入库</p>
              </div>
            </el-upload>
          </div>
        </el-tab-pane>

        <!-- Tab 3: 直接粘贴 JSON 文本 -->
        <el-tab-pane label="📋 粘贴文本 / JSON" name="text">
          <div class="tab-pane-content">
            <p class="tab-tip">直接粘贴书源 JSON 数组或单个书源对象：</p>
            <el-input
              v-model="importTextInput"
              type="textarea"
              :rows="7"
              placeholder="[ { &quot;bookSourceName&quot;: &quot;...&quot;, &quot;bookSourceUrl&quot;: &quot;...&quot;, &quot;ruleSearch&quot;: { ... } } ]"
            />
            <div class="import-action-row">
              <el-button type="primary" class="btn-gold" :loading="importing" @click="doImportByText">
                解析并导入文本
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 4: 精品预设源一键订阅 -->
        <el-tab-pane label="🎁 精品预设源" name="presets">
          <div class="tab-pane-content">
            <div class="preset-list">
              <div v-for="p in presetSources" :key="p.url" class="preset-item">
                <div class="preset-info">
                  <div class="preset-name">{{ p.name }}</div>
                  <div class="preset-desc">{{ p.desc }}</div>
                </div>
                <el-button size="small" type="primary" class="btn-gold" :loading="importingUrl === p.url" @click="installPreset(p)">
                  一键安装
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- ── 单个书源编辑/新建弹窗 ────────────────────────────── -->
    <el-dialog
      v-model="editVisible"
      :title="form.id ? '编辑书源' : '新建书源'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="form" label-width="84px">
        <el-form-item label="书源名称" required>
          <el-input v-model="form.name" placeholder="例如：半山人小说" />
        </el-form-item>
        <el-form-item label="搜索地址" required>
          <el-input v-model="form.url" placeholder="例如：https://www.banshanren.com/search?keyword={search}" />
        </el-form-item>
        <el-form-item label="规则 JSON">
          <el-input
            v-model="form.rule"
            type="textarea"
            :rows="11"
            placeholder='Legado 3.0 或简版规则 JSON'
          />
        </el-form-item>
        <el-form-item label="立即启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" class="btn-gold" :loading="saving" @click="save">保存书源</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import type { UploadFile, ElTable } from 'element-plus'
import {
  deleteSource,
  batchDeleteSources,
  batchToggleSources,
  importSourceUrl,
  importSourceText,
  importSourceFile,
  getSourcePresets,
  listSources,
  saveSource,
  testSourceDelay,
  batchTestSourceDelay,
  getHealthStatus,
  disableDeadSources,
  deleteDeadSources,
  type HealthStatusRes,
} from '@/api'
import type { BookSource } from '@/types'

const tableRef = ref<any>(null)
const sources = ref<BookSource[]>([])
const selectedRows = ref<BookSource[]>([])
const isManageMode = ref(false)

// 延迟映射表 id -> delay (ms, -1 为失败/超时)
const delayMap = ref<Record<number, number>>({})
const delayErrorMap = ref<Record<number, string>>({})
const testingDelay = ref(false)
const testingSingleId = ref<number | null>(null)

// 健康度巡检状态
const healthStatus = ref<HealthStatusRes | null>(null)
const selectedHealthTab = ref<'all' | 'healthy' | 'slow' | 'dead'>('all')

// 分页状态
const currentPage = ref(1)
const pageSize = ref(20)

const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const importingUrl = ref('')
const searchFilter = ref('')

const editVisible = ref(false)
const importDialogVisible = ref(false)
const activeImportTab = ref('url')

const importUrlInput = ref('https://www.yckceo.com/yuedu/rss/index.html')
const importTimeout = ref(30)
const importTextInput = ref('')
const presetSources = ref<{ name: string; url: string; desc: string }[]>([])

const form = reactive({
  id: undefined as number | undefined,
  name: '',
  url: '',
  rule: '',
  enabled: true,
})

const enabledCount = computed(() => sources.value.filter(isEnabled).length)

const healthyCount = computed(() => {
  const map = healthStatus.value?.results || {}
  return sources.value.filter((s) => s.id && map[s.id]?.category === 'healthy').length
})

const slowCount = computed(() => {
  const map = healthStatus.value?.results || {}
  return sources.value.filter((s) => s.id && map[s.id]?.category === 'slow').length
})

const deadCount = computed(() => {
  const map = healthStatus.value?.results || {}
  return sources.value.filter((s) => s.id && map[s.id]?.category === 'dead').length
})

const filteredSources = computed(() => {
  const kw = searchFilter.value.trim().toLowerCase()
  const tab = selectedHealthTab.value
  const healthMap = healthStatus.value?.results || {}

  return sources.value.filter((s) => {
    // 关键词筛选
    if (kw) {
      const matchName = s.name.toLowerCase().includes(kw)
      const matchUrl = s.url && s.url.toLowerCase().includes(kw)
      if (!matchName && !matchUrl) return false
    }

    // 健康度标签筛选
    if (tab !== 'all') {
      const cat = s.id ? healthMap[s.id]?.category : undefined
      if (cat !== tab) return false
    }

    return true
  })
})

async function loadHealth() {
  try {
    const res = await getHealthStatus()
    healthStatus.value = res
    if (res?.results) {
      for (const [sidStr, r] of Object.entries(res.results)) {
        const sid = Number(sidStr)
        delayMap.value[sid] = r.delay
        if (r.error) {
          delayErrorMap.value[sid] = r.error
        }
      }
    }
  } catch {}
}

async function handleDisableAllDead() {
  try {
    await ElMessageBox.confirm('确定要一键禁用当前体检识别到的所有失效书源吗？', '提示', {
      type: 'warning',
      confirmButtonText: '确定禁用',
      cancelButtonText: '取消',
    })
    const res = await disableDeadSources()
    ElMessage.success(res.message || '已成功禁用失效书源')
    await load()
  } catch {}
}

async function handleDeleteAllDead() {
  try {
    await ElMessageBox.confirm('确定要一键永久删除当前体检识别到的所有失效书源吗？此操作不可撤销！', '高危操作确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    })
    const res = await deleteDeadSources()
    ElMessage.success(res.message || '已成功删除失效书源')
    await load()
  } catch {}
}

// 分页切片数据
const pagedSources = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredSources.value.slice(start, start + pageSize.value)
})

function isEnabled(s: BookSource) {
  return s.enabled === true || s.enabled === 1 || s.enabled === undefined
}

function handleSelectionChange(rows: BookSource[]) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

function toggleManageMode() {
  isManageMode.value = !isManageMode.value
  if (!isManageMode.value) {
    clearSelection()
  }
}

function getDelayClass(delay: number) {
  if (delay < 0) return 'delay-error'
  if (delay <= 400) return 'delay-fast'
  if (delay <= 1200) return 'delay-medium'
  return 'delay-slow'
}

async function testSingleDelay(row: BookSource) {
  if (!row.id) return
  testingSingleId.value = row.id
  try {
    const res = await testSourceDelay(row.id)
    delayMap.value[row.id] = res.delay
    if (res.error) {
      delayErrorMap.value[row.id] = res.error
    } else {
      delete delayErrorMap.value[row.id]
    }
    if (res.success) {
      ElMessage.success(`[${row.name}] 测速成功: ${res.delay}ms`)
    } else {
      ElMessage.warning(`[${row.name}] 测速失败: ${res.error || '超时'}`)
    }
  } catch (e: any) {
    delayMap.value[row.id] = -1
    delayErrorMap.value[row.id] = e.message
    ElMessage.error(`测速失败: ${e.message}`)
  } finally {
    testingSingleId.value = null
  }
}

async function batchTestAllDelay() {
  if (sources.value.length === 0) return
  testingDelay.value = true
  ElMessage.info(`正在并发测速 ${sources.value.length} 个书源...`)
  try {
    const results = await batchTestSourceDelay()
    for (const r of results) {
      delayMap.value[r.sourceId] = r.delay
      if (r.error) {
        delayErrorMap.value[r.sourceId] = r.error
      }
    }
    const successCount = results.filter((r) => r.success).length
    ElNotification({
      title: '批量测速完成',
      message: `已完成全部 ${results.length} 个书源探测，可用 ${successCount} 个`,
      type: 'success',
      duration: 3500,
    })
  } catch (e: any) {
    ElMessage.error(e.message || '批量测速失败')
  } finally {
    testingDelay.value = false
  }
}

async function batchTestSelectedDelay() {
  if (selectedRows.value.length === 0) return
  const ids = selectedRows.value.map((r) => r.id!).filter(Boolean)
  testingDelay.value = true
  ElMessage.info(`正在并发测速选中的 ${ids.length} 个书源...`)
  try {
    const results = await batchTestSourceDelay(ids)
    for (const r of results) {
      delayMap.value[r.sourceId] = r.delay
      if (r.error) {
        delayErrorMap.value[r.sourceId] = r.error
      }
    }
    const successCount = results.filter((r) => r.success).length
    ElMessage.success(`测速完成：${successCount}/${ids.length} 个书源响应正常`)
  } catch (e: any) {
    ElMessage.error(e.message || '测速失败')
  } finally {
    testingDelay.value = false
  }
}

async function load() {
  loading.value = true
  try {
    sources.value = await listSources()
  } catch (e: any) {
    ElMessage.error(e.message || '加载书源失败')
  } finally {
    loading.value = false
  }
}

async function loadPresets() {
  try {
    presetSources.value = await getSourcePresets()
  } catch {}
}

function openImportDialog() {
  importDialogVisible.value = true
}

function openEdit(row?: BookSource) {
  form.id = row?.id
  form.name = row?.name || ''
  form.url = row?.url || ''
  form.rule = typeof row?.rule === 'string' ? row.rule : row?.rule ? JSON.stringify(row.rule, null, 2) : ''
  form.enabled = row ? isEnabled(row) : true
  editVisible.value = true
}

function showImportResult(res: any) {
  const isOk = res?.success || (typeof res?.count === 'number' && res.count > 0) || res?.id
  if (isOk) {
    ElNotification({
      title: '书源导入成功',
      message: res.message || `成功导入 ${res.count || 1} 个书源（${res.name || '订阅导入'}）`,
      type: 'success',
      duration: 5000,
    })
    importDialogVisible.value = false
    load()
  } else {
    ElMessage.error(res?.message || '导入失败，请检查规则格式或网络连接')
  }
}

async function doImportByUrl() {
  const url = importUrlInput.value.trim()
  if (!url) {
    ElMessage.warning('请输入订阅 URL')
    return
  }
  importing.value = true
  try {
    const res = await importSourceUrl(url, undefined, importTimeout.value)
    showImportResult(res)
  } catch (e: any) {
    ElMessage.error(e.message || '网络导入超时或失败，请检查网址或代理设置')
  } finally {
    importing.value = false
  }
}

async function doImportByText() {
  const text = importTextInput.value.trim()
  if (!text) {
    ElMessage.warning('请粘贴书源 JSON 或文本')
    return
  }
  importing.value = true
  try {
    const res = await importSourceText(text)
    showImportResult(res)
    importTextInput.value = ''
  } catch (e: any) {
    ElMessage.error(e.message || '文本解析导入失败')
  } finally {
    importing.value = false
  }
}

async function onFileSelected(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  importing.value = true
  try {
    const res = await importSourceFile(raw)
    showImportResult(res)
  } catch (e: any) {
    ElMessage.error(e.message || '文件导入解析失败')
  } finally {
    importing.value = false
  }
}

async function installPreset(p: { name: string; url: string }) {
  importingUrl.value = p.url
  try {
    const res = await importSourceUrl(p.url, p.name, 45)
    showImportResult(res)
  } catch (e: any) {
    ElMessage.error(e.message || '预设源安装失败')
  } finally {
    importingUrl.value = ''
  }
}

async function toggleEnabled(row: BookSource, val: boolean) {
  row.enabled = val ? 1 : 0
  try {
    await saveSource({
      ...row,
      enabled: row.enabled,
    })
    ElMessage.success(`已${val ? '启用' : '禁用'}书源：${row.name}`)
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
    row.enabled = val ? 0 : 1
  }
}

async function batchEnable(val: boolean) {
  const ids = selectedRows.value.map((r) => r.id!).filter(Boolean)
  if (!ids.length) return
  try {
    await batchToggleSources(ids, val)
    ElMessage.success(`已成功批量${val ? '启用' : '禁用'} ${ids.length} 个书源`)
    load()
    clearSelection()
  } catch (e: any) {
    ElMessage.error(e.message || '批量操作失败')
  }
}

async function toggleAllGlobal(val: boolean) {
  const ids = sources.value.map((r) => r.id!).filter(Boolean)
  if (!ids.length) return
  try {
    await batchToggleSources(ids, val)
    ElMessage.success(`已全部${val ? '启用' : '禁用'}所有 ${ids.length} 个书源`)
    load()
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function batchDelete() {
  const ids = selectedRows.value.map((r) => r.id!).filter(Boolean)
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(
      `确定要永久删除选中的 ${ids.length} 个书源吗？此操作不可撤销。`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await batchDeleteSources(ids)
    ElMessage.success(`已成功删除 ${ids.length} 个书源`)
    clearSelection()
    load()
  } catch {}
}

async function remove(row: BookSource) {
  if (!row.id) return
  try {
    await ElMessageBox.confirm(`确定要删除书源「${row.name}」吗？`, '删除书源', {
      type: 'warning',
    })
    await deleteSource(row.id)
    ElMessage.success('书源已删除')
    load()
  } catch {}
}

function exportSelectedSources() {
  if (!selectedRows.value.length) return
  exportJsonData(selectedRows.value, `legado-sources-selected-${selectedRows.value.length}.json`)
}

function exportAllSources() {
  if (!sources.value.length) {
    ElMessage.warning('暂无书源可导出')
    return
  }
  exportJsonData(sources.value, `legado-sources-all-${sources.value.length}.json`)
}

function exportJsonData(data: BookSource[], filename: string) {
  const payload = data.map((s) => {
    let parsedRule = s.rule
    if (typeof s.rule === 'string') {
      try {
        parsedRule = JSON.parse(s.rule)
      } catch {}
    }
    if (parsedRule && typeof parsedRule === 'object') {
      return parsedRule
    }
    return {
      bookSourceName: s.name,
      bookSourceUrl: s.url,
      enabled: isEnabled(s),
    }
  })

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`成功导出 ${data.length} 个书源为 JSON 文件`)
}

async function save() {
  if (!form.name.trim() || !form.url.trim()) {
    ElMessage.warning('请填写书源名称和地址')
    return
  }
  saving.value = true
  try {
    await saveSource({
      id: form.id,
      name: form.name.trim(),
      url: form.url.trim(),
      rule: form.rule.trim(),
      enabled: form.enabled ? 1 : 0,
    })
    ElMessage.success('书源已保存')
    editVisible.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
  loadPresets()
  loadHealth()
})
</script>

<style scoped>
.source-page {
  padding: 24px 28px 60px;
  max-width: 1200px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ── 健康度过滤栏 ── */
.health-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.health-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.h-tab {
  font-size: 12px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.h-tab:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.h-tab.active {
  background: var(--color-text-primary);
  color: var(--color-bg);
  border-color: var(--color-text-primary);
}

.h-tab.healthy.active {
  background: #27c93f;
  border-color: #27c93f;
  color: #fff;
}

.h-tab.slow.active {
  background: #f59e0b;
  border-color: #f59e0b;
  color: #fff;
}

.h-tab.dead.active {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}

.health-quick-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-icon {
  margin-right: 5px;
}

/* 子控制条 */
.source-sub-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: 10px 16px;
  box-shadow: var(--shadow-xs);
}

.source-stat {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.source-filter-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 延迟 Badge */
.delay-badge {
  display: inline-flex;
  align-items: center;
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
}
.delay-badge.delay-fast {
  background: rgba(39, 201, 63, 0.15);
  color: #27c93f;
}
.delay-badge.delay-medium {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}
.delay-badge.delay-slow {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}
.delay-badge.delay-error {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}
.delay-badge-empty {
  font-size: 11.5px;
  color: var(--color-text-muted);
}

/* 悬浮批量 Dock */
.batch-action-dock {
  position: sticky;
  top: 72px;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-text-primary);
  color: var(--color-bg);
  border-radius: var(--radius-lg);
  padding: 10px 18px;
  box-shadow: var(--shadow-lg);
  margin-bottom: 4px;
}

.batch-dock-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dock-action-btn {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.dock-action-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.dock-action-btn.btn-action-ping {
  background: #f59e0b;
  border-color: #f59e0b;
  color: #fff;
}
.dock-action-btn.btn-action-ping:hover {
  background: #d97706;
}

.dock-action-btn.btn-action-enable {
  background: #27c93f;
  border-color: #27c93f;
  color: #fff;
}
.dock-action-btn.btn-action-enable:hover {
  background: #20a032;
}

.dock-action-btn.btn-action-delete {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}
.dock-action-btn.btn-action-delete:hover {
  background: #dc2626;
}

/* 表格卡片 */
.table-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
}

.source-name-cell {
  font-weight: 600;
  color: var(--color-text-primary);
}

.source-url-cell {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-family: monospace;
}

.badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 600;
}
.badge-configured {
  background: var(--color-accent-pale);
  color: var(--color-accent);
}
.badge-empty {
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
}

.pagination-footer {
  display: flex;
  justify-content: flex-end;
  padding: 14px 18px;
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
}

/* 导入弹窗样式 */
.tab-pane-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 6px 0;
}

.tab-tip {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

.preset-links {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.preset-label {
  color: var(--color-text-muted);
}

.preset-tag {
  color: var(--color-accent);
  background: var(--color-accent-pale);
  padding: 2px 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-tag:hover {
  transform: translateY(-1px);
  filter: brightness(1.1);
}

/* 导入超时控制 */
.import-timeout-control {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  font-size: 12.5px;
}

.timeout-label {
  color: var(--color-text-secondary);
  font-weight: 500;
}

.timeout-unit {
  color: var(--color-text-muted);
}

.timeout-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 6px;
}

.t-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.t-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.t-chip.active {
  background: var(--color-accent-pale);
  border-color: var(--color-accent);
  color: var(--color-accent);
  font-weight: 600;
}

.import-action-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.upload-dropzone {
  width: 100%;
}

.upload-drag-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  gap: 8px;
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 380px;
  overflow-y: auto;
}

.preset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  gap: 12px;
}

.preset-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.preset-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: var(--color-surface);
  border: 1px dashed var(--color-border-subtle);
  border-radius: var(--radius-lg);
  gap: 10px;
}

.empty-icon {
  font-size: 40px;
}

.empty-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0 0 10px;
}

/* ─── 移动端响应式适配 (<= 768px) ────────────────────────── */
@media (max-width: 768px) {
  .source-page {
    padding: 16px 12px 30px;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .toolbar-actions {
    width: 100%;
    display: flex;
    gap: 8px;
  }

  .toolbar-actions .el-button {
    flex: 1;
    justify-content: center;
  }

  .source-sub-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .source-filter-tools {
    overflow-x: auto;
    white-space: nowrap;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
    width: 100%;
  }

  .health-filter-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .health-tabs {
    overflow-x: auto;
    white-space: nowrap;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
    width: 100%;
  }

  .batch-action-dock {
    left: 12px;
    right: 12px;
    transform: none;
    flex-direction: column;
    gap: 8px;
    padding: 10px 14px;
  }

  .batch-dock-actions {
    flex-wrap: wrap;
    justify-content: center;
    width: 100%;
  }

  :deep(.el-dialog) {
    width: 92vw !important;
    max-width: 500px;
    margin: 20px auto !important;
  }
}
</style>
