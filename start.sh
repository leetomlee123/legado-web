#!/usr/bin/env bash
# 启动 Legado Web（Vue 前端 + Python 后端）
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8081}"

echo "📦 安装前端依赖..."
(cd "$ROOT/frontend" && npm install)

echo "🐍 准备 Python 虚拟环境..."
VENV="$ROOT/backend/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -r "$ROOT/backend/requirements.txt"

echo "📚 启动 Python 后端 (端口 $PORT)..."
(cd "$ROOT/backend" && PORT="$PORT" "$VENV/bin/python" main.py) &
BACK_PID=$!
trap "kill $BACK_PID 2>/dev/null" EXIT

sleep 1.5
echo "🖥️  启动前端 dev server http://localhost:5173 ..."
(cd "$ROOT/frontend" && npm run dev)
