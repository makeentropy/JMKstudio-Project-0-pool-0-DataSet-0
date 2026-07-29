#!/usr/bin/env bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
  echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

confirm_action() {
  local message="$1"
  local default="${2:-y}"
  local prompt

  if [ "$default" = "y" ]; then
    prompt="[Y/n]"
  else
    prompt="[y/N]"
  fi

  read -r -p "$message $prompt " response
  response="${response:-$default}"

  case "$response" in
    [yY][eE][sS]|[yY])
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

wait_for_service() {
  local host="$1"
  local port="$2"
  local timeout="${3:-30}"
  local start_time
  start_time=$(date +%s)

  log_info "等待服务 ${host}:${port} 就绪（超时: ${timeout}秒）..."

  while true; do
    local current_time
    current_time=$(date +%s)
    local elapsed=$((current_time - start_time))

    if [ "$elapsed" -ge "$timeout" ]; then
      log_error "服务 ${host}:${port} 在 ${timeout} 秒内未就绪"
      return 1
    fi

    if command -v nc >/dev/null 2>&1; then
      if nc -z -w 2 "$host" "$port" >/dev/null 2>&1; then
        log_success "服务 ${host}:${port} 已就绪"
        return 0
      fi
    elif command -v bash >/dev/null 2>&1; then
      if (echo > /dev/tcp/"$host"/"$port") >/dev/null 2>&1; then
        log_success "服务 ${host}:${port} 已就绪"
        return 0
      fi
    else
      log_error "未找到 nc 或 bash 的 /dev/tcp 支持，无法检测服务状态"
      return 1
    fi

    sleep 1
  done
}

generate_password() {
  local length="${1:-32}"
  local password

  if command -v openssl >/dev/null 2>&1; then
    password=$(openssl rand -base64 "$((length * 3 / 4))" | tr -d '\n' | tr -d '=' | tr '+/' '-_')
    if [ "${#password}" -lt "$length" ]; then
      password="${password}$(openssl rand -base64 32 | tr -d '\n' | tr -d '=' | tr '+/' '-_')"
    fi
    password="${password:0:$length}"
  else
    password=$(LC_ALL=C tr -dc 'A-Za-z0-9!@#$%^&*()_+-=' </dev/urandom | head -c "$length")
  fi

  echo "$password"
}

file_size_human() {
  local bytes="$1"

  if [ "$bytes" -lt 1024 ]; then
    echo "${bytes} B"
  elif [ "$bytes" -lt 1048576 ]; then
    echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1024}") KB"
  elif [ "$bytes" -lt 1073741824 ]; then
    echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1048576}") MB"
  else
    echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1073741824}") GB"
  fi
}

export RED GREEN YELLOW BLUE CYAN NC
