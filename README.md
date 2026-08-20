# Legado Web （阅读 Web 版）

将安卓小说阅读器 **阅读3.0 (Legado)** 重构为 **Web 应用**，以最小可用版本交付。

## ✅ 已实现核心功能（最小目标）

| 功能 | 说明 | 状态 |
|------|------|------|
| **导入源** | 支持 TXT / EPUB / PDF 导入，自动解析章节 | ✅ |
| **搜索** | 全局多源搜索（Web 书源 `{search}` 占位符） | ✅ |
| **看书** | 沉浸式阅读器，章节上下翻页、夜间模式、进度 | ✅ |
| **界面** | 模仿阅文风格（紫色主色 + 卡片式书架 + 侧栏导航） | ✅ |

## 🚀 快速启动

```bash
# 一键启动（前端 + 后端）—— 推荐方式
./start.sh
```

**手动启动（推荐）**：

```bash
# 1. 前端
cd frontend && npm run dev

# 2. 后端（Python）
cd backend/python
pip install -r requirements.txt
python main.py
```

- 前端：http://localhost:5173 （Vite 代理 `/api` → 后端）
- 后端 API：http://localhost:4388

> 注：默认后端端口 **4388**。如被占用可通过 `PORT=4388 ./start.sh` 修改。

## 🏗️ 技术栈

- **前端**：Vue 3 + TypeScript + Pinia + Vue Router + Element Plus + Vite
- **后端**：Python + Flask + SQLite + curl_cffi（网络请求）
- **旧后端**：`backend/*.js`（Node + Express，仅作参考）
- **数据库**：SQLite（`backend/data/legado.db`）

## 📁 目录结构

```
legado-web/
├── start.sh              # 一键启动脚本（已更新）
├── frontend/             # Vue 3 + Vite 前端
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
├── backend/
    ├── python/           # Python Flask 后端（默认）
    │   ├── main.py
    │   ├── book.py
    │   ├── epub.py
    │   ├── pdf.py
    │   ├── source.py
    │   ├── db.py
    │   └── settings.py
    ├── server.js         # 旧 Node 后端（参考）
    ├── schema.sql
    └── data/legado.db
```

## 🔌 API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/books` | 书架列表 |
| GET | `/api/books/:id` | 书籍详情 |
| GET | `/api/books/:id/chapters` | 章节列表 |
| GET | `/api/books/:id/chapters/:cid/content` | 章节内容 |
| GET | `/api/books/:id/cover` | 封面 |
| POST | `/api/books/import/txt` | 导入 TXT |
| POST | `/api/books/import/epub` | 导入 EPUB |
| POST | `/api/books/import/pdf` | 导入 PDF |
| GET/POST/PUT/DELETE | `/api/sources[/:id]` | 书源管理 |
| GET | `/api/search/all` | 多源搜索 |
| GET/POST | `/api/settings` | 代理设置 |

## 🎯 后续可扩展

- 书源导入导出
- 阅读进度自动保存
- 网络书章节按需抓取
- PDF 渲染
- PWA 安装

## 常见问题

### npm run dev 报错

**最可能原因**：`start.sh` 自动安装前端依赖失败导致 `node_modules` 缺失。

**解决步骤**：

1. **手动安装前端依赖**（在 `frontend` 目录下）：
   ```bash
   cd frontend
   npm install
   ```

2. **启动前端**：
   ```bash
   cd frontend
   npm run dev
   ```

3. **后端**（Python）：
   ```bash
   cd backend/python
   pip install -r requirements.txt
   python main.py
   ```

### 其他常见报错

- **端口被占用**：
  ```bash
  PORT=4388 ./start.sh
  ```

- **后端启动失败**（`main.py` 错误）：
  ```bash
  cd backend/python
  python main.py
  ```

- **前端代理失败**：
  确保后端已启动后再打开前端。

---

**更新说明**：`start.sh` 已更新为支持 Python 后端 + 虚拟环境 + 一键启动。`README.md` 已同步更新。

现在请按**手动启动步骤**运行，确保 `npm install` 成功后再 `npm run dev`。 

需要我再更新其他文件（如 `.env`、Dockerfile、CI 配置）吗？