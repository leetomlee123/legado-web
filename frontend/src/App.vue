<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
auth.init()
</script>

<style>
/* ─── Google Fonts ─────────────────────────────────────── */
/* Outfit: UI 字体 | Noto Serif SC: 阅读正文 */

/* ─── 设计 Token ─────────────────────────────────────────── */
:root {
  /* 颜色系统 — 墨韵书房 */
  --color-bg:           #faf7f2;  /* 奶油白 主背景 */
  --color-bg-subtle:    #f4f0e8;  /* 浅暖白 卡片/二级背景 */
  --color-surface:      #fff9f0;  /* 纯净暖白 浮层 */
  --color-sidebar:      #1c1208;  /* 深墨棕 侧边栏 */
  --color-sidebar-item: rgba(255, 245, 220, 0.06); /* 侧边栏 item 背景 */

  /* 强调色 — 单一书金色 */
  --color-accent:       #b8863a;
  --color-accent-light: #d4a55a;
  --color-accent-pale:  rgba(184, 134, 58, 0.12);
  --color-accent-glow:  rgba(184, 134, 58, 0.25);

  /* 文字 */
  --color-text-primary:   #2a1f14;  /* 深棕 */
  --color-text-secondary: #8a7560;  /* 暖灰 */
  --color-text-muted:     #b8a898;  /* 浅暖灰 */
  --color-text-inverse:   #fdf5e0;  /* 浅奶油 用于深色背景 */

  /* 边框 */
  --color-border:        rgba(184, 134, 58, 0.15);
  --color-border-subtle: rgba(42, 31, 20, 0.08);

  /* 阴影 — 带棕色调 */
  --shadow-xs: 0 1px 3px rgba(42, 31, 20, 0.06), 0 1px 2px rgba(42, 31, 20, 0.04);
  --shadow-sm: 0 2px 8px rgba(42, 31, 20, 0.08), 0 1px 3px rgba(42, 31, 20, 0.06);
  --shadow-md: 0 4px 16px rgba(42, 31, 20, 0.10), 0 2px 6px rgba(42, 31, 20, 0.07);
  --shadow-lg: 0 8px 32px rgba(42, 31, 20, 0.12), 0 4px 12px rgba(42, 31, 20, 0.08);
  --shadow-accent: 0 4px 20px rgba(184, 134, 58, 0.30);

  /* 字体 */
  --font-ui:     'Outfit', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-reading:'Noto Serif SC', 'STSong', 'SimSun', serif;

  /* 圆角 */
  --radius-sm:  6px;
  --radius-md:  10px;
  --radius-lg:  16px;
  --radius-xl:  24px;

  /* 层级 */
  --z-sidebar:  100;
  --z-header:   90;
  --z-overlay:  200;
  --z-modal:    300;
  --z-tooltip:  400;

  /* 过渡 */
  --transition-fast:   150ms ease;
  --transition-base:   220ms ease;
  --transition-slow:   350ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ─── 基础重置 ────────────────────────────────────────────── */
html,
body,
#app {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: var(--font-ui);
  background: var(--color-bg);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ─── 噪声纹理（背景质感）─────────────────────────────────── */
/* 使用 CSS 实现轻微纸张噪声感 */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: 200px 200px;
}

/* ─── Element Plus 主题覆盖 ──────────────────────────────── */
:root {
  --el-color-primary: var(--color-accent);
  --el-color-primary-light-3: var(--color-accent-light);
  --el-color-primary-light-5: rgba(184, 134, 58, 0.4);
  --el-color-primary-light-7: rgba(184, 134, 58, 0.2);
  --el-color-primary-light-8: rgba(184, 134, 58, 0.15);
  --el-color-primary-light-9: rgba(184, 134, 58, 0.08);
  --el-color-primary-dark-2: #9a6e2a;

  --el-border-radius-base: var(--radius-sm);
  --el-border-radius-small: 4px;
  --el-border-radius-round: 20px;

  --el-font-family: var(--font-ui);
  --el-text-color-primary: var(--color-text-primary);
  --el-text-color-regular: var(--color-text-secondary);
  --el-text-color-placeholder: var(--color-text-muted);

  --el-bg-color: var(--color-surface);
  --el-bg-color-page: var(--color-bg);
  --el-border-color: var(--color-border);
  --el-border-color-light: var(--color-border-subtle);
}

/* el-button primary 覆盖 */
.el-button--primary {
  background: var(--color-accent) !important;
  border-color: var(--color-accent) !important;
  color: #fff !important;
  font-weight: 500 !important;
  letter-spacing: 0.02em !important;
  transition: background var(--transition-base), transform var(--transition-fast), box-shadow var(--transition-base) !important;
}

.el-button--primary:hover {
  background: var(--color-accent-light) !important;
  border-color: var(--color-accent-light) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-accent) !important;
}

.el-button--primary:active {
  transform: translateY(0) scale(0.98) !important;
  box-shadow: none !important;
}

/* el-input focus 边框 */
.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--color-accent) inset !important;
}

/* ─── 页面切换过渡 ────────────────────────────────────────── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>