#!/usr/bin/env bash
# ==========================================================
# CHRONOS · CLI 启动脚本  (Linux / macOS / Termux)
# ==========================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_FILE="$SCRIPT_DIR/../cli/chronos_cli.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ 未找到 python3，请先安装 (pkg install python in Termux)"
  exit 1
fi

exec python3 "$CLI_FILE" "$@"
