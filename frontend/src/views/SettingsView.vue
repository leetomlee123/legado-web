<template>
  <div class="settings-page">
    <h3>设置</h3>

    <div class="card">
      <div class="card-title">网络代理</div>
      <p class="hint">
        用于搜索/抓取的外部 HTTP 代理。留空表示直连。格式：
        <code>http://127.0.0.1:7890</code>
      </p>
      <el-input
        v-model="proxy"
        placeholder="http://127.0.0.1:7890"
        clearable
        class="proxy-input"
      />
      <div class="card-actions">
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
      </div>
    </div>
  </div>
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
    ElMessage.success('已保存')
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
  padding: 24px;
  max-width: 640px;
  margin: 0 auto;
}

.card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c2c2c;
}

.hint {
  color: #999;
  font-size: 13px;
  margin: 6px 0 14px;
}

.hint code {
  background: #f2f2f5;
  padding: 1px 6px;
  border-radius: 4px;
}

.proxy-input {
  max-width: 100%;
}

.card-actions {
  margin-top: 16px;
}
</style>