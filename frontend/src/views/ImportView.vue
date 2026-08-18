<template>
  <div class="import-page">
    <h3>导入书籍</h3>
    <p class="desc">支持 TXT / EPUB / PDF 格式文件，直接拖入或点击选择。</p>

    <el-upload
      drag
      multiple
      :auto-upload="false"
      :on-change="onFileChange"
      :show-file-list="false"
      accept=".txt,.epub,.pdf"
      class="upload-area"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        拖拽文件到这里，或 <em>点击选择</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">单次可导入多个文件</div>
      </template>
    </el-upload>

    <div v-if="uploading" class="progress">
      <el-progress :percentage="progress" :stroke-width="14" />
    </div>

    <el-alert
      v-if="result"
      :type="result.failed ? 'warning' : 'success'"
      :closable="false"
      class="result"
      :title="`导入完成：成功 ${result.success} 本，失败 ${result.failed} 本`"
    />

    <div v-if="result?.failed">
      <div class="error-msg">{{ result.message }}</div>
    </div>

    <div class="actions">
      <router-link to="/">
        <el-button type="primary">返回书架</el-button>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { importTxt, importEpub, importPdf } from '@/api'
import type { UploadFile } from 'element-plus'
import type { ImportResult } from '@/types'

const uploading = ref(false)
const progress = ref(0)
const result = ref<ImportResult | null>(null)

async function onFileChange(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  uploading.value = true
  progress.value = 10
  try {
    const ext = raw.name.split('.').pop()?.toLowerCase()
    let res: ImportResult
    if (ext === 'txt') res = await importTxt(raw)
    else if (ext === 'epub') res = await importEpub(raw)
    else if (ext === 'pdf') res = await importPdf(raw)
    else {
      ElMessage.warning(`不支持的文件类型：${ext}`)
      return
    }
    progress.value = 100
    result.value = res
  } catch (e: any) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.import-page {
  padding: 24px;
  max-width: 640px;
  margin: 0 auto;
}

.desc {
  color: #999;
  margin: 4px 0 20px;
}

.upload-area {
  border-radius: 12px;
}

.progress {
  margin-top: 20px;
}

.result {
  margin-top: 20px;
}

.error-msg {
  color: #f56c6c;
  font-size: 13px;
  margin-top: 8px;
  white-space: pre-wrap;
}

.actions {
  margin-top: 24px;
}
</style>