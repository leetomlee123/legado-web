# 🚀 Legado Web Docker 容器化部署指南

本项目采用 **Node.js (前端打包) + Python (轻量运行时)** 的多阶段构建方案，将前后端合为一个独立、高效、低资源占用的 Docker 镜像。

---

## 目录
- [一、快速一键启动（推荐）](#一快速一键启动推荐)
- [二、目录挂载与数据持久化](#二目录挂载与数据持久化)
- [三、Docker Compose 常用管理命令](#三docker-compose-常用管理命令)
- [四、Nginx 反向代理与 SSL (HTTPS) 配置](#四nginx-反向代理与-ssl-https-配置)
- [五、Caddy 反代配置示例](#五caddy-反代配置示例)
- [六、常见问题与日常维护](#六常见问题与日常维护)

---

## 一、快速一键启动（推荐）

### 1. 克隆代码仓库并进入根目录
```bash
git clone https://github.com/leetomlee123/legado-web.git
cd legado-web
```

### 2. 使用 Docker Compose 构建并启动
```bash
# 首次构建镜像并在后台运行服务
docker compose up -d --build
```

启动完成后，打开浏览器访问：
👉 **http://localhost:8081** 即可开始使用！

---

## 二、目录挂载与数据持久化

在 `docker-compose.yaml` 中，已配置宿主机与容器的数据卷映射：

```yaml
volumes:
  # 持久化 SQLite 数据库与书籍文件（TXT/EPUB/PDF/封面图片）
  - ./data:/app/data
  # 持久化运行日志与错误排查日志
  - ./logs:/app/logs
```

> [!TIP]
> **日常数据备份**：如需迁移服务器或备份书架与书源，只需打包项目根目录下的 `./data` 文件夹即可完整迁移。

---

## 三、Docker Compose 常用管理命令

```bash
# 1. 查看容器运行状态与健康检查
docker compose ps

# 2. 查看实时运行日志
docker compose logs -f

# 3. 停止服务
docker compose stop

# 4. 重启服务
docker compose restart

# 5. 代码更新后重新拉取并重构上线
git pull
docker compose up -d --build

# 6. 完全停止并删除容器
docker compose down
```

---

## 四、Nginx 反向代理与 SSL (HTTPS) 配置

> [!IMPORTANT]
> 由于 Legado Web 采用了 **SSE (Server-Sent Events)** 技术来实现小说流式多源并发搜索与实时日志推流，在 Nginx 配置中必须加入 `proxy_buffering off;` 和 `proxy_cache off;`，否则推流会被 Nginx 缓冲导致卡顿或延时。

### 推荐 Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name reader.yourdomain.com;
    # 强制跳转 HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name reader.yourdomain.com;

    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/reader.yourdomain.com.crt;
    ssl_certificate_key /etc/nginx/ssl/reader.yourdomain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 客户端上传文件限制（支持大体积 TXT / EPUB / PDF 导入）
    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # ── 关键配置：支持 SSE 流式多源搜索与实时日志 ──
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
```

---

## 五、Caddy 反代配置示例

如果使用 Caddy 2 作为反向代理，只需在 `Caddyfile` 中配置：

```caddyfile
reader.yourdomain.com {
    reverse_proxy 127.0.0.1:8081 {
        transport http {
            read_timeout 600s
        }
    }
}
```

---

## 六、常见问题与日常维护

### 1. 无法连接宿主机的 Clash / v2ray 代理？
- 若代理运行在宿主机（如 `127.0.0.1:7890`），在容器内部请填写宿主机局域网 IP 或 `http://host.docker.internal:7890`（可在设置页面点击 **「⚡ 测试代理连接」** 校验连通性）。

### 2. 搜索慢或部分书源超时？
- 在 **设置** 页面将「请求超时时间」调整为 `5~10 秒`；
- 在 **书源管理** 页面点击 **「⚡ 批量测速」**，将显示超时的书源一键禁用或删除。

### 3. 如何修改访问端口？
- 修改 `docker-compose.yaml` 中的 `ports`，例如将 `"8081:8081"` 改为 `"9090:8081"`，然后执行 `docker compose up -d` 即可。
