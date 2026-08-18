<template>
  <div class="source-page">
    <div class="toolbar">
      <div>
        <h3>书源管理</h3>
        <p class="desc">添加、订阅或导入 JSON 书源，搜索页会使用已启用的书源。</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="openImportUrl">订阅导入</el-button>
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          accept=".json,application/json"
          :on-change="onJsonFile"
        >
          <el-button>导入 JSON</el-button>
        </el-upload>
        <el-button type="primary" :icon="Plus" @click="openEdit()">添加书源</el-button>
      </div>
    </div>

    <el-empty v-if="!loading && sources.length === 0" description="还没有书源，先添加或导入一个" />

    <el-table v-else :data="sources" v-loading="loading" class="table" stripe>
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="url" label="地址" min-width="240" show-overflow-tooltip />
      <el-table-column label="规则" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.rule ? 'success' : 'info'">
            {{ row.rule ? '已配置' : '空' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="isEnabled(row)"
            @change="(v: boolean) => toggleEnabled(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="editVisible" :title="form.id ? '编辑书源' : '添加书源'" width="560px">
      <el-form :model="form" label-width="72px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="书源名称" />
        </el-form-item>
        <el-form-item label="地址" required>
          <el-input v-model="form.url" placeholder="搜索页或站点 URL，可含 {search}" />
        </el-form-item>
        <el-form-item label="规则">
          <el-input
            v-model="form.rule"
            type="textarea"
            :rows="10"
            placeholder='JSON，例如 {"search":{"url":"...{search}","selector":".item","name":".name","bookUrl":"a@href"}}'
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="urlVisible" title="订阅导入" width="480px">
      <el-form label-width="72px">
        <el-form-item label="名称">
          <el-input v-model="subName" placeholder="可选，默认「订阅导入」" />
        </el-form-item>
        <el-form-item label="URL" required>
          <el-input v-model="subUrl" placeholder="书源订阅链接，返回 JSON 规则" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="urlVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doImportUrl">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { deleteSource, importSourceUrl, listSources, saveSource } from '@/api'
import type { BookSource } from '@/types'

const sources = ref<BookSource[]>([])
const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const editVisible = ref(false)
const urlVisible = ref(false)
const subUrl = ref('')
const subName = ref('')

const form = reactive({
  id: undefined as number | undefined,
  name: '',
  url: '',
  rule: '',
  enabled: true,
})

function isEnabled(s: BookSource) {
  return s.enabled === true || s.enabled === 1 || s.enabled === undefined
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

function openEdit(row?: BookSource) {
  form.id = row?.id
  form.name = row?.name || ''
  form.url = row?.url || ''
  form.rule = typeof row?.rule === 'string' ? row.rule : row?.rule ? JSON.stringify(row.rule, null, 2) : ''
  form.enabled = row ? isEnabled(row) : true
  editVisible.value = true
}

function openImportUrl() {
  subUrl.value = ''
  subName.value = ''
  urlVisible.value = true
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
    ElMessage.success(form.id ? '已更新' : '已添加')
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

async function doImportUrl() {
  const url = subUrl.value.trim()
  if (!url) {
    ElMessage.warning('请填写订阅 URL')
    return
  }
  importing.value = true
  try {
    await importSourceUrl(url, subName.value.trim() || undefined)
    ElMessage.success('订阅导入成功')
    urlVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    importing.value = false
  }
}

function normalizeSource(raw: any): BookSource | null {
  if (!raw || typeof raw !== 'object') return null
  const name = raw.name || raw.bookSourceName || raw.sourceName
  const url =
    raw.url ||
    raw.bookSourceUrl ||
    raw.searchUrl ||
    raw.search?.url ||
    ''
  let rule = raw.rule
  if (rule && typeof rule !== 'string') rule = JSON.stringify(rule)
  if (!rule && (raw.search || raw.detail || raw.toc || raw.content)) {
    rule = JSON.stringify({
      search: raw.search,
      detail: raw.detail,
      toc: raw.toc,
      content: raw.content,
    })
  }
  if (!name) return null
  return {
    name: String(name),
    url: String(url || ''),
    rule: rule ? String(rule) : '',
    enabled: raw.enabled === undefined ? true : Boolean(raw.enabled),
  }
}

async function onJsonFile(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  try {
    const text = await raw.text()
    const data = JSON.parse(text)
    const list = Array.isArray(data) ? data : [data]
    let ok = 0
    let fail = 0
    for (const item of list) {
      const src = normalizeSource(item)
      if (!src || !src.url) {
        fail += 1
        continue
      }
      try {
        await saveSource(src)
        ok += 1
      } catch {
        fail += 1
      }
    }
    ElMessage[fail ? 'warning' : 'success'](`导入完成：成功 ${ok} 个，失败 ${fail} 个`)
    await load()
  } catch (e: any) {
    ElMessage.error(e.message || 'JSON 解析失败')
  }
}

onMounted(load)
</script>

<style scoped>
.source-page {
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar h3 {
  margin: 0;
}

.desc {
  color: #999;
  margin: 4px 0 0;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.table {
  width: 100%;
  background: #fff;
  border-radius: 10px;
}
</style>
