<template>
  <div class="source-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h3 class="page-title">书源管理中心</h3>
        <p class="desc">支持多种形式书源导入（URL 订阅、文件上传、文本粘贴、精品源一键安装），支持分页浏览与批量管理。</p>
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
          style="width: 220px;"
          @input="currentPage = 1"
        />
        <el-button size="small" :type="isManageMode ? 'primary' : 'default'" @click="toggleManageMode">
          {{ isManageMode ? '退出批量' : '批量管理' }}
        </el-button>
        <el-button size="small" @click="toggleAllGlobal(true)">全部启用</el-button>
        <el-button size="small" @click="toggleAllGlobal(false)">全部禁用</el-button>
        <el-button size="small" @click="exportAllSources">导出全部 JSON</el-button>
      </div>
    </div>

    <!-- ── 批量操作悬浮 Dock（选中项目时亮显）────────────────── -->
    <transition name="fade">
      <div v-if="selectedRows.length > 0" class="batch-action-dock">
        <div class="batch-dock-left">
          <span class="badge-select-count">已跨页选中 {{ selectedRows.length }} 个书源</span>
        </div>
        <div class="batch-dock-actions">
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

        <el-table-column prop="name" label="书源名称" min-width="160">
          <template #default="{ row }">
            <span class="source-name-cell">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="url" label="书源地址" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="source-url-cell">{{ row.url || '内置 / 动态解析' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="规则状态" width="100" align="center">
          <template #default="{ row }">
            <span class="badge" :class="row.rule ? 'badge-configured' : 'badge-empty'">
              {{ row.rule ? '已配置' : '待完善' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="启用" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="isEnabled(row)"
              @change="(v: boolean) => toggleEnabled(row, v)"
            />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
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
            <div class="import-action-row">
              <el-button type="primary" class="btn-gold" :loading="importing" @click="doImportByUrl">
                开始解析并导入
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

    <!-- ── 手动编辑/新建书源弹窗 ────────────────────────────── -->
    <el-dialog v-model="editVisible" :title="form.id ? '编辑书源' : '新建书源'" width="580px">
      <el-form :model="form" label-width="80px">
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
} from '@/api'
import type { BookSource } from '@/types'

const tableRef = ref<InstanceType<typeof ElTable> | null>(null)
const sources = ref<BookSource[]>([])
const selectedRows = ref<BookSource[]>([])
const isManageMode = ref(false)

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

const filteredSources = computed(() => {
  const kw = searchFilter.value.trim().toLowerCase()
  if (!kw) return sources.value
  return sources.value.filter(
    (s) =>
      s.name.toLowerCase().includes(kw) ||
      (s.url && s.url.toLowerCase().includes(kw))
  )
})

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
      duration: 4500,
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
    const res = await importSourceUrl(url)
    showImportResult(res)
  } catch (e: any) {
    ElMessage.error(e.message || '网络导入失败')
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
    ElMessage.error(e.message || '文件上传解析失败')
  } finally {
    importing.value = false
  }
}

async function installPreset(p: { name: string; url: string }) {
  importingUrl.value = p.url
  try {
    const res = await importSourceUrl(p.url, p.name)
    showImportResult(res)
  } catch (e: any) {
    ElMessage.error(e.message || '预设源安装失败')
  } finally {
    importingUrl.value = ''
  }
}

// ── 批量操作 ─────────────────────────────────────────────

async function batchEnable(enabled: boolean) {
  const ids = selectedRows.value.map((r) => r.id!).filter(Boolean)
  if (!ids.length) return

  try {
    await batchToggleSources(ids, enabled)
    ElMessage.success(`已批量${enabled ? '启用' : '禁用'} ${ids.length} 个书源`)
    await load()
    clearSelection()
  } catch (e: any) {
    ElMessage.error(e.message || '批量操作失败')
  }
}

async function batchDelete() {
  const ids = selectedRows.value.map((r) => r.id!).filter(Boolean)
  if (!ids.length) return

  try {
    await ElMessageBox.confirm(
      `确定要批量删除选中的 ${ids.length} 个书源吗？删除后不可恢复。`,
      '批量删除书源',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )

    await batchDeleteSources(ids)
    ElMessage.success(`已成功删除 ${ids.length} 个书源`)
    clearSelection()
    await load()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '批量删除失败')
  }
}

function exportSources(list: BookSource[], filename = 'legado_sources.json') {
  if (!list.length) {
    ElMessage.warning('没有可导出的书源')
    return
  }

  const exportData = list.map((s) => {
    let ruleObj = null
    try {
      ruleObj = typeof s.rule === 'string' ? JSON.parse(s.rule) : s.rule
    } catch {
      ruleObj = s.rule
    }

    if (ruleObj && typeof ruleObj === 'object') {
      return {
        bookSourceName: s.name,
        bookSourceUrl: s.url,
        enabled: s.enabled !== 0,
        ...ruleObj,
      }
    }

    return {
      bookSourceName: s.name,
      bookSourceUrl: s.url,
      enabled: s.enabled !== 0,
      rule: s.rule,
    }
  })

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已成功导出 ${list.length} 个书源文件`)
}

function exportSelectedSources() {
  exportSources(selectedRows.value, `legado_selected_${selectedRows.value.length}_sources.json`)
}

function exportAllSources() {
  exportSources(sources.value, `legado_all_${sources.value.length}_sources.json`)
}

async function toggleAllGlobal(enabled: boolean) {
  const ids = sources.value.map((s) => s.id!).filter(Boolean)
  if (!ids.length) return
  try {
    await batchToggleSources(ids, enabled)
    ElMessage.success(enabled ? '已全部启用' : '已全部禁用')
    await load()
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function save() {
  if (!form.name.trim() || !form.url.trim()) {
    ElMessage.warning('请填写名称和地址')
    return
  }
  if (form.rule.trim()) {
    try {
      JSON.parse(form.rule)
    } catch {
      ElMessage.warning('规则不是合法 JSON')
      return
    }
  }
  saving.value = true
  try {
    await saveSource({
      id: form.id,
      name: form.name.trim(),
      url: form.url.trim(),
      rule: form.rule.trim(),
      enabled: form.enabled,
    })
    ElMessage.success(form.id ? '书源已更新' : '书源已添加')
    editVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(row: BookSource, enabled: boolean) {
  try {
    await saveSource({ ...row, rule: row.rule || '', enabled })
    row.enabled = enabled ? 1 : 0
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  }
}

async function remove(row: BookSource) {
  if (!row.id) return
  try {
    await ElMessageBox.confirm(`确定删除书源「${row.name}」？`, '删除书源', { type: 'warning' })
    await deleteSource(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

onMounted(() => {
  load()
  loadPresets()
})
</script>

<style scoped>
.source-page {
  padding: 32px 24px 80px;
  max-width: 980px;
  margin: 0 auto;
  position: relative;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.desc {
  color: var(--color-text-secondary);
  margin: 6px 0 0;
  font-size: 13.5px;
  line-height: 1.5;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.btn-gold {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: #fff;
}

.btn-gold:hover {
  background: var(--color-accent-light);
  border-color: var(--color-accent-light);
}

.btn-icon {
  margin-right: 6px;
}

/* ─── 子控制栏 ────────────────────────────────────────────── */
.source-sub-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.source-stat {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.text-success {
  color: #52c41a;
}

.source-filter-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

/* ─── 批量操作悬浮 Dock ──────────────────────────────────── */
.batch-action-dock {
  position: sticky;
  top: 16px;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 18px;
  background: var(--color-surface);
  border: 1.5px solid var(--color-accent);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  margin-bottom: 16px;
}

.badge-select-count {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-accent);
}

.batch-dock-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.dock-action-btn {
  font-size: 12.5px;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.btn-action-enable {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
  border-color: rgba(82, 196, 26, 0.3);
}

.btn-action-enable:hover {
  background: #52c41a;
  color: #fff;
}

.btn-action-disable {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-secondary);
  border-color: var(--color-border-subtle);
}

.btn-action-disable:hover {
  background: rgba(0, 0, 0, 0.1);
}

.btn-action-export {
  background: rgba(24, 144, 255, 0.1);
  color: #1890ff;
  border-color: rgba(24, 144, 255, 0.3);
}

.btn-action-export:hover {
  background: #1890ff;
  color: #fff;
}

.btn-action-delete {
  background: rgba(255, 77, 79, 0.1);
  color: #ff4d4f;
  border-color: rgba(255, 77, 79, 0.3);
}

.btn-action-delete:hover {
  background: #ff4d4f;
  color: #fff;
}

.btn-action-cancel {
  background: none;
  border: 1px solid var(--color-border-subtle);
  color: var(--color-text-muted);
}

.btn-action-cancel:hover {
  color: var(--color-text-primary);
}

/* ─── 表格卡片 ────────────────────────────────────────────── */
.table-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.source-name-cell {
  font-weight: 600;
  color: var(--color-text-primary);
}

.source-url-cell {
  font-size: 12.5px;
  color: var(--color-text-muted);
}

.badge {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 4px;
}

.badge-configured {
  background: rgba(82, 196, 26, 0.12);
  color: #52c41a;
}

.badge-empty {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-muted);
}

.pagination-footer {
  display: flex;
  justify-content: flex-end;
  padding: 14px 18px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border-subtle);
}

/* ─── 导入弹窗 ────────────────────────────────────────────── */
.tab-pane-content {
  padding: 12px 4px;
}

.tab-tip {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 10px;
}

.preset-links {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.preset-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.preset-tag {
  font-size: 11.5px;
  color: var(--color-accent);
  background: var(--color-accent-pale);
  padding: 2px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.preset-tag:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.import-action-row {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}

.upload-dropzone {
  width: 100%;
}

.upload-drag-inner {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

/* ─── 预设源列表 ──────────────────────────────────────────── */
.preset-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.preset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.preset-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 3px;
}

.preset-desc {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* ─── 空状态 ──────────────────────────────────────────────── */
.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 6px;
}

.empty-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 20px;
}
</style>
