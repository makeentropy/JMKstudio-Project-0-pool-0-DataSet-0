#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=./utils.sh
source "${SCRIPT_DIR}/utils.sh"

detect_os() {
  local os
  os=$(uname -s)
  case "$os" in
    Linux*)
      if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "${ID:-}" in
          ubuntu|debian|linuxmint|pop)
            echo "ubuntu"
            ;;
          centos|rhel|fedora|rocky|almalinux)
            echo "centos"
            ;;
          *)
            echo "linux"
            ;;
        esac
      else
        echo "linux"
      fi
      ;;
    Darwin*)
      echo "mac"
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

install_system_deps_ubuntu() {
  log_info "检测到 Ubuntu/Debian 系统，安装系统依赖..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq curl git build-essential python3

  if ! command -v redis-server >/dev/null 2>&1; then
    if confirm_action "是否安装 redis-server？" "n"; then
      sudo apt-get install -y -qq redis-server
    fi
  fi

  if ! command -v docker >/dev/null 2>&1; then
    log_warn "未检测到 Docker，请手动安装: https://docs.docker.com/engine/install/"
  else
    log_info "Docker 已安装: $(docker --version)"
  fi

  if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
    log_warn "未检测到 Docker Compose，请手动安装"
  else
    log_info "Docker Compose 已安装"
  fi
}

install_system_deps_centos() {
  log_info "检测到 CentOS/RHEL 系统，安装系统依赖..."
  sudo yum install -y -q curl git gcc gcc-c++ make python3

  if ! command -v redis-server >/dev/null 2>&1; then
    if confirm_action "是否安装 redis-server？" "n"; then
      sudo yum install -y -q redis
    fi
  fi

  if ! command -v docker >/dev/null 2>&1; then
    log_warn "未检测到 Docker，请手动安装: https://docs.docker.com/engine/install/"
  else
    log_info "Docker 已安装: $(docker --version)"
  fi

  if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
    log_warn "未检测到 Docker Compose，请手动安装"
  else
    log_info "Docker Compose 已安装"
  fi
}

install_system_deps_mac() {
  log_info "检测到 macOS 系统..."
  if ! command -v brew >/dev/null 2>&1; then
    log_warn "未检测到 Homebrew，请先安装: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    return 0
  fi

  log_info "使用 Homebrew 安装系统依赖..."
  brew install curl git python3 2>/dev/null || true

  if ! command -v redis-server >/dev/null 2>&1; then
    if confirm_action "是否安装 redis-server？" "n"; then
      brew install redis 2>/dev/null || true
    fi
  fi

  if ! command -v docker >/dev/null 2>&1; then
    log_warn "未检测到 Docker Desktop for Mac，请从 https://www.docker.com/products/docker-desktop/ 安装"
  else
    log_info "Docker 已安装: $(docker --version)"
  fi
}

check_nodejs() {
  log_info "检查 Node.js 版本..."

  if ! command -v node >/dev/null 2>&1; then
    log_error "未检测到 Node.js"
    if [ -d "${HOME}/.nvm" ] || command -v nvm >/dev/null 2>&1; then
      log_info "检测到 nvm，尝试使用 nvm 安装 Node.js v18 LTS..."
      export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
      [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
      nvm install 18 || true
      nvm use 18 || true
    else
      log_warn "请手动安装 Node.js v18 或更高版本"
      log_warn "下载地址: https://nodejs.org/"
      log_warn "或使用 nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
      return 1
    fi
  fi

  local node_version
  node_version=$(node --version 2>/dev/null || echo "v0.0.0")
  local major_version
  major_version=$(echo "$node_version" | sed 's/^v//' | cut -d. -f1)

  if [ "$major_version" -ge 18 ]; then
    log_success "Node.js 版本符合要求: $node_version"
  else
    log_error "Node.js 版本过低: $node_version，需要 v18 或更高版本"
    return 1
  fi

  local npm_version
  npm_version=$(npm --version 2>/dev/null || echo "unknown")
  log_info "npm 版本: $npm_version"
}

install_npm_deps() {
  log_info "安装项目 npm 依赖..."

  log_info "清理 node_modules..."
  rm -rf "${PROJECT_DIR}/node_modules"
  if [ -d "${PROJECT_DIR}/backend/node_modules" ]; then
    rm -rf "${PROJECT_DIR}/backend/node_modules"
  fi

  log_info "安装根目录依赖 (npm ci --production=false)..."
  cd "${PROJECT_DIR}"
  npm ci --production=false

  if [ -f "${PROJECT_DIR}/backend/package.json" ] && [ "${PROJECT_DIR}/package.json" -ef "${PROJECT_DIR}/backend/package.json" ]; then
    log_info "backend 目录与根目录 package.json 相同，跳过重复安装"
  elif [ -f "${PROJECT_DIR}/backend/package.json" ]; then
    log_info "安装 backend 目录依赖..."
    cd "${PROJECT_DIR}/backend"
    npm ci --production=false || log_warn "backend npm ci 失败，跳过..."
  fi

  log_success "npm 依赖安装完成"
}

run_audit() {
  log_info "运行 npm audit (audit-level=high)..."
  cd "${PROJECT_DIR}"
  if npm audit --audit-level high; then
    log_success "npm audit 通过，未发现 high 级别以上漏洞"
  else
    log_warn "npm audit 发现 high 级别以上漏洞，请评估风险后处理（不阻断安装）"
  fi
}

generate_env_file() {
  log_info "生成 .env 配置文件..."

  if [ -f "${PROJECT_DIR}/.env" ]; then
    if confirm_action ".env 文件已存在，是否覆盖？" "n"; then
      cp "${PROJECT_DIR}/.env" "${PROJECT_DIR}/.env.bak.$(date +%Y%m%d%H%M%S)"
      log_info "旧配置已备份"
    else
      log_info "保留现有 .env 文件"
      return 0
    fi
  fi

  local example_file="${PROJECT_DIR}/.env.example"
  if [ ! -f "$example_file" ]; then
    example_file="${PROJECT_DIR}/backend/.env.example"
  fi

  if [ ! -f "$example_file" ]; then
    log_warn "未找到 .env.example 文件，跳过 .env 生成"
    return 0
  fi

  local session_secret
  local jwt_secret
  session_secret=$(openssl rand -hex 32 2>/dev/null || generate_password 64)
  jwt_secret=$(openssl rand -hex 32 2>/dev/null || generate_password 64)

  cp "$example_file" "${PROJECT_DIR}/.env"

  sed -i "s|your-session-secret-key-change-in-production-32chars-min|${session_secret}|g" "${PROJECT_DIR}/.env"
  sed -i "s|your-session-secret-key-here-change-in-production|${session_secret}|g" "${PROJECT_DIR}/.env"
  sed -i "s|SESSION_SECRET=.*|SESSION_SECRET=${session_secret}|" "${PROJECT_DIR}/.env"

  sed -i "s|your-jwt-secret-key-change-in-production-32chars-min|${jwt_secret}|g" "${PROJECT_DIR}/.env"
  sed -i "s|your-jwt-secret-key-here-change-in-production|${jwt_secret}|g" "${PROJECT_DIR}/.env"
  sed -i "s|JWT_SECRET=.*|JWT_SECRET=${jwt_secret}|" "${PROJECT_DIR}/.env"

  sed -i "s|^NODE_ENV=.*|NODE_ENV=development|" "${PROJECT_DIR}/.env"

  log_success ".env 文件已生成，SESSION_SECRET 和 JWT_SECRET 已自动填充"
  log_info "请根据需要修改其他配置项（如支付宝参数、Redis配置等）"
}

main() {
  log_info "=========================================="
  log_info "  Secure Platform 依赖安装脚本"
  log_info "=========================================="
  log_info "项目目录: ${PROJECT_DIR}"

  local os
  os=$(detect_os)
  log_info "检测到操作系统: $os"

  case "$os" in
    ubuntu)
      install_system_deps_ubuntu
      ;;
    centos)
      install_system_deps_centos
      ;;
    mac)
      install_system_deps_mac
      ;;
    *)
      log_warn "未识别的操作系统，请手动安装系统依赖"
      ;;
  esac

  check_nodejs
  install_npm_deps
  run_audit
  generate_env_file

  log_success "=========================================="
  log_success "  依赖安装完成！"
  log_success "=========================================="
  log_info "下一步操作："
  log_info "  1. 检查并修改 ${PROJECT_DIR}/.env 配置"
  log_info "  2. 启动开发: cd ${PROJECT_DIR} && npm run dev"
  log_info "  3. 运行测试: cd ${PROJECT_DIR} && npm test"
}

main "$@"
