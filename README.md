# Legado Web （阅读 Web 版）

将安卓小说阅读器 **阅读3.0 (Legado)** 重构为 **Web 应用**，以最小可用版本交付。

## ✅ 已实现核心功能（最小目标）

| 功能 | 说明 | 状态 |
|------|------|------|
| **导入源** | 支持 TXT / EPUB 导入，自动解析章节 | ✅ |
| **搜索** | 全局多源搜索（Web 书源 `{search}` 占位） | ✅ |
| **看书** | 沉浸式阅读器，章节上下翻页、夜间模式、进度 | ✅ |
| **界面** | 模仿阅文风格（紫色主色 + 卡片式书架 + 侧栏导航） | ✅ |

## 🚀 快速启动

```bash
# 一键启动（前端 + 后端）
./start.sh
```

- 前端开发服：http://localhost:5173 （Vite 代理 `/api` → 后端）
- 后端 API：http://localhost:8081

> 注：默认后端端口 **8081**（8080 常被占用）。可通过 `PORT=8081 ./start.sh` 修改。

## 🏗️ 技术栈

- **前端**：Vue 3 + TypeScript + Pinia + Vue Router + Element Plus + Vite
- **后端**：Go + chi + SQLite（`modernc.org/sqlite`，无 CGO）
- **旧后端**：`backend/*.js`（Node + Express，仅作参考）
- **数据库**：SQLite（`backend/data/legado.db`，自动初始化）

## 📁 目录结构

```
legado-web/
├── start.sh              # 一键启动脚本
├── frontend/
│   ├── src/
│   │   ├── api/          # API 封装
│   │   ├── components/   # AppLayout（阅文风格壳）
│   │   ├── views/
│   │   │   ├── BookcaseView.vue   # 书架
│   │   │   ├── SearchView.vue     # 搜索
│   │   │   ├── ImportView.vue     # 导入
│   │   │   └── ReadView.vue       # 阅读器
│   │   ├── router/       # 路由
│   │   ├── stores/       # Pinia
│   │   └── types/        # TS 类型
│   └── vite.config.ts
└── backend/
    ├── golang/           # 默认后端（Go + chi）
    │   ├── main.go
    │   ├── handlers.go
    │   ├── book.go / epub.go / pdf.go
    │   └── source.go
    ├── server.js         # 旧 Node 入口（参考）
    ├── schema.sql
    └── data/legado.db    # 共用 SQLite
```

## 🔌 API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/books` | 书架列表（keyword/group/page） |
| GET | `/api/books/:id` | 书籍详情 |
| GET | `/api/books/:id/chapters` | 章节列表 |
| GET | `/api/books/:id/chapters/:cid/content` | 章节内容 |
| GET | `/api/books/:id/cover` | 封面/占位图 |
| POST | `/api/books/import/txt` | 导入 TXT |
| POST | `/api/books/import/epub` | 导入 EPUB |
| POST | `/api/books/import/pdf` | 导入 PDF |
| DELETE | `/api/books/:id` | 删除书籍 |
| GET/POST/PUT/DELETE | `/api/sources[/:id]` | 书源管理 |
| POST | `/api/sources/import` | 订阅 URL 导入书源 |
| GET | `/api/search/all` | 多源搜索 |

## 🎯 后续可扩展

- 书源导入导出（Json / 订阅链接）
- 阅读进度自动保存、历史记录
- 网络书章节按需抓取（jsoup + xpath 规则）
- PDF 渲染、远程同步（WebDAV）
- PWA 安装、离线缓存