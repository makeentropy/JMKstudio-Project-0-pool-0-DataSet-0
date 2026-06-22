#!/bin/bash
# baseXOR Object Dev - Main Entry Point
# Boost container with XOR pool, AI LLM agent, TrueNAS, and snapshot support

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POOL_NAME="${POOL_NAME:-baseXOR_POOL}"
BOOST_DEVICE="${BOOST_DEVICE:-/dev/boost}"

show_banner() {
    cat << 'EOF'
    ================================================
         baseXOR-object-dev
         Quantum XOR Pool with AI LLM Agent
    ================================================
EOF
}

init_all() {
    echo "[*] Initializing baseXOR-object-dev..."
    
    echo "[*] Creating XOR pool..."
    bash "$SCRIPT_DIR/scripts/create_xor_pool.sh" init
    
    echo "[*] Initializing signal collection..."
    bash "$SCRIPT_DIR/scripts/collect_signals.sh" init
    
    echo "[*] Starting snapshot daemon..."
    bash "$SCRIPT_DIR/scripts/snapshot_manager.sh" daemon &
    
    echo "[*] baseXOR-object-dev initialization complete"
}

start_containers() {
    echo "[*] Starting Docker containers..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
    echo "[*] Containers started"
}

stop_containers() {
    echo "[*] Stopping Docker containers..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" down
    echo "[*] Containers stopped"
}

case "$1" in
    init)
        show_banner
        init_all
        ;;
    start)
        show_banner
        start_containers
        ;;
    stop)
        stop_containers
        ;;
    restart)
        stop_containers
        start_containers
        ;;
    pool-init)
        bash "$SCRIPT_DIR/scripts/create_xor_pool.sh" init
        ;;
    snap)
        bash "$SCRIPT_DIR/scripts/snapshot_manager.sh" snap
        ;;
    signal)
        bash "$SCRIPT_DIR/scripts/collect_signals.sh" start
        ;;
    status)
        echo "Pool: $POOL_NAME"
        echo "Boost Device: $BOOST_DEVICE"
        docker ps --filter "name=baseXOR" 2>/dev/null || echo "Docker not available"
        ;;
    *)
        echo "Usage: $0 {init|start|stop|restart|pool-init|snap|signal|status}"
        exit 1
        ;;
esac
