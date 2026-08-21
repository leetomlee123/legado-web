<template>
  <section class="import-page" aria-label="导入书籍">
    <div class="page-header">
      <h2 class="page-title">导入书籍</h2>
      <p class="page-desc">支持 TXT、EPUB、PDF 格式，拖拽或点击选择文件</p>
    </div>

    <!-- 上传区 -->
    <el-upload
      drag
      multiple
      :auto-upload="false"
      :on-change="onFileChange"
      :show-file-list="false"
      accept=".txt,.epub,.pdf"
      class="upload-area"
      aria-label="文件上传区，点击或拖拽文件到此处"
    >
      <div class="upload-inner">
        <div class="upload-icon" aria-hidden="true">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <div class="upload-text">
          拖拽文件到这里，或<span class="upload-highlight">点击选择</span>
        </div>
        <div class="upload-formats">
          <span class="format-tag">TXT</span>
          <span class="format-tag">EPUB</span>
          <span class="format-tag">PDF</span>
        </div>
      </div>
    </el-upload>

    <!-- 上传进度 -->
    <div v-if="uploading" class="progress-section" role="status" aria-live="polite">
      <div class="progress-label">
        <span>正在导入...</span>
        <span>{{ progress }}%</span>
      </div>
      <div class="progress-track" aria-hidden="true">
        <div class="progress-bar" :style="{ width: progress + '%' }"></div>
      </div>
    </div>

    <!-- 结果反馈 -->
    <div
      v-if="result"
      class="result-card"
      :class="result.failed ? 'result-warning' : 'result-success'"
      role="status"
      aria-live="polite"
    >
      <div class="result-icon" aria-hidden="true">
        <!-- 成功图标 -->
        <svg v-if="!result.failed" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <!-- 警告图标 -->
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <div class="result-content">
        <div class="result-title">
          导入完成：成功 {{ result.success }} 本，失败 {{ result.failed }} 本
        </div>
        <div v-if="result.failed && result.message" class="result-detail">{{ result.message }}</div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <router-link to="/" class="btn-back" id="import-back-btn" aria-label="返回书架">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回书架
      </router-link>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
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
  result.value = null
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
/* ─── 布局 ────────────────────────────────────────────────── */
.import-page {
  padding: 32px 28px;
  max-width: 640px;
  margin: 0 auto;
}

/* ─── 页头 ────────────────────────────────────────────────── */
.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
  margin: 0 0 6px;
}

.page-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}

/* ─── 上传区 ──────────────────────────────────────────────── */
.upload-area {
  border-radius: var(--radius-lg) !important;
}

/* Element Plus 上传区域覆盖 */
.upload-area :deep(.el-upload-dragger) {
  background: var(--color-surface);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 0;
  height: auto;
  transition: border-color var(--transition-base), background var(--transition-base), box-shadow var(--transition-base);
}

.upload-area :deep(.el-upload-dragger:hover),
.upload-area :deep(.el-upload-dragger.is-dragover) {
  border-color: var(--color-accent);
  background: var(--color-accent-pale);
  box-shadow: 0 0 0 4px var(--color-accent-glow);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 32px;
}

.upload-icon {
  color: var(--color-accent);
  opacity: 0.7;
  transition: opacity var(--transition-base), transform var(--transition-slow);
}

.upload-area :deep(.el-upload-dragger:hover) .upload-icon,
.upload-area :deep(.el-upload-dragger.is-dragover) .upload-icon {
  opacity: 1;
  transform: translateY(-4px);
}

.upload-text {
  font-size: 15px;
  color: var(--color-text-secondary);
  text-align: center;
}

.upload-highlight {
  color: var(--color-accent);
  font-weight: 500;
  cursor: pointer;
}

.upload-formats {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.format-tag {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
  background: var(--color-bg-subtle);
  border: 1px solid var(--color-border-subtle);
  padding: 3px 8px;
  border-radius: 4px;
}

/* ─── 进度条 ──────────────────────────────────────────────── */
.progress-section {
  margin-top: 20px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.progress-track {
  height: 4px;
  background: var(--color-bg-subtle);
  border-radius: 99px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--color-accent), var(--color-accent-light));
  border-radius: 99px;
  transition: width var(--transition-slow);
}

/* ─── 结果卡片 ────────────────────────────────────────────── */
.result-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-top: 20px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid;
}

.result-success {
  background: rgba(46, 125, 110, 0.06);
  border-color: rgba(46, 125, 110, 0.25);
  color: #2e7d6e;
}

.result-warning {
  background: rgba(192, 105, 46, 0.06);
  border-color: rgba(192, 105, 46, 0.25);
  color: #c0692e;
}

.result-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.result-title {
  font-size: 14px;
  font-weight: 500;
  color: inherit;
}

.result-detail {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
  white-space: pre-wrap;
}

/* ─── 操作区 ──────────────────────────────────────────────── */
.actions {
  margin-top: 24px;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: transparent;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: border-color var(--transition-base), color var(--transition-base), background var(--transition-base);
}

.btn-back:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-pale);
}

/* ─── 移动端响应式适配 (<= 768px) ────────────────────────── */
@media (max-width: 768px) {
  .import-page {
    padding: 20px 14px 40px;
  }

  .upload-area :deep(.el-upload-dragger) {
    padding: 30px 16px;
  }

  .actions {
    display: flex;
  }

  .btn-back {
    width: 100%;
    justify-content: center;
  }
}
</style>