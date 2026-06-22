#!/bin/bash
# baseXOR Snapshot Management Script
# Handles regular snapshots and data pair backup

set -e

SNAPSHOT_PATH="${POOL_PATH:-/pools}/snapshots"
POOL_PATH="${POOL_PATH:-/pools}"
CONFIG_PATH="$POOL_PATH/snapshot_config.json"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SNAPSHOT] $1"
}

load_config() {
    if [ -f "$CONFIG_PATH" ]; then
        INTERVAL=$(grep -o '"interval_seconds":[0-9]*' "$CONFIG_PATH" | grep -o '[0-9]*')
        RETENTION=$(grep -o '"retention_count":[0-9]*' "$CONFIG_PATH" | grep -o '[0-9]*')
        COMPRESSION=$(grep -o '"compression":"[^"]*"' "$CONFIG_PATH" | cut -d'"' -f4)
    fi
    
    INTERVAL="${INTERVAL:-3600}"
    RETENTION="${RETENTION:-24}"
    COMPRESSION="${COMPRESSION:-lz4}"
}

take_snapshot() {
    local snapshot_name="snapshot_$(date +%Y%m%d_%H%M%S)"
    local snapshot_dir="$SNAPSHOT_PATH/$snapshot_name"
    
    log "Taking snapshot: $snapshot_name"
    
    mkdir -p "$snapshot_dir"
    
    rsync -a --compress="${COMPRESSION}" "$POOL_PATH/" "$snapshot_dir/" 2>/dev/null || \
    cp -a "$POOL_PATH/" "$snapshot_dir/"
    
    echo "$snapshot_name" > "$snapshot_dir/snapshot_info.txt"
    echo "Created: $(date)" >> "$snapshot_dir/snapshot_info.txt"
    echo "Pool: $POOL_PATH" >> "$snapshot_dir/snapshot_info.txt"
    
    log "Snapshot created: $snapshot_dir"
    
    cleanup_old_snapshots
}

cleanup_old_snapshots() {
    log "Cleaning up old snapshots (retention: $RETENTION)"
    
    cd "$SNAPSHOT_PATH" || exit 1
    ls -dt snapshot_* 2>/dev/null | tail -n +$((RETENTION + 1)) | while read snap; do
        log "Removing old snapshot: $snap"
        rm -rf "$snap"
    done
}

data_pair_backup() {
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    local backup_dir="$SNAPSHOT_PATH/backup/$backup_name"
    
    log "Creating data pair backup: $backup_name"
    
    mkdir -p "$backup_dir"
    
    cp -a "$POOL_PATH/data" "$backup_dir/data_primary" 2>/dev/null || true
    cp -a "$POOL_PATH/meta" "$backup_dir/data_secondary" 2>/dev/null || true
    
    log "Data pair backup created: $backup_dir"
}

list_snapshots() {
    log "Available snapshots:"
    ls -lt "$SNAPSHOT_PATH"/snapshot_* 2>/dev/null || log "No snapshots found"
}

daemon_mode() {
    log "Starting snapshot daemon (interval: ${INTERVAL}s)"
    while true; do
        take_snapshot
        sleep "$INTERVAL"
    done
}

case "$1" in
    snap|take)
        load_config
        take_snapshot
        ;;
    backup)
        load_config
        data_pair_backup
        ;;
    list)
        list_snapshots
        ;;
    daemon)
        load_config
        daemon_mode
        ;;
    *)
        echo "Usage: $0 {snap|backup|list|daemon}"
        exit 1
        ;;
esac
