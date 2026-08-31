# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此仓库中的代码工作提供指导。

## 项目概述

这是一个基于Web的小说阅读器应用（Legado Web），将流行的安卓小说阅读器「阅读3.0 (Legado)」移植为浏览器端体验。

### 核心功能

- 支持 TXT/EPUB/PDF 书籍导入并自动解析章节
- 多源搜索（SSE 流式推送，深度兼容阅读 3.0 书源协议）
- 沉浸式阅读器：章节上下翻页、夜间模式、起点风格 7 套配色、排版控制、进度跟踪、键盘翻页
- 书源定时追更刷新、健康度巡检、全局网络代理
- 书源探索（exploreUrl 分类榜单）
- 文本转语音（TTS）悬浮播放器
- PWA 离线缓存（service worker）

## 架构与结构

项目分为前后端两部分：

**前端（Vue 3 + TypeScript + Vite）**
- 构建系统配置文件 `frontend/vite.config.ts`，开发时代理 `/api` 到后端
- 使用 Vue Router 路由、Pinia 状态管理、Element Plus UI 组件
- 关键视图（`frontend/src/views/`）：
  - `BookcaseView.vue` —— 主书架界面
  - `ReadView.vue` —— 沉浸式章节阅读器（含 TTS、目录、换源、排版）
  - `SearchView.vue` —— 多源流式搜索
  - `ExploreView.vue` —— 书源探索与分类榜单
  - `SourceView.vue` —— 书源管理
  - `ImportView.vue` —— 书源与书籍导入
  - `SettingsView.vue` —— 定时刷新、代理与系统设置
  - `LogsView.vue` —— 运行日志
  - `BookDetailView.vue` —— 书籍详情
- API 层位于 `frontend/src/api/`

**后端（Python Flask）**
- 入口 `backend/main.py`，框架 `Flask`，数据库 `SQLite`
  - HTTP 客户端用 `curl_cffi`（模拟 Chrome TLS/JA3/JA4 握手），解析用 bs4/lxml
  - TXT / EPUB / PDF 导入分别在 `book.py`、`epub.py`、`pdf.py`
  - 书源规则引擎在 `source.py`（兼容 JSONPath / XPath / CSS / 正则 / JS 沙箱 / java.ajax）
  - 定时追更调度在 `bookshelf_refresh.py`，健康巡检在 `health.py`
  - 系统参数与网络代理在 `settings.py`，数据库在 `db.py`
- 前端构建产物输出到 `dist/`，由后端 `mount_frontend()` 作为 SPA 静态托管

## 开发命令

### 快速启动（本地开发，前端热更新）
```bash
./start.sh
```
- 同时准备前端依赖、Python 虚拟环境，启动 Python 后端（默认 :4388）与 Vite 开发服务器（http://localhost:5173）
- 后端端口可用 `PORT=4388 ./start.sh` 修改

### 构建与开发
- **前端开发**：`cd frontend && npm run dev` （Vite 开发服务器，:5173）
- **前端类型检查 + 构建**：`cd frontend && npm run build` （先 `vue-tsc --noEmit` 再 `vite build`，产物在 `dist/`）
- **预览产物**：`cd frontend && npm run preview`
- **后端**：`cd backend && source .venv/bin/activate && PORT=4388 python main.py` （默认 :4388）

### Python 后端单元测试
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
pytest test_book.py test_legado_rule.py -v
```
前端当前**没有**测试框架或 lint 脚本（`package.json` 仅含 dev/build/preview）。

### 生产构建（Docker）
```bash
docker compose build && docker compose up -d
```
> **重要**：前端静态资源在镜像内多阶段构建时复制（`COPY --from=frontend-builder /app/frontend/dist /app/dist`）。
> 改完前端后需 `docker compose build` 并重启容器才会生效；仅重建宿主机 `frontend/dist` 不会进入运行中的镜像。

## 其他说明

- 本仓库后端为 **Python（Flask）** 实现。历史 CLAUDE.md 中「Go + chi」「`backend/golang`」「Node 后端」「source.go（goquery）」等描述均已过时，请勿据此操作。
- 保持 `/api` 路径与 JSON 字段与现有前端兼容。
- 阅读器正文段落、目录单元格的悬浮底色规则位于 `frontend/src/views/ReadView.vue` 的样式段。