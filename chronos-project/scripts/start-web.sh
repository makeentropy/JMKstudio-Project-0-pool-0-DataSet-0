#!/usr/bin/env bash
# ==========================================================
# CHRONOS · Web 启动脚本
# 在 /workspace/chronos-project/web 目录下启动静态文件服务器
# ==========================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$SCRIPT_DIR/../web"
PORT="${CHRONOS_WEB_PORT:-8000}"
HOST="${CHRONOS_WEB_HOST:-0.0.0.0}"

cd "$WEB_DIR"

echo "================================================"
echo "  CHRONOS Web (时空工作站 H5)"
echo "================================================"
echo "  目录    : $WEB_DIR"
echo "  地址    : http://localhost:$PORT"
echo "  LAN IP  : http://$(hostname -I 2>/dev/null | awk '{print $1}'):$PORT"
echo "  终止    : Ctrl+C"
echo "================================================"
echo

# 优先用 Python3 http.server
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m http.server "$PORT" --bind "$HOST"
elif command -v python >/dev/null 2>&1; then
  exec python -m http.server "$PORT" --bind "$HOST"
elif command -v busybox >/dev/null 2>&1; then
  exec busybox httpd -f -p "$PORT" -h "$WEB_DIR"
else
  echo "❌ 未找到 python3/python/busybox。请手动启动 Web 服务器："
  echo "   cd $WEB_DIR && python3 -m http.server $PORT"
  exit 1
fi
