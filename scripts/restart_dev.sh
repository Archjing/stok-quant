#!/usr/bin/env bash
# 重启前后端（Linux / WSL）
# 用法：
#   bash scripts/restart_dev.sh
# 可选环境变量：
#   BACKEND_PORT=8777 FRONTEND_PORT=5173 FRONTEND_HOST=0.0.0.0

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/log"
BACKEND_PORT="${BACKEND_PORT:-8777}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"

mkdir -p "$RUN_DIR" "$LOG_DIR"

kill_by_port() {
  local port="$1"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  elif command -v ss >/dev/null 2>&1; then
    pids="$(ss -lptn "sport = :$port" 2>/dev/null | awk -F'pid=' 'NF>1{split($2,a,","); print a[1]}' | sort -u || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp "$port" 2>/dev/null || true)"
  fi

  if [[ -n "${pids// }" ]]; then
    echo "[stop] 结束端口 $port 上的进程: $pids"
    # shellcheck disable=SC2086
    kill -9 $pids || true
  else
    echo "[stop] 端口 $port 无需清理"
  fi
}

start_backend() {
  echo "[start] 后端启动中..."
  cd "$ROOT_DIR"
  nohup uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$LOG_DIR/backend.dev.log" 2>&1 &
  echo $! > "$RUN_DIR/backend.pid"
  echo "[ok] backend pid=$(cat "$RUN_DIR/backend.pid") log=$LOG_DIR/backend.dev.log"
}

start_frontend() {
  echo "[start] 前端启动中..."
  cd "$ROOT_DIR/frontend"
  nohup npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
    > "$LOG_DIR/frontend.dev.log" 2>&1 &
  echo $! > "$RUN_DIR/frontend.pid"
  echo "[ok] frontend pid=$(cat "$RUN_DIR/frontend.pid") log=$LOG_DIR/frontend.dev.log"
}

echo "============================================"
echo "  Restart Dev Services (Backend + Frontend)"
echo "============================================"

echo "[1/3] 停止旧服务"
kill_by_port "$BACKEND_PORT"
kill_by_port "$FRONTEND_PORT"

echo "[2/3] 启动后端"
start_backend

echo "[3/3] 启动前端"
start_frontend

echo
echo "完成："
echo "- Backend : http://127.0.0.1:$BACKEND_PORT"
echo "- Frontend: http://127.0.0.1:$FRONTEND_PORT"
echo
echo "查看日志："
echo "- tail -f $LOG_DIR/backend.dev.log"
echo "- tail -f $LOG_DIR/frontend.dev.log"
