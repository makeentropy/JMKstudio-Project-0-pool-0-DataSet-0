#!/usr/bin/env bash
# ============================================================
#  Snapshot 恢复批处理 (Linux/macOS)
#  用法: ./snapshot_recover.sh [entity] [snapshot_id] [output_path]
# ============================================================
set -euo pipefail

ENTITY="${1:-}"
SNAP_ID="${2:-}"
OUTPUT="${3:-}"

if [ -z "$ENTITY" ]; then read -rp "请输入实体 ID: " ENTITY; fi
if [ -z "$SNAP_ID" ]; then read -rp "请输入快照 ID: " SNAP_ID; fi
if [ -z "$OUTPUT" ]; then read -rp "请输入输出路径: " OUTPUT; fi

BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v ai-crawler >/dev/null 2>&1; then
    ai-crawler snapshot restore --entity "$ENTITY" --id "$SNAP_ID" --out "$OUTPUT"
else
    python3 "$BIN_DIR/snapshot_cli.py" restore --entity "$ENTITY" --id "$SNAP_ID" --out "$OUTPUT"
fi
