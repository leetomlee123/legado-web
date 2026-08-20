# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此仓库中的代码工作提供指导。

## 项目概述

这是一个基于Web的小说阅读器应用（Legado Web），将流行的安卓小说阅读器「阅读3.0 (Legado)」移植为浏览器端体验。

### 核心功能

- 支持 TXT/EPUB 书籍导入并自动解析章节
- 多源搜索（Web 书源占位符）
- 沉浸式阅读器，支持章节上下翻页、夜间模式、进度跟踪
- UI 模仿中文网络小说平台（紫色主题、卡片式书架、侧边栏导航）

### 架构与结构

项目分为前后端两部分：

**前端（Vue 3 + TypeScript）**
- Vite 构建系统，配置文件 `frontend/vite.config.ts`
- 使用 Vue Router 路由、Pinia 状态管理、Element Plus UI 组件
- 关键视图：
  - `BookcaseView.vue` —— 主书架界面
  - `SearchView.vue` —— 全局搜索
  - `ImportView.vue` —— 书籍导入
  - `ReadView.vue` —— 沉浸式章节阅读器
- API 层位于 `src/api/`
- 主题和布局在 `src/components/AppLayout.vue`

**后端（Go + chi）**
- 入口 `backend/golang/main.go`，路由库 `go-chi/chi/v5`
- SQLite（`backend/data/legado.db`，`modernc.org/sqlite`，无 CGO）
- TXT / EPUB / PDF 导入分别在 `book.go`、`epub.go`、`pdf.go`
- 书源规则引擎在 `source.go`（goquery）
- 旧 Node 实现仍保留在 `backend/*.js`，默认不再启动

前端在开发模式下代理到 `/api`（通过 Vite 配置）

## 开发命令

### 快速启动
```bash
./start.sh
```
- 同时启动前端开发服务器（http://localhost:5173）和后端（http://localhost:4388）
- 后端默认端口为 4388，可通过 `PORT=4388 ./start.sh` 修改

### 构建与开发
- **前端**：`cd frontend && npm run dev` （Vite 开发服务器）
- **后端**：`cd backend/golang && go run .` （默认 :4388）
- **旧 Node 后端**：`cd backend && node server.js`
- **生产构建**：`cd frontend && npm run build` （输出到 `dist/`）

### 测试
- 运行单个文件测试：`cd frontend && npm test <文件路径>`
- 运行所有测试：`cd frontend && npm test`
- 代码检查：`cd frontend && npm run lint`

### 其他脚本
- 每个目录下的 `npm run dev` 用于针对性开发
- `npm run build` 用于前端生产构建

## 其他说明

- 未找到 `.cursor/rules/` 或 `.cursorrules` 文件。
- 未检测到 OpenAI Codex 或 Gemini CLI 配置。
- README.md 内容已包含在概述中。
- 默认后端是 Go。保持 `/api` 路径与 JSON 字段与现有前端兼容。
```