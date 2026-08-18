<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <span class="logo-dot"></span>
        <span class="logo-text">阅 读</span>
      </div>
      <el-menu
        :default-active="activePath"
        router
        class="menu"
        background-color="transparent"
        text-color="#9ba3c7"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>书架</span>
        </el-menu-item>
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <span>搜索</span>
        </el-menu-item>
        <el-menu-item index="/import">
          <el-icon><Upload /></el-icon>
          <span>导入书籍</span>
        </el-menu-item>
        <el-menu-item index="/sources">
          <el-icon><Collection /></el-icon>
          <span>书源管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ route.meta?.title || '阅读' }}</div>
        <div class="header-actions">
          <el-tooltip content="搜索书籍">
            <el-icon class="action" @click="router.push('/search')"><Search /></el-icon>
          </el-tooltip>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { House, Search, Upload, Collection, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const activePath = computed(() => route.path)
</script>

<style scoped>
.layout {
  height: 100%;
}

/* 阅文品牌紫色 - 深色侧栏 */
.sidebar {
  background: linear-gradient(180deg, #7a2ff0 0%, #5b1fbf 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 2px 0 12px rgba(90, 30, 190, 0.25);
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 22px 0 16px;
}

.logo-dot {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.logo-text {
  color: #ffffff;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 2px;
}

.menu {
  width: 100%;
  border: none;
  flex: 1;
}

.menu :deep(.el-menu-item) {
  justify-content: center;
  height: 52px;
  margin: 4px 12px;
  border-radius: 10px;
}

.menu :deep(.el-menu-item.is-active) {
  background: rgba(255, 255, 255, 0.16);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border-bottom: 1px solid #f0f0f0;
  height: 60px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #2c2c2c;
}

.action {
  font-size: 20px;
  color: #7a2ff0;
  cursor: pointer;
  margin-left: 12px;
}

.action:hover {
  opacity: 0.7;
}

.main {
  background: #f7f7fa;
  padding: 0;
  overflow: auto;
}
</style>