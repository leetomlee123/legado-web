# ==========================================
# Stage 1: Build Frontend (Node.js)
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install --registry=https://registry.npmmirror.com

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Backend Runtime
# ==========================================
FROM python:3.11-slim AS runner

# 设置时区与环境变量
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PORT=4388 \
    LEGADO_DATA=/app/data

WORKDIR /app

# 安装基础运行依赖（含 Node.js 供书源复杂 JS 沙箱及 dynamic AJAX 执行）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    curl \
    nodejs \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 

# 复制后端代码
COPY backend/ /app/

# 复制前端打包产物至 static dist 目录
COPY --from=frontend-builder /app/frontend/dist /app/dist

# 挂载数据与日志目录
VOLUME ["/app/data", "/app/logs"]

# 暴露端口
EXPOSE 4388

# 启动服务
CMD ["python", "main.py"]
