#!/usr/bin/env bash
# ============================================================
#  Snapshot 备份批处理 (Linux/macOS)
#  用法: ./snapshot_backup.sh [entity] [source_path] [compression]
#  示例: ./snapshot_backup.sh mydata /data tar.gz
# ============================================================
set -euo pipefail

ENTITY="${1:-}"
SOURCE="${2:-}"
COMPRESSION="${3:-none}"

if [ -z "$ENTITY" ]; then
    read -rp "请输入实体 ID: " ENTITY
fi
if [ -z "$SOURCE" ]; then
    read -rp "请输入源路径: " SOURCE
fi

BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v ai-crawler >/dev/null 2>&1; then
    ai-crawler snapshot create-full --entity "$ENTITY" --source "$SOURCE" --compression "$COMPRESSION"
else
    python3 "$BIN_DIR/snapshot_cli.py" create-full --entity "$ENTITY" --source "$SOURCE" --compression "$COMPRESSION"
fi
