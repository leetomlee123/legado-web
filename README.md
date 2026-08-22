<div align="center">

# 📚 Legado Web

**开源阅读 3.0 Web 现代化重构版**

*基于「开源阅读 3.0 (Legado)」书源协议的现代 Web 端小说阅读器与书源管理平台*

[![Vue 3](https://img.shields.io/badge/Vue-3.4+-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue?style=flat-square)](LICENSE)

[在线体验](#-快速部署) · [功能特性](#-核心特性) · [快速开始](#-快速开始) · [架构设计](#-架构与目录结构) · [常见问题](#-常见问题)

</div>

---

## 📖 项目简介

**Legado Web** 是一款为浏览器、平板、折叠屏及桌面端打造的现代化小说阅读平台。它深度兼容 **开源阅读 3.0 (Legado)** 的书源规则协议，彻底摆脱原生移动 App 限制，让你在任何具备现代浏览器的设备上，都能享受纯净无广告、秒开秒读、排版典雅的书籍阅读体验。

---

## ✨ 核心特性

### 1. 🎨 起点级沉浸式阅读器（精准对标起点中文网）
- **双层画布架构**：外层桌面桌布 (`canvasBg`) 与内层书籍白纸卡片 (`pageBg`) 分离，还原真实纸张阅读质感与微立体阴影。
- **7 套官方经典配色**：
  - 经典纸白（起点官方默认，象牙纸色柔和护眼）
  - 羊皮纸（温暖复古微黄）
  - 护眼绿（淡雅青草绿，舒缓眼疲劳）
  - 雅致蓝（莫兰迪冷灰蓝）
  - 胭脂粉（温馨淡粉）
  - 纯净白（高对比极简白）
  - 夜间黑（暗光环境下深灰防刺眼）
- **起点经典右侧悬浮 Dock 工具栏**：目录抽屉、一键换源、原网页直达、加入书架、日夜间一键切换、排版设置、一键回到顶部。
- **精细化排版控制**：正文字号 (14~28px)、行间距 (1.4~2.6)、黑体/宋体/楷体切换、版面宽度 (640~1280px / 自适应宽度)。
- **极致流畅秒开**：
  - 会话级目录高速缓存 (`sessionStorage`) 与本地进度即时就绪 (`localStorage`)，杜绝每次进入阅读页的全屏加载遮罩。
  - 前后相邻章节静默预加载技术，翻页零等待。
  - 支持键盘左右方向键快捷翻页。

### 2. ⚡ 全网流式多源并发搜索
- **SSE (Server-Sent Events) 流式推送**：搜索词发出后，各书源检索结果先搜先出、逐源毫秒级推送，无需等待全网搜完。
- **高并发线程池检索**：支持 1~32 并发线程自定义配置。
- **智能去重与同名书聚合**：自动聚合不同书源的同名同作者书籍，快速对比各源最新章节与更新时间。
- **即时中断响应**：支持前端主动终止检索，后台线程池即刻取消未完成的书源网络请求，节省网络与算力。

### 3. 🧩 全能书源规则解析引擎
- **全格式书源导入**：支持网络 URL 导入、本地 JSON 文件上传、规则文本粘贴与内置精品书源预设。
- **原生兼容阅读 3.0 复杂规则**：
  - JSONPath（含 `$..content` 递归与多字段 `||` 回退兜底）
  - XPath 3.0
  - CSS Selector（支持 `@text`, `@html`, `@attr` 等属性提取）
  - Regular Expression 正则清洗与替换
  - `<js>` / `@js:` V8 沙箱脚本执行
  - `java.ajax()` 动态异步请求与复杂章节 Token 解密管道
- **反爬对抗与浏览器指纹模拟**：集成 `curl_cffi` 完整模拟 Chrome 120 TLS/JA3/JA4 握手特征，绕过绝大部分 Cloudflare / WAF 基础拦截。

### 4. 🔄 书架管理与定时追更引擎
- **定时自动刷新书架章节**：
  - 后台多线程定时静默轮询书架中所有网络书籍目录。
  - 智能增量合并：刷新目录时自动保留已下载缓存的正文数据。
  - 发现新章节自动打上“新”字更新红点提醒。
- **设置页可视化定时配置**：
  - 支持快捷切换周期：`30分钟`、`1小时`、`2小时`、`6小时 (推荐)`、`12小时`、`24小时 (每天一次)`。
  - 实时展示书架网文总数、更新书籍数、新增章节数及手动“⚡ 立即刷新书架章节”进度条。
- **书架操作**：支持网文/本地书籍筛选、多选批量移出、素净优雅书封与文字书脊保底。

### 5. 🩺 书源健康度定时巡检
- 后台周期性静默探测全部书源的连通性与响应速度（🟢 健康 `<1.2s`、🟡 迟缓 `>1.2s`、🔴 失效/超时）。
- 支持「自动隔离失效书源」开关与一键批量禁用/清理失效源。

### 6. 🧭 探索与发现
- 完美解析书源内的 `exploreUrl` 规则。
- 动态呈现玄幻、修真、都市、科幻等多级分类榜单与热门推荐。

### 7. 🌐 全局网络代理与出口测试
- 支持配置 HTTP / HTTPS / SOCKS5 全局网络代理。
- 内置一键代理连通性、出口 IP 与网络延迟测试工具。

---

## 🚀 快速开始

### 方式一：Docker Compose 一键部署（推荐）

#### 1. 编写 `docker-compose.yml`

```yaml
version: "3.8"

services:
  legado-web:
    image: leetomlee123/legado-web:latest
    container_name: legado-web
    restart: unless-stopped
    ports:
      - "4388:4388"
    volumes:
      # 持久化数据库与导入书籍、封面缓存
      - ./data:/app/data
      # 持久化系统运行日志
      - ./logs:/app/logs
    environment:
      - PORT=4388
      - LEGADO_DATA=/app/data
      - TZ=Asia/Shanghai
```

#### 2. 启动服务

```bash
docker compose up -d
```

服务启动后，在浏览器访问 `http://localhost:4388` 即可开始使用。

---

### 方式二：Docker CLI 直接运行

```bash
docker run -d \
  --name legado-web \
  --restart unless-stopped \
  -p 4388:4388 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e TZ=Asia/Shanghai \
  leetomlee123/legado-web:latest
```

---

### 方式三：本地源码开发与构建

#### 环境要求
- **Node.js**: >= 18.0.0
- **Python**: >= 3.10
- **npm** 或 **pnpm**

#### 1. 克隆代码仓库
```bash
git clone https://github.com/leetomlee123/legado-web.git
cd legado-web
```

#### 2. 前端构建
```bash
cd frontend
npm install
npm run build
cd ..
```

#### 3. 后端启动
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 将前端静态构建产物挂载并启动应用
PORT=4388 python main.py
```

访问 `http://localhost:4388` 即可体验完整功能。

---

## 🛠️ 环境变量与配置

| 环境变量 | 默认值 | 描述 |
| :--- | :--- | :--- |
| `PORT` | `4388` | 服务监听端口 |
| `LEGADO_DATA` | `/app/data` | 数据持久化目录（存储 SQLite 数据库、缓存文件、封面等） |
| `TZ` | `Asia/Shanghai` | 容器时区配置 |

---

## 📂 架构与目录结构

```text
legado-web/
├── backend/                  # Python 后端服务
│   ├── main.py               # REST API 路由、SSE 流式推送与 SPA 静态托管
│   ├── source.py             # 阅读 3.0 书源规则解析引擎与网络抓取核心
│   ├── bookshelf_refresh.py  # 书架章节定时自动刷新与增量追更调度器
│   ├── health.py             # 书源健康度巡检引擎
│   ├── settings.py           # 系统参数持久化与网络代理管理
│   ├── requirements.txt      # 后端依赖列表 (curl_cffi, flask, etc.)
│   └── schema.sql            # SQLite 数据库表结构
├── frontend/                 # Vue 3 现代化前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── BookcaseView.vue   # 书架管理视图
│   │   │   ├── ReadView.vue       # 起点风格核心阅读器
│   │   │   ├── SearchView.vue     # 多源流式搜索视图
│   │   │   ├── ExploreView.vue    # 书源探索与分类榜单
│   │   │   ├── SourceView.vue     # 书源列表、管理与测速
│   │   │   ├── ImportView.vue     # 书源与本地书籍导入
│   │   │   ├── SettingsView.vue   # 定时刷新、代理与系统设置
│   │   │   └── LogsView.vue       # 系统实时日志控制台
│   │   ├── api/                   # HTTP / SSE 接口客户端
│   │   ├── utils/                 # 书封渲染、主题与文本工具
│   │   └── router/                # 页面路由配置
│   ├── package.json
│   └── vite.config.ts
├── Dockerfile                # 多阶段轻量化 Docker 构建文件
├── docker-compose.yml        # Docker Compose 生产部署配置
└── README.md
```

---

## ❓ 常见问题

### Q1: 书源从哪里获取？
> 本系统完全兼容开源阅读 3.0 (Legado) 的书源格式（JSON）。你可以直接从网络上各大开源书源仓库导入书源 URL，或导入本地保存的 `bookSource.json` 文件。系统内置了常用公共精品源供一键导入。

### Q2: 为什么有些书源在其他平台打不开，在 Legado Web 可以正常阅读？
> Legado Web 使用了 `curl_cffi` 作为底层网络引擎，在发起 HTTP 请求时能够精准伪装真实 Chrome 浏览器最新的 TLS/JA3 指纹与 HTTP/2 特征；同时集成了 Node.js V8 沙箱引擎，完整支持书源中的复杂动态 Token 运算和 `java.ajax` 解密。

### Q3: 从书架点击阅读时会卡顿吗？
> 不会。系统引入了会话级目录缓存（SessionStorage）与本地阅读进度即时就绪技术，点击书籍瞬间直接呈现阅读界面，并在后台进行并发静默校准。

---

## 📄 开源协议与致谢

- 本项目基于 [GPL-3.0 License](LICENSE) 协议开源。
- 感谢 [开源阅读 (Legado)](https://github.com/gedoor/legado) 及其开源社区在小说书源生态建设中的卓越贡献。

---

<div align="center">
  <sub>Made with ❤️ for book lovers everywhere.</sub>
</div>
