<template>
  <div class="layout">
    <!-- 桌面端侧边栏 -->
    <aside class="sidebar" role="navigation" aria-label="主导航">
      <!-- Logo -->
      <div class="logo">
        <div class="logo-icon" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="3" width="10" height="22" rx="2" fill="#c8983a" opacity="0.9"/>
            <rect x="15" y="5" width="10" height="20" rx="2" fill="#fdf5e0" opacity="0.6"/>
            <rect x="5" y="8" width="6" height="1.5" rx="0.75" fill="#1c1208" opacity="0.4"/>
            <rect x="5" y="11" width="6" height="1.5" rx="0.75" fill="#1c1208" opacity="0.3"/>
            <rect x="5" y="14" width="4" height="1.5" rx="0.75" fill="#1c1208" opacity="0.2"/>
          </svg>
        </div>
        <span class="logo-text">阅&thinsp;读</span>
      </div>

      <!-- 导航菜单 -->
      <nav class="menu-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ 'is-active': activePath === item.path || (item.path !== '/' && activePath.startsWith(item.path)) }"
          :aria-current="activePath === item.path ? 'page' : undefined"
        >
          <span class="nav-icon" aria-hidden="true" v-html="item.icon"></span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 底部装饰 -->
      <div class="sidebar-footer">
        <div class="footer-text">Legado Web</div>
      </div>
    </aside>

    <div class="main-container">
      <header class="app-header" role="banner">
        <h1 class="header-title">{{ route.meta?.title || '阅读' }}</h1>
        <div class="header-actions">
          <button
            id="header-search-btn"
            class="action-btn"
            aria-label="打开搜索"
            @click="router.push('/search')"
            title="搜索书籍"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
        </div>
      </header>
      <main class="app-main">
        <router-view />
      </main>

      <!-- 移动端专属底部导航栏 -->
      <nav class="mobile-bottom-nav" role="navigation" aria-label="移动端主导航">
        <router-link
          v-for="item in navItems"
          :key="'mobile-' + item.path"
          :to="item.path"
          class="mobile-nav-item"
          :class="{ 'is-active': activePath === item.path || (item.path !== '/' && activePath.startsWith(item.path)) }"
        >
          <span class="mobile-nav-icon" aria-hidden="true" v-html="item.icon"></span>
          <span class="mobile-nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const activePath = computed(() => route.path)

const navItems = [
  {
    path: '/',
    label: '书架',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M2 4h4v16H2z"/><path d="M10 4h4v16h-4z"/><path d="M18 4h4v16h-4z"/>
    </svg>`,
  },
  {
    path: '/search',
    label: '搜索',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>`,
  },
  {
    path: '/import',
    label: '导入书籍',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
    </svg>`,
  },
  {
    path: '/sources',
    label: '书源管理',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>`,
  },
  {
    path: '/logs',
    label: '系统日志',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
    </svg>`,
  },
  {
    path: '/settings',
    label: '设置',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>`,
  },
]
</script>

<style scoped>
/* ─── 整体布局 ──────────────────────────────────────────── */
.layout {
  display: flex;
  width: 100vw;
  height: 100%;
  overflow: hidden;
  position: relative;
}

/* ─── 侧边栏 ──────────────────────────────────────────────── */
.sidebar {
  width: 220px;
  min-width: 220px;
  max-width: 220px;
  background: var(--color-sidebar);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  position: relative;
  overflow: hidden;
  z-index: var(--z-sidebar);
  flex-shrink: 0;
}

/* ─── 主内容区外层容器 ────────────────────────────────────── */
.main-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

/* 侧边栏噪声纹理 */
.sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.04;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: 200px 200px;
}

/* 侧边栏右侧金色细线 */
.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 1px;
  height: 100%;
  background: linear-gradient(180deg, transparent, rgba(184, 134, 58, 0.3) 30%, rgba(184, 134, 58, 0.3) 70%, transparent);
}

/* ─── Logo ────────────────────────────────────────────────── */
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 26px 20px 20px;
  position: relative;
}

.logo-icon {
  flex-shrink: 0;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.logo-text {
  color: var(--color-text-inverse);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 3px;
  opacity: 0.92;
}

/* ─── 导航菜单 ────────────────────────────────────────────── */
.menu-nav {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: var(--radius-md);
  color: rgba(253, 245, 224, 0.55);
  text-decoration: none;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.02em;
  transition:
    background var(--transition-base),
    color var(--transition-base),
    padding-left var(--transition-base);
  position: relative;
}

.nav-item:hover {
  background: var(--color-sidebar-item);
  color: rgba(253, 245, 224, 0.85);
  padding-left: 18px;
}

.nav-item.is-active {
  background: rgba(184, 134, 58, 0.14);
  color: var(--color-accent-light);
  font-weight: 500;
  padding-left: 18px;
}

/* 左侧金色竖线 active 指示 */
.nav-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 25%;
  height: 50%;
  width: 3px;
  background: var(--color-accent);
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  opacity: 0.85;
}

.nav-item.is-active .nav-icon {
  opacity: 1;
}

/* ─── 底部装饰 ────────────────────────────────────────────── */
.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 245, 220, 0.05);
}

.footer-text {
  font-size: 11px;
  color: rgba(253, 245, 224, 0.2);
  letter-spacing: 0.05em;
  font-weight: 300;
}

/* ─── Header ──────────────────────────────────────────────── */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-subtle);
  height: 60px;
  min-height: 60px;
  padding: 0 24px;
  z-index: var(--z-header);
  flex-shrink: 0;
  width: 100%;
  box-sizing: border-box;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: 0.01em;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.action-btn:hover {
  background: var(--color-accent-pale);
  color: var(--color-accent);
}

.action-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* ─── 主内容区 ────────────────────────────────────────────── */
.app-main {
  background: var(--color-bg);
  padding: 0;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  width: 100%;
  box-sizing: border-box;
  -webkit-overflow-scrolling: touch;
}

/* ─── 移动端专属底部导航栏 (默认在桌面端隐藏) ─────────────── */
.mobile-bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background: var(--color-surface);
  border-top: 1px solid var(--color-border-subtle);
  z-index: 150;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  backdrop-filter: blur(12px);
  align-items: center;
  justify-content: space-around;
}

.mobile-nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 100%;
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.01em;
  transition: color var(--transition-fast), transform var(--transition-fast);
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  position: relative;
}

.mobile-nav-item:active {
  transform: scale(0.92);
}

.mobile-nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  opacity: 0.75;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.mobile-nav-item.is-active {
  color: var(--color-accent);
  font-weight: 600;
}

.mobile-nav-item.is-active .mobile-nav-icon {
  opacity: 1;
  transform: translateY(-1px);
}

.mobile-nav-item.is-active::after {
  content: '';
  position: absolute;
  top: 4px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-accent);
}

/* ─── 移动端断点响应式适配 (<= 768px) ────────────────────────── */
@media (max-width: 768px) {
  .layout {
    width: 100vw;
    height: 100%;
  }

  .sidebar {
    display: none !important;
  }

  .main-container {
    width: 100vw;
    min-width: 100vw;
    max-width: 100vw;
    height: 100%;
  }

  .app-header {
    height: 52px;
    min-height: 52px;
    padding: 0 16px;
  }

  .header-title {
    font-size: 16px;
  }

  .app-main {
    width: 100%;
    padding-bottom: calc(58px + env(safe-area-inset-bottom, 0px));
  }

  .mobile-bottom-nav {
    display: flex !important;
  }
}
</style>