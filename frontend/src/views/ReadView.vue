<template>
  <div class="qidian-reader" :class="[`theme-${theme}`]" :style="readerStyleVars">
    <!-- ── 右侧悬浮功能 Dock（起点经典右侧边栏）─────────────── -->
    <aside class="qidian-right-dock" role="toolbar" aria-label="阅读工具栏">
      <!-- 目录 -->
      <button
        class="dock-item"
        id="dock-toc-btn"
        :class="{ active: showToc }"
        title="目录"
        aria-label="目录"
        @click="showToc = !showToc"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <line x1="8" y1="6" x2="21" y2="6"/>
          <line x1="8" y1="12" x2="21" y2="12"/>
          <line x1="8" y1="18" x2="21" y2="18"/>
          <line x1="3" y1="6" x2="3.01" y2="6"/>
          <line x1="3" y1="12" x2="3.01" y2="12"/>
          <line x1="3" y1="18" x2="3.01" y2="18"/>
        </svg>
        <span class="dock-label">目录</span>
      </button>

      <!-- 换源 -->
      <button
        class="dock-item"
        id="dock-source-btn"
        :class="{ active: showChangeSource }"
        title="切换书源"
        aria-label="切换书源"
        @click="openChangeSourceModal"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 3h5v5"/>
          <path d="M4 20L21 3"/>
          <path d="M21 16v5h-5"/>
          <path d="M15 15l6 6"/>
          <path d="M4 4l5 5"/>
        </svg>
        <span class="dock-label">换源</span>
      </button>

      <!-- 书架/返回 -->
      <button
        class="dock-item"
        id="dock-shelf-btn"
        title="我的书架"
        aria-label="我的书架"
        @click="router.push('/')"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
        <span class="dock-label">书架</span>
      </button>

      <!-- 加入书架（未入架时亮显，已入架时展示已加） -->
      <button
        class="dock-item"
        id="dock-add-shelf-btn"
        :class="{ 'in-shelf': currentBook?.inBookcase }"
        :title="currentBook?.inBookcase ? '已在书架中' : '加入书架'"
        :aria-label="currentBook?.inBookcase ? '已在书架中' : '加入书架'"
        :disabled="addingToShelf || Boolean(currentBook?.inBookcase)"
        @click="onAddToShelf"
      >
        <svg v-if="!addingToShelf" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
        </svg>
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" class="spin" aria-hidden="true">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/>
        </svg>
        <span class="dock-label">{{ currentBook?.inBookcase ? '已在书架' : '加书架' }}</span>
      </button>

      <!-- 日夜间一键切换 -->
      <button
        class="dock-item"
        id="dock-night-btn"
        :title="theme === 'night' ? '切换日间模式' : '切换夜间模式'"
        :aria-label="theme === 'night' ? '切换日间模式' : '切换夜间模式'"
        @click="toggleNightMode"
      >
        <svg v-if="theme !== 'night'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
        <span class="dock-label">{{ theme === 'night' ? '日间' : '夜间' }}</span>
      </button>

      <!-- 设置 -->
      <button
        class="dock-item"
        id="dock-settings-btn"
        :class="{ active: showSettings }"
        title="阅读设置"
        aria-label="阅读设置"
        @click="showSettings = !showSettings"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <line x1="4" y1="21" x2="4" y2="14"/>
          <line x1="4" y1="10" x2="4" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="12"/>
          <line x1="12" y1="8" x2="12" y2="3"/>
          <line x1="20" y1="21" x2="20" y2="16"/>
          <line x1="20" y1="12" x2="20" y2="3"/>
          <line x1="1" y1="14" x2="7" y2="14"/>
          <line x1="9" y1="8" x2="15" y2="8"/>
          <line x1="17" y1="16" x2="23" y2="16"/>
        </svg>
        <span class="dock-label">设置</span>
      </button>

      <!-- 回到顶部 -->
      <button
        class="dock-item dock-item-top"
        id="dock-top-btn"
        title="返回顶部"
        aria-label="返回顶部"
        @click="scrollToTop"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="18 15 12 9 6 15"/>
        </svg>
        <span class="dock-label">顶部</span>
      </button>
    </aside>

    <!-- ── 起点风格阅读容器 ─────────────────────────────────── -->
    <div class="qidian-page-container">
      <!-- ── 中央白纸/羊皮纸卡片阅读区 ──────────────────────── -->
      <main
        class="qidian-read-main"
        id="reader-main"
        :style="{ maxWidth: pageMaxWidthStyle }"
      >
        <!-- 第一阶段：正在解析章节列表 Loading -->
        <div v-if="loadingToc" class="qidian-loading-toc" role="status" aria-live="polite">
          <div class="qd-spinner"></div>
          <div class="qd-loading-title">正在解析章节列表</div>
          <div class="qd-loading-sub">正在从书源实时检索目录，请稍候...</div>
        </div>

        <!-- 目录解析错误 -->
        <div v-else-if="tocError" class="qidian-error-card" role="alert">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ed424b" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p class="error-text">{{ tocError }}</p>
          <button class="btn-qd-retry" @click="initBookAndChapters">重新解析目录</button>
        </div>

        <!-- 正常阅读主体内容 -->
        <article v-else class="qidian-article-wrap">
          <!-- 章节标题 -->
          <h1 class="chapter-main-title">{{ currentChapterTitle }}</h1>

          <!-- 章节元数据信息栏（书名 / 作者 / 字数 / 进度） -->
          <div class="chapter-meta-bar">
            <span class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              </svg>
              {{ currentBook?.name }}
            </span>
            <span class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
              {{ currentBook?.author || '佚名' }}
            </span>
            <span v-if="currentBook?.sourceName" class="meta-item source-meta-click" @click="openChangeSourceModal" title="点击快速切换书源">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 3h5v5"/><path d="M4 20L21 3"/><path d="M21 16v5h-5"/><path d="M15 15l6 6"/><path d="M4 4l5 5"/>
              </svg>
              源: {{ currentBook.sourceName }}
            </span>
            <span v-if="content" class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/>
              </svg>
              {{ content.length }} 字
            </span>
            <span class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
              第 {{ chapterIndex + 1 }} / {{ chapters.length }} 章
            </span>
          </div>

          <!-- 第二阶段：正在解析章节数据 Loading -->
          <div v-if="loadingContent" class="qidian-content-loading" role="status" aria-live="polite">
            <div class="content-loading-tag">
              <span class="spin-dot"></span>
              正在解析章节正文数据...
            </div>
            <div class="qd-skeleton-box">
              <div v-for="n in 14" :key="n" class="qd-sk-line" :style="{ width: skWidth(n) + '%' }"></div>
            </div>
          </div>

          <!-- 正文抓取错误 -->
          <div v-else-if="contentError" class="qidian-error-card" role="alert">
            <p class="error-text">{{ contentError }}</p>
            <button class="btn-qd-retry" @click="loadCurrentChapterContent">重新抓取本章</button>
          </div>

          <!-- 正文段落 -->
          <div v-else class="chapter-content-body" v-html="rendered" aria-live="polite"></div>

          <!-- 底部起点式章节翻页栏 -->
          <div v-if="!loadingContent && !contentError && chapters.length" class="chapter-bottom-nav">
            <button
              class="btn-qd-page"
              id="prev-chapter-btn"
              :disabled="chapterIndex <= 0"
              @click="prevChapter"
              aria-label="上一章"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
              上一章
            </button>

            <button
              class="btn-qd-page btn-toc-shortcut"
              @click="showToc = true"
              aria-label="查看目录"
            >
              目录 ({{ chapterIndex + 1 }}/{{ chapters.length }})
            </button>

            <button
              class="btn-qd-page"
              id="next-chapter-btn"
              :disabled="chapterIndex >= chapters.length - 1"
              @click="nextChapter"
              aria-label="下一章"
            >
              下一章
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
            </button>
          </div>
        </article>
      </main>
    </div>

    <!-- ── 目录抽屉（起点标准左侧全功能目录）─────────────── -->
    <Teleport to="body">
      <transition name="drawer-slide">
        <div
          v-if="showToc"
          class="qd-toc-overlay"
          :class="[`theme-${theme}`]"
          :style="readerStyleVars"
          @click.self="showToc = false"
          role="dialog"
          aria-modal="true"
          aria-label="书籍目录"
        >
          <div class="qd-toc-drawer">
            <!-- 头部：标题与关闭 -->
            <div class="qd-toc-head">
              <div class="toc-head-main">
                <span class="toc-head-title">目录</span>
                <span class="toc-head-book" :title="currentBook?.name">《{{ currentBook?.name }}》</span>
              </div>
              <button class="qd-close-btn" aria-label="关闭目录" @click="showToc = false">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <!-- 控制条：分卷统计、排序与定位 -->
            <div class="qd-toc-subhead">
              <div class="toc-volume-tag">
                正文卷 · 共 <strong>{{ chapters.length }}</strong> 章
              </div>
              <div class="toc-head-tools">
                <button
                  class="btn-toc-tool"
                  :title="isReverseOrder ? '切换为正序' : '切换为倒序'"
                  @click="isReverseOrder = !isReverseOrder"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="7 3 7 21"/><polyline points="3 7 7 3 11 7"/><polyline points="17 21 17 3"/><polyline points="13 17 17 21 21 17"/>
                  </svg>
                  {{ isReverseOrder ? '倒序' : '正序' }}
                </button>
                <button
                  class="btn-toc-tool btn-locate-cur"
                  title="定位到当前章节"
                  @click="scrollToActiveChapter"
                >
                  定位当前
                </button>
              </div>
            </div>

            <!-- 搜索框 -->
            <div class="qd-toc-search-wrap">
              <span class="search-ico" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                </svg>
              </span>
              <input
                v-model="tocKeyword"
                type="search"
                class="toc-search-input"
                placeholder="搜索章节名称或序号..."
                aria-label="搜索章节"
              />
              <button
                v-if="tocKeyword"
                class="btn-clear-search"
                aria-label="清空搜索"
                @click="tocKeyword = ''"
              >
                ✕
              </button>
            </div>

            <!-- 目录章节列表 -->
            <div class="qd-toc-scroll" id="qd-toc-scroll" role="list">
              <div v-if="filteredChapters.length === 0" class="toc-empty-filter">
                未搜索到匹配章节
              </div>

              <button
                v-for="item in filteredChapters"
                :key="item.id || item.originalIndex"
                class="qd-toc-cell"
                :class="{ active: item.originalIndex === chapterIndex }"
                :id="`toc-cell-${item.originalIndex}`"
                role="listitem"
                @click="goToChapter(item.originalIndex)"
              >
                <span class="cell-num">{{ item.originalIndex + 1 }}</span>
                <span class="cell-title" :title="item.title">{{ item.title }}</span>
                <span v-if="item.originalIndex === chapterIndex" class="cell-badge">当前读到</span>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- ── 起点 1:1 阅读设置弹窗 ──────────────────────────── -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div
          v-if="showSettings"
          class="qd-settings-overlay"
          @click.self="showSettings = false"
          role="dialog"
          aria-modal="true"
          aria-label="阅读设置"
        >
          <div class="qd-settings-modal">
            <!-- 头部 -->
            <div class="settings-modal-head">
              <span class="modal-title">设置</span>
              <button class="modal-close-btn" id="settings-close-btn" aria-label="关闭设置" @click="showSettings = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div class="settings-modal-body">
              <!-- 1. 阅读主题 -->
              <div class="setting-item-row">
                <span class="setting-item-label">阅读主题</span>
                <div class="theme-circle-list">
                  <button
                    v-for="t in THEMES"
                    :key="t.id"
                    class="theme-circle-btn"
                    :class="{ active: theme === t.id }"
                    :style="{ background: t.swatchBg }"
                    :aria-label="t.label"
                    :title="t.label"
                    @click="theme = t.id"
                  >
                    <span v-if="theme === t.id" class="theme-check-icon">✓</span>
                  </button>
                </div>
              </div>

              <!-- 2. 正文字体 -->
              <div class="setting-item-row">
                <span class="setting-item-label">正文字体</span>
                <div class="segmented-group">
                  <button
                    v-for="f in FONTS"
                    :key="f.id"
                    class="seg-btn"
                    :class="{ active: fontFamily === f.id }"
                    @click="fontFamily = f.id"
                  >
                    {{ f.label }}
                  </button>
                </div>
              </div>

              <!-- 3. 字体大小 -->
              <div class="setting-item-row">
                <span class="setting-item-label">字体大小</span>
                <div class="font-size-stepper">
                  <button class="step-btn" aria-label="缩小字号" @click="fontSize = Math.max(14, fontSize - 1)">A-</button>
                  <span class="step-value">{{ fontSize }}</span>
                  <button class="step-btn" aria-label="增大字号" @click="fontSize = Math.min(28, fontSize + 1)">A+</button>
                </div>
              </div>

              <!-- 4. 页面宽度 -->
              <div class="setting-item-row">
                <span class="setting-item-label">页面宽度</span>
                <div class="segmented-group">
                  <button
                    v-for="w in PAGE_WIDTHS"
                    :key="w.id"
                    class="seg-btn"
                    :class="{ active: pageWidth === w.id }"
                    @click="pageWidth = w.id"
                  >
                    {{ w.label }}
                  </button>
                </div>
              </div>

              <!-- 5. 行距设置 -->
              <div class="setting-item-row">
                <span class="setting-item-label">行间距离</span>
                <div class="segmented-group">
                  <button
                    v-for="lh in [1.6, 1.8, 2.0, 2.2]"
                    :key="lh"
                    class="seg-btn"
                    :class="{ active: lineHeight === lh }"
                    @click="lineHeight = lh"
                  >
                    {{ lh }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- ── 起点风格 换源抽屉 ─────────────────────────────── -->
    <Teleport to="body">
      <transition name="drawer-slide-right">
        <div
          v-if="showChangeSource"
          class="qd-source-overlay"
          :class="[`theme-${theme}`]"
          :style="readerStyleVars"
          @click.self="closeChangeSourceModal"
          role="dialog"
          aria-modal="true"
          aria-label="切换书源"
        >
          <div class="qd-source-drawer">
            <!-- 头部 -->
            <div class="source-drawer-head">
              <div class="source-head-info">
                <span class="source-drawer-title">切换书源</span>
                <span class="source-cur-tag" v-if="currentBook?.sourceName">
                  当前: {{ currentBook.sourceName }}
                </span>
              </div>
              <button class="qd-close-btn" aria-label="关闭换源" @click="closeChangeSourceModal">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <!-- 搜索栏 -->
            <div class="source-search-bar">
              <input
                v-model="sourceSearchKeyword"
                type="search"
                class="source-search-input"
                placeholder="输入书名搜索同名书籍..."
                @keyup.enter="startSourceSearch"
              />
              <button
                class="btn-source-search"
                :disabled="searchingSources"
                @click="startSourceSearch"
              >
                <svg v-if="!searchingSources" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                </svg>
                <span v-else class="spin-dot"></span>
                {{ searchingSources ? '检索中' : '搜索' }}
              </button>
            </div>

            <!-- 检索状态条 -->
            <div class="source-search-status">
              <span class="status-left">
                <span v-if="searchingSources" class="status-loading-text">
                  <span class="spin-dot"></span>
                  正在全网多源检索 ({{ sourceSearchCompleted }}/{{ sourceSearchTotal }})...
                </span>
                <span v-else-if="sourceSearchResults.length" class="status-count-text">
                  共检索到 <strong>{{ sourceSearchResults.length }}</strong> 个可用书源
                </span>
                <span v-else class="status-empty-text">未检索到完全匹配的书源</span>
              </span>
              <div class="status-right-tools">
                <label class="exact-match-toggle" title="只显示与书名完全一致的书源">
                  <input type="checkbox" v-model="exactMatchOnly" />
                  <span>仅完全匹配</span>
                </label>
                <button
                  v-if="searchingSources"
                  class="btn-stop-source-search"
                  @click="stopSourceSearch"
                >
                  停止检索
                </button>
              </div>
            </div>

            <!-- 候选书源列表 -->
            <div class="source-results-scroll" role="list">
              <div v-if="!sourceSearchResults.length && !searchingSources" class="source-empty-state">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <p>未搜索到其他可用书源</p>
                <span>您可以尝试修改搜索词，或前往“书源管理”导入更多书源规则</span>
              </div>

              <div
                v-for="(item, idx) in sourceSearchResults"
                :key="item.sourceId + '_' + item.bookUrl + '_' + idx"
                class="source-candidate-card"
                :class="{ 'is-current': isCurrentSource(item) }"
                role="listitem"
              >
                <div class="candidate-top">
                  <div class="candidate-source-name">
                    <span class="source-pill">{{ item.sourceName }}</span>
                    <span v-if="isCurrentSource(item)" class="badge-current">当前在读</span>
                  </div>
                  <button
                    class="btn-switch-source"
                    :class="{ 'btn-using': isCurrentSource(item) }"
                    :disabled="isCurrentSource(item) || switchingSourceId === item.sourceId"
                    @click="onSelectSwitchSource(item)"
                  >
                    <span v-if="switchingSourceId === item.sourceId" class="spin-dot"></span>
                    <span v-if="isCurrentSource(item)">使用中</span>
                    <span v-else-if="switchingSourceId === item.sourceId">切换中...</span>
                    <span v-else>切换至此源</span>
                  </button>
                </div>

                <div class="candidate-book-info">
                  <span class="candidate-title">《{{ item.name }}》</span>
                  <span class="candidate-author">{{ item.author || '作者不详' }}</span>
                </div>

                <p v-if="item.intro" class="candidate-intro">{{ item.intro }}</p>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getBook,
  listChapters,
  getChapterContent,
  addBookToShelf,
  getReadProgress,
  saveReadProgress,
  changeBookSource,
  searchStream,
} from '@/api'
import type { Book, Chapter } from '@/types'

const route = useRoute()
const router = useRouter()

// 路由标识符（UUID 或数字 ID）
const identifier = computed(() => String(route.params.book || ''))

const currentBook = ref<Book | null>(null)
const chapters = ref<Chapter[]>([])
const chapterIndex = ref(0)
const contentCache = ref<Map<number, string>>(new Map()) // index -> content
const content = ref('')

// 加载状态
const loadingToc = ref(false)         // 正在解析章节列表
const loadingContent = ref(false)     // 正在解析章节数据
const tocError = ref('')
const contentError = ref('')
const addingToShelf = ref(false)

const showToc = ref(false)
const showSettings = ref(false)
const tocKeyword = ref('')
const isReverseOrder = ref(false)

// ── 换源相关状态 ─────────────────────────────────────────
interface CandidateSourceItem {
  sourceId: number
  sourceName: string
  name: string
  author?: string
  cover?: string
  intro?: string
  bookUrl: string
}

const showChangeSource = ref(false)
const sourceSearchKeyword = ref('')
const exactMatchOnly = ref(true)
const searchingSources = ref(false)
const rawSourceSearchResults = ref<CandidateSourceItem[]>([])
const sourceSearchCompleted = ref(0)
const sourceSearchTotal = ref(0)
const switchingSourceId = ref<number | null>(null)
let cancelSourceSearchStream: (() => void) | null = null

function cleanBookTitle(t: string): string {
  return (t || '')
    .trim()
    .toLowerCase()
    .replace(/[《》\(\)\[\]【】\s\-_·:：]/g, '')
}

const sourceSearchResults = computed(() => {
  if (!exactMatchOnly.value) {
    return rawSourceSearchResults.value
  }
  const targetClean = cleanBookTitle(sourceSearchKeyword.value || currentBook.value?.name || '')
  if (!targetClean) {
    return rawSourceSearchResults.value
  }
  return rawSourceSearchResults.value.filter((item) => {
    const itemClean = cleanBookTitle(item.name)
    return itemClean === targetClean
  })
})

// 过滤与排序后的目录章节
const filteredChapters = computed(() => {
  const kw = tocKeyword.value.trim().toLowerCase()
  let list = chapters.value.map((c, originalIndex) => ({
    ...c,
    originalIndex,
  }))

  if (kw) {
    list = list.filter(
      (c) =>
        c.title.toLowerCase().includes(kw) ||
        String(c.originalIndex + 1).includes(kw)
    )
  }

  if (isReverseOrder.value) {
    return [...list].reverse()
  }
  return list
})

function scrollToActiveChapter() {
  const el = document.getElementById(`toc-cell-${chapterIndex.value}`)
  if (el) {
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
}

// 打开目录时自动定位当前阅读章节
watch(showToc, (val) => {
  if (val) {
    nextTick(() => {
      setTimeout(() => {
        scrollToActiveChapter()
      }, 100)
    })
  }
})

// ── 计算属性 ─────────────────────────────────────────────
const currentChapterTitle = computed(() =>
  chapters.value[chapterIndex.value]?.title || ''
)

const rendered = computed(() => {
  if (!content.value) return ''
  return content.value
    .split('\n')
    .filter((p) => p.trim())
    .map((p) => `<p>${p}</p>`)
    .join('')
})

// ── 起点风格主题配置 ─────────────────────────────────────
type ThemeId = 'cream' | 'white' | 'eye' | 'blue' | 'night'
const THEMES: { id: ThemeId; label: string; swatchBg: string; canvasBg: string; pageBg: string; text: string }[] = [
  { id: 'white', label: '默认白', swatchBg: '#ffffff', canvasBg: '#f6f6f6', pageBg: '#ffffff', text: '#262626' },
  { id: 'cream', label: '羊皮纸', swatchBg: '#f5efe3', canvasBg: '#eae5d8', pageBg: '#f5efe3', text: '#332c25' },
  { id: 'eye', label: '护眼绿', swatchBg: '#e2f2e2', canvasBg: '#d8ebd8', pageBg: '#e2f2e2', text: '#1f331f' },
  { id: 'blue', label: '淡雅蓝', swatchBg: '#e3eff5', canvasBg: '#d7e4ea', pageBg: '#e3eff5', text: '#1c2e38' },
  { id: 'night', label: '夜间黑', swatchBg: '#1e1e1e', canvasBg: '#141414', pageBg: '#1e1e1e', text: '#9e9e9e' },
]

const FONTS = [
  { id: 'sans', label: '黑体' },
  { id: 'serif', label: '宋体' },
  { id: 'kai', label: '楷体' },
]

const FONT_MAP: Record<string, string> = {
  sans: "'PingFang SC', 'Microsoft YaHei', sans-serif",
  serif: "'Noto Serif SC', 'STSong', 'SimSun', serif",
  kai: "'KaiTi', 'STKaiti', serif",
}

const PAGE_WIDTHS = [
  { id: 'auto', label: '自动' },
  { id: '640', label: '640' },
  { id: '800', label: '800' },
  { id: '900', label: '900' },
  { id: '1000', label: '1000' },
  { id: '1280', label: '1280' },
]

const theme = ref<ThemeId>('cream')
const fontSize = ref(18)
const lineHeight = ref(1.9)
const fontFamily = ref('sans')
const pageWidth = ref('800')

const pageMaxWidthStyle = computed(() => {
  if (pageWidth.value === 'auto') return '100%'
  return `${pageWidth.value}px`
})

const readerStyleVars = computed(() => {
  const currentTheme = THEMES.find((t) => t.id === theme.value) || THEMES[1]
  const widthVal = pageWidth.value === 'auto' ? 800 : Number(pageWidth.value) || 800
  const dockLeftOffset = widthVal / 2 + 10
  return {
    '--qd-canvas-bg': currentTheme.canvasBg,
    '--qd-page-bg': currentTheme.pageBg,
    '--qd-text-color': currentTheme.text,
    '--qd-font-family': FONT_MAP[fontFamily.value],
    '--qd-font-size': `${fontSize.value}px`,
    '--qd-line-height': lineHeight.value,
    '--qd-dock-left': `calc(50% + ${dockLeftOffset}px)`,
  }
})

function toggleNightMode() {
  theme.value = theme.value === 'night' ? 'cream' : 'night'
}

function scrollToTop() {
  window.scrollTo(0, 0)
}

function skWidth(n: number) {
  const rng = [92, 88, 95, 85, 90, 78, 94, 87, 91, 82, 96, 84, 89, 60]
  return rng[n % rng.length]
}

// ── 阅读进度保存 ─────────────────────────────────────────
function persistProgress(index: number) {
  const targetChapter = chapters.value[index]
  if (!targetChapter || !identifier.value) return

  // 1. 本地存储快速写
  try {
    localStorage.setItem(
      `read_progress_${identifier.value}`,
      JSON.stringify({ index, chapterId: targetChapter.id, time: Date.now() })
    )
  } catch {}

  // 2. 后端数据库记录
  saveReadProgress(identifier.value, {
    chapterId: targetChapter.id,
    chapterIndex: index,
  }).catch((err) => {
    console.debug('[progress] save failed:', err)
  })
}

// ── 数据初始化与加载 ─────────────────────────────────────

async function initBookAndChapters() {
  const idOrUuid = identifier.value
  if (!idOrUuid) {
    tocError.value = '未找到书籍标识符'
    return
  }

  // 1. 获取书籍信息
  try {
    const b = await getBook(idOrUuid)
    currentBook.value = b
  } catch (e: any) {
    console.warn('获取书籍信息失败:', e)
  }

  // 2. 解析章节列表（第一阶段 Loading）
  loadingToc.value = true
  tocError.value = ''
  try {
    const list = await listChapters(idOrUuid)
    if (!list || !list.length) {
      throw new Error('未获取到章节目录，请检查书源是否有效')
    }
    chapters.value = list
    loadingToc.value = false

    // 3. 读取历史阅读记录并恢复
    let initialIndex = 0
    try {
      const prog = await getReadProgress(idOrUuid)
      if (prog && typeof prog.chapterIndex === 'number' && prog.chapterIndex >= 0 && prog.chapterIndex < list.length) {
        initialIndex = prog.chapterIndex
      } else {
        const local = localStorage.getItem(`read_progress_${idOrUuid}`)
        if (local) {
          const parsed = JSON.parse(local)
          if (parsed && typeof parsed.index === 'number' && parsed.index < list.length) {
            initialIndex = parsed.index
          }
        }
      }
    } catch (e) {
      console.debug('读取阅读进度失败:', e)
    }

    // 4. 解析目标章节数据（第二阶段 Loading）
    await loadChapterContentByIndex(initialIndex)
  } catch (e: any) {
    loadingToc.value = false
    tocError.value = e.message || '章节列表解析失败'
  }
}

// 正在预加载的章节索引集合（避免重复请求）
const preloadingSet = new Set<number>()

/** 静默预加载相邻前后章节内容 */
async function preloadNeighborChapters(currentIndex: number) {
  if (!chapters.value.length || !identifier.value) return

  // 优先级：先预加载下一章（+1），再预加载上一章（-1），接着预加载下下章（+2）
  const candidates = [currentIndex + 1, currentIndex - 1, currentIndex + 2]
  const targetIndices = candidates.filter(
    (idx) =>
      idx >= 0 &&
      idx < chapters.value.length &&
      !contentCache.value.has(idx) &&
      !preloadingSet.has(idx)
  )

  for (const idx of targetIndices) {
    const chapter = chapters.value[idx]
    if (!chapter) continue

    preloadingSet.add(idx)
    getChapterContent(identifier.value, chapter.id)
      .then((res) => {
        const text = res?.content || ''
        if (text.trim()) {
          contentCache.value.set(idx, text)
        }
      })
      .catch((err) => {
        console.debug(`[preload] chapter ${idx} skipped:`, err)
      })
      .finally(() => {
        preloadingSet.delete(idx)
      })
  }
}

/** 加载指定章节的正文内容 */
async function loadChapterContentByIndex(index: number) {
  chapterIndex.value = index

  // 1. 若已有缓存，秒开展现
  if (contentCache.value.has(index)) {
    content.value = contentCache.value.get(index)!
    loadingContent.value = false
    contentError.value = ''
    scrollToTop()
    persistProgress(index)
    preloadNeighborChapters(index)
    return
  }

  const targetChapter = chapters.value[index]
  if (!targetChapter) return

  loadingContent.value = true
  contentError.value = ''
  content.value = ''
  scrollToTop()

  try {
    const res = await getChapterContent(identifier.value, targetChapter.id)
    const text = res?.content || ''
    if (!text.trim()) {
      throw new Error('章节内容为空，可能书源规则不匹配')
    }
    content.value = text
    contentCache.value.set(index, text)
    persistProgress(index)
    preloadNeighborChapters(index)
  } catch (e: any) {
    contentError.value = e.message || '章节数据解析失败'
  } finally {
    loadingContent.value = false
  }
}

async function loadCurrentChapterContent() {
  await loadChapterContentByIndex(chapterIndex.value)
}

function goToChapter(index: number) {
  loadChapterContentByIndex(index)
  showToc.value = false
}

function prevChapter() {
  if (chapterIndex.value > 0) goToChapter(chapterIndex.value - 1)
}

function nextChapter() {
  if (chapterIndex.value < chapters.value.length - 1) goToChapter(chapterIndex.value + 1)
}

// ── 加入书架 ─────────────────────────────────────────────
async function onAddToShelf() {
  if (addingToShelf.value || currentBook.value?.inBookcase) return
  addingToShelf.value = true
  try {
    const saved = await addBookToShelf(identifier.value)
    if (currentBook.value) {
      currentBook.value.inBookcase = 1
    }
    ElMessage.success(`《${saved.name || currentBook.value?.name}》已加入书架`)
  } catch (e: any) {
    ElMessage.error(e.message || '加入书架失败')
  } finally {
    addingToShelf.value = false
  }
}

// ── 换源方法 ─────────────────────────────────────────────
function openChangeSourceModal() {
  if (currentBook.value?.source_type && currentBook.value.source_type !== 'web') {
    ElMessage.info('当前为本地导入书籍，仅网络书源书籍支持换源')
    return
  }
  showChangeSource.value = true
  sourceSearchKeyword.value = currentBook.value?.name || ''
  if (sourceSearchResults.value.length === 0) {
    startSourceSearch()
  }
}

function closeChangeSourceModal() {
  showChangeSource.value = false
  stopSourceSearch()
}

function stopSourceSearch() {
  if (cancelSourceSearchStream) {
    cancelSourceSearchStream()
    cancelSourceSearchStream = null
  }
  searchingSources.value = false
}

function startSourceSearch() {
  stopSourceSearch()
  const kw = sourceSearchKeyword.value.trim()
  if (!kw) {
    ElMessage.warning('请输入搜索书名')
    return
  }

  rawSourceSearchResults.value = []
  searchingSources.value = true
  sourceSearchCompleted.value = 0
  sourceSearchTotal.value = 0

  const seenUrls = new Set<string>()

  cancelSourceSearchStream = searchStream(
    kw,
    undefined,
    (data) => {
      if (data.type === 'start') {
        sourceSearchTotal.value = data.totalSources || 0
      } else if (data.type === 'source_result') {
        sourceSearchCompleted.value = data.completed || 0
        sourceSearchTotal.value = data.totalSources || 0
        if (data.books && data.books.length) {
          for (const b of data.books) {
            const anyB = b as any
            const bUrl = anyB.bookUrl || anyB.source_url || anyB.sourceUrl || ''
            const sid = Number(data.sourceId || anyB.sourceId || anyB.source_id || 0)
            const key = `${sid}_${bUrl}`
            if (bUrl && sid && !seenUrls.has(key)) {
              seenUrls.add(key)
              rawSourceSearchResults.value.push({
                sourceId: sid,
                sourceName: data.sourceName || anyB.sourceName || '未知书源',
                name: b.name,
                author: b.author || '',
                cover: b.cover || '',
                intro: b.intro || '',
                bookUrl: bUrl,
              })
            }
          }
        }
      } else if (data.type === 'done') {
        searchingSources.value = false
      }
    },
    () => {
      searchingSources.value = false
    },
    (err) => {
      console.debug('[source search stream err]', err)
      searchingSources.value = false
    }
  )
}

function isCurrentSource(item: CandidateSourceItem): boolean {
  if (!currentBook.value) return false
  const curSid = Number(currentBook.value.source_id || currentBook.value.sourceId || 0)
  const curUrl = currentBook.value.source_url || currentBook.value.sourceUrl || ''
  return curSid === item.sourceId || (Boolean(curUrl) && curUrl === item.bookUrl)
}

async function onSelectSwitchSource(item: CandidateSourceItem) {
  if (switchingSourceId.value !== null) return
  if (!identifier.value) return

  switchingSourceId.value = item.sourceId
  try {
    const curTitle = currentChapterTitle.value
    const curIdx = chapterIndex.value
    const res = await changeBookSource(identifier.value, {
      sourceId: item.sourceId,
      bookUrl: item.bookUrl,
      name: item.name,
      author: item.author,
      cover: item.cover,
      intro: item.intro,
      currentChapterTitle: curTitle,
      currentChapterIndex: curIdx,
    })

    if (res && res.ok) {
      currentBook.value = res.book
      contentCache.value.clear()
      showChangeSource.value = false
      ElMessage.success(res.message || `已成功切换至【${item.sourceName}】`)
      // 重新加载章节目录和阅读内容
      await initBookAndChapters()
    } else {
      throw new Error(res?.message || '换源响应异常')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '切换书源失败，请重试')
  } finally {
    switchingSourceId.value = null
  }
}

// ── 键盘快捷键监听 ───────────────────────────────────────
function onKeyDown(e: KeyboardEvent) {
  if (showToc.value || showSettings.value || showChangeSource.value) {
    if (e.key === 'Escape') {
      showToc.value = false
      showSettings.value = false
      closeChangeSourceModal()
    }
    return
  }
  if (e.key === 'ArrowLeft') {
    prevChapter()
  } else if (e.key === 'ArrowRight') {
    nextChapter()
  }
}

onMounted(() => {
  initBookAndChapters()
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  stopSourceSearch()
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<style scoped>
/* ─── 起点阅读整体画布 ────────────────────────────────────── */
.qidian-reader {
  min-height: 100vh;
  background-color: var(--qd-canvas-bg);
  color: var(--qd-text-color);
  font-family: var(--qd-font-family);
  transition: background-color 0.25s ease, color 0.25s ease;
  position: relative;
}

/* ─── 右侧起点经典悬浮 Dock ──────────────────────────────── */
.qidian-right-dock {
  position: fixed;
  left: var(--qd-dock-left, calc(50% + 410px));
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  background: var(--qd-page-bg);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  z-index: 30;
  transition: left 0.2s ease;
}

@media (max-width: 1100px) {
  .qidian-right-dock {
    left: auto;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
  }
}

@media (max-width: 600px) {
  .qidian-right-dock {
    bottom: 20px;
    top: auto;
    right: 12px;
    transform: none;
    border-radius: 24px;
  }
}

.dock-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  color: var(--qd-text-color);
  opacity: 0.75;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
  gap: 3px;
}

.dock-item:last-child {
  border-bottom: none;
}

.dock-item:hover:not(:disabled) {
  opacity: 1;
  color: #ed424b;
  background-color: rgba(237, 66, 75, 0.06);
}

.dock-item.active {
  opacity: 1;
  color: #ed424b;
  background-color: rgba(237, 66, 75, 0.08);
}

.dock-item.in-shelf {
  color: #52c41a;
}

.dock-item:disabled {
  cursor: default;
}

.dock-label {
  font-size: 11px;
  line-height: 1;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ─── 页面容器 ────────────────────────────────────────────── */
.qidian-page-container {
  width: 100%;
  min-height: 100vh;
  padding: 32px 0 80px;
}

/* ─── 中央阅读主卡片 ──────────────────────────────────────── */
.qidian-read-main {
  width: 100%;
  margin: 0 auto;
  background-color: var(--qd-page-bg);
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.06);
  border-radius: 4px;
  box-sizing: border-box;
  padding: 40px 64px 64px;
  transition: max-width 0.2s ease, background-color 0.25s ease;
}

@media (max-width: 768px) {
  .qidian-read-main {
    padding: 24px 18px 48px;
    margin-top: 0;
    box-shadow: none;
    border-radius: 0;
  }
}

/* ─── 章节主标题与元数据 ─────────────────────────────────── */
.chapter-main-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--qd-text-color);
  margin: 0 0 16px;
  line-height: 1.35;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.chapter-meta-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  padding-bottom: 24px;
  margin-bottom: 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  font-size: 12px;
  color: #888;
  flex-wrap: wrap;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

/* ─── 正文排版（起点 2em 首行缩进标准）─────────────────────── */
.chapter-content-body {
  font-size: var(--qd-font-size);
  line-height: var(--qd-line-height);
  color: var(--qd-text-color);
}

.chapter-content-body :deep(p) {
  text-indent: 2em;
  margin: 0 0 1.15em;
  text-align: justify;
  letter-spacing: 0.02em;
}

/* ─── 底部章节翻页栏 ──────────────────────────────────────── */
.chapter-bottom-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 56px;
  padding-top: 28px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  flex-wrap: wrap;
}

.btn-qd-page {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 24px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 4px;
  color: var(--qd-text-color);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-qd-page:hover:not(:disabled) {
  border-color: #ed424b;
  color: #ed424b;
  background: rgba(237, 66, 75, 0.05);
}

.btn-qd-page:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-toc-shortcut {
  background: transparent;
  border: none;
  font-size: 13px;
  color: #888;
}

/* ─── Loading 状态 ────────────────────────────────────────── */
.qidian-loading-toc {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 90px 20px;
  text-align: center;
}

.qd-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(237, 66, 75, 0.2);
  border-top-color: #ed424b;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

.qd-loading-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--qd-text-color);
  margin-bottom: 6px;
}

.qd-loading-sub {
  font-size: 13px;
  color: #999;
}

.qidian-content-loading {
  padding: 20px 0;
}

.content-loading-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: rgba(237, 66, 75, 0.08);
  color: #ed424b;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
  margin-bottom: 24px;
}

.spin-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ed424b;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 1; }
}

.qd-skeleton-box {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.qd-sk-line {
  height: 18px;
  border-radius: 3px;
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.04) 25%, rgba(0, 0, 0, 0.08) 50%, rgba(0, 0, 0, 0.04) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ─── 错误卡片 ────────────────────────────────────────────── */
.qidian-error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  text-align: center;
}

.error-text {
  font-size: 15px;
  color: #ed424b;
  margin: 14px 0 20px;
}

.btn-qd-retry {
  padding: 8px 24px;
  background: #ed424b;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-qd-retry:hover {
  opacity: 0.9;
}

/* ─── 目录抽屉（起点标准左侧全功能目录）─────────────── */
.qd-toc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
}

.qd-toc-drawer {
  width: 440px;
  max-width: 90vw;
  height: 100%;
  background: var(--qd-page-bg, #ffffff);
  color: var(--qd-text-color, #262626);
  display: flex;
  flex-direction: column;
  box-shadow: 6px 0 28px rgba(0, 0, 0, 0.22);
  border-right: 1px solid rgba(0, 0, 0, 0.08);
}

.qd-toc-head {
  padding: 16px 20px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.toc-head-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.toc-head-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--qd-text-color);
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.toc-head-book {
  font-size: 13px;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.qd-close-btn {
  background: transparent;
  border: none;
  color: inherit;
  opacity: 0.55;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: opacity 0.15s, color 0.15s;
}

.qd-close-btn:hover {
  opacity: 1;
  color: #ed424b;
}

/* 控制子栏 */
.qd-toc-subhead {
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.02);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.toc-volume-tag {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.toc-volume-tag strong {
  color: #ed424b;
}

.toc-head-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-toc-tool {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  font-size: 12px;
  color: var(--qd-text-color);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-toc-tool:hover {
  border-color: #ed424b;
  color: #ed424b;
}

.btn-locate-cur {
  color: #ed424b;
  border-color: rgba(237, 66, 75, 0.3);
  background: rgba(237, 66, 75, 0.05);
}

/* 搜索框 */
.qd-toc-search-wrap {
  position: relative;
  padding: 10px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.search-ico {
  position: absolute;
  left: 30px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
  display: flex;
  align-items: center;
  pointer-events: none;
}

.toc-search-input {
  width: 100%;
  padding: 8px 30px 8px 32px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  background: var(--qd-canvas-bg, #f6f6f6);
  color: var(--qd-text-color, #262626);
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.toc-search-input:focus {
  border-color: #ed424b;
}

.btn-clear-search {
  position: absolute;
  right: 28px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 12px;
  padding: 4px;
}

/* 章节滚动列表 */
.qd-toc-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

.toc-empty-filter {
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.qd-toc-cell {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 11px 20px;
  background: transparent;
  border: none;
  border-left: 3px solid transparent;
  color: var(--qd-text-color);
  font-size: 13.5px;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s, border-color 0.15s;
  gap: 10px;
  box-sizing: border-box;
}

.qd-toc-cell:hover {
  background-color: rgba(237, 66, 75, 0.06);
  color: #ed424b;
}

.qd-toc-cell.active {
  background-color: rgba(237, 66, 75, 0.09);
  color: #ed424b;
  font-weight: 600;
  border-left-color: #ed424b;
}

.cell-num {
  font-size: 12px;
  color: #999;
  min-width: 32px;
}

.cell-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-badge {
  font-size: 11px;
  padding: 2px 6px;
  background: #ed424b;
  color: #fff;
  border-radius: 3px;
  font-weight: 500;
  white-space: nowrap;
}

/* ─── 起点 1:1 设置弹窗 ───────────────────────────────────── */
.qd-settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qd-settings-modal {
  width: 440px;
  max-width: 90vw;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  overflow: hidden;
  color: #333;
  animation: modal-pop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modal-pop {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.settings-modal-head {
  padding: 16px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f0f0f0;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}

.modal-close-btn {
  background: transparent;
  border: none;
  color: #999;
  cursor: pointer;
  padding: 4px;
}

.modal-close-btn:hover {
  color: #ed424b;
}

.settings-modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.setting-item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.setting-item-label {
  font-size: 13px;
  color: #666;
  min-width: 64px;
}

/* 主题圆形按钮 */
.theme-circle-list {
  display: flex;
  align-items: center;
  gap: 12px;
}

.theme-circle-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.15);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: transform 0.15s, border-color 0.15s;
  padding: 0;
}

.theme-circle-btn.active {
  border: 2px solid #ed424b;
  transform: scale(1.1);
}

.theme-check-icon {
  font-size: 13px;
  color: #ed424b;
  font-weight: bold;
}

/* 起点分段按钮（Segmented Group） */
.segmented-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.seg-btn {
  padding: 6px 12px;
  background: #f5f5f5;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 12px;
  color: #555;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.seg-btn:hover {
  color: #ed424b;
}

.seg-btn.active {
  background: #fff;
  border-color: #ed424b;
  color: #ed424b;
  font-weight: 600;
}

/* 字号步进器 */
.font-size-stepper {
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.step-btn {
  padding: 6px 16px;
  background: transparent;
  border: none;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  cursor: pointer;
  transition: background-color 0.15s;
}

.step-btn:hover {
  background-color: rgba(0, 0, 0, 0.06);
  color: #ed424b;
}

.step-value {
  padding: 0 16px;
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.source-meta-click {
  cursor: pointer;
  color: var(--color-accent, #c0692e);
  transition: opacity 0.15s ease;
}

.source-meta-click:hover {
  opacity: 0.8;
  text-decoration: underline;
}

/* ─── 换源抽屉样式 ────────────────────────────────────────── */
.qd-source-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
}

.qd-source-drawer {
  width: 460px;
  max-width: 90vw;
  height: 100%;
  background: var(--qd-page-bg, #fff);
  color: var(--qd-text-color, #262626);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
  position: relative;
  box-sizing: border-box;
}

.source-drawer-head {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.source-head-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.source-drawer-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--qd-text-color, #262626);
}

.source-cur-tag {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(184, 134, 58, 0.12);
  color: var(--color-accent, #b8863a);
  border: 1px solid rgba(184, 134, 58, 0.25);
}

.source-search-bar {
  display: flex;
  gap: 8px;
  padding: 14px 20px 10px;
}

.source-search-input {
  flex: 1;
  padding: 9px 12px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.02);
  color: inherit;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s ease;
}

.source-search-input:focus {
  border-color: var(--color-accent, #b8863a);
  background: #fff;
}

.btn-source-search {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 16px;
  background: var(--color-accent, #b8863a);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s ease;
}

.btn-source-search:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-source-search:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.source-search-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 20px 10px;
  font-size: 12px;
  color: #888;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
}

.status-loading-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-accent, #b8863a);
}

.status-count-text strong {
  color: var(--color-accent, #b8863a);
}

.status-right-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.exact-match-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: var(--qd-text-color, #555);
  cursor: pointer;
  user-select: none;
}

.exact-match-toggle input {
  cursor: pointer;
  accent-color: var(--color-accent, #b8863a);
}

.btn-stop-source-search {
  background: none;
  border: 1px solid rgba(245, 34, 45, 0.4);
  color: #f5222d;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.btn-stop-source-search:hover {
  background: rgba(245, 34, 45, 0.08);
}

.source-results-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 14px 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: #999;
}

.source-empty-state svg {
  margin-bottom: 12px;
  opacity: 0.5;
}

.source-empty-state p {
  font-size: 14px;
  font-weight: 500;
  margin: 0 0 4px;
  color: #666;
}

.source-empty-state span {
  font-size: 12px;
  color: #999;
}

.source-candidate-card {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.015);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s ease;
}

.source-candidate-card:hover {
  border-color: rgba(184, 134, 58, 0.35);
  background: rgba(184, 134, 58, 0.03);
}

.source-candidate-card.is-current {
  border-color: rgba(46, 125, 110, 0.35);
  background: rgba(46, 125, 110, 0.04);
}

.candidate-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.candidate-source-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-pill {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent, #b8863a);
  background: rgba(184, 134, 58, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
}

.badge-current {
  font-size: 11px;
  color: #2e7d6e;
  background: rgba(46, 125, 110, 0.12);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.btn-switch-source {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  border: 1px solid var(--color-accent, #b8863a);
  background: var(--color-accent, #b8863a);
  color: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-switch-source:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-switch-source:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-switch-source.btn-using {
  background: transparent;
  color: #2e7d6e;
  border-color: rgba(46, 125, 110, 0.4);
}

.candidate-book-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.candidate-title {
  font-weight: 600;
  color: inherit;
}

.candidate-author {
  font-size: 12px;
  color: #888;
}

.candidate-intro {
  font-size: 12px;
  color: #777;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ─── 动效 ────────────────────────────────────────────────── */
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: opacity 0.25s, transform 0.25s;
}

.drawer-slide-enter-from,
.drawer-slide-leave-to {
  opacity: 0;
}

.drawer-slide-enter-from .qd-toc-drawer,
.drawer-slide-leave-to .qd-toc-drawer {
  transform: translateX(-100%);
}

.drawer-slide-enter-active .qd-toc-drawer,
.drawer-slide-leave-active .qd-toc-drawer {
  transition: transform 0.25s ease-out;
}

.drawer-slide-right-enter-active,
.drawer-slide-right-leave-active {
  transition: opacity 0.25s, transform 0.25s;
}

.drawer-slide-right-enter-from,
.drawer-slide-right-leave-to {
  opacity: 0;
}

.drawer-slide-right-enter-from .qd-source-drawer,
.drawer-slide-right-leave-to .qd-source-drawer {
  transform: translateX(100%);
}

.drawer-slide-right-enter-active .qd-source-drawer,
.drawer-slide-right-leave-active .qd-source-drawer {
  transition: transform 0.25s ease-out;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>