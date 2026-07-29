#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=./utils.sh
source "${SCRIPT_DIR}/utils.sh"

cd "${PROJECT_DIR}"

ENVIRONMENT="production"

parse_args() {
  for arg in "$@"; do
    case "$arg" in
      --env=*)
        ENVIRONMENT="${arg#*=}"
        ;;
      --env)
        shift
        ENVIRONMENT="${1:-}"
        ;;
      *)
        ;;
    esac
  done

  case "$ENVIRONMENT" in
    production|staging)
      ;;
    *)
      log_error "无效的环境: ${ENVIRONMENT}，仅支持 production 或 staging"
      exit 1
      ;;
  esac
}

precheck_env_file() {
  log_info "检查 .env 配置文件..."

  if [ ! -f "${PROJECT_DIR}/.env" ]; then
    log_error ".env 文件不存在，请先创建配置"
    exit 1
  fi

  # shellcheck disable=SC2034
  local SESSION_SECRET JWT_SECRET PORT NODE_ENV
  SESSION_SECRET=$(grep -E '^SESSION_SECRET=' "${PROJECT_DIR}/.env" | cut -d= -f2- | tr -d '\r' || true)
  JWT_SECRET=$(grep -E '^JWT_SECRET=' "${PROJECT_DIR}/.env" | cut -d= -f2- | tr -d '\r' || true)
  PORT=$(grep -E '^PORT=' "${PROJECT_DIR}/.env" | cut -d= -f2- | tr -d '\r' || echo "3000")
  NODE_ENV=$(grep -E '^NODE_ENV=' "${PROJECT_DIR}/.env" | cut -d= -f2- | tr -d '\r' || echo "production")

  if [ -z "$SESSION_SECRET" ] || [ "$SESSION_SECRET" = "your-session-secret-key-change-in-production-32chars-min" ] || [ "${#SESSION_SECRET}" -lt 32 ]; then
    log_error "SESSION_SECRET 未正确配置（至少32字符）"
    exit 1
  fi

  if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "your-jwt-secret-key-change-in-production-32chars-min" ] || [ "${#JWT_SECRET}" -lt 32 ]; then
    log_error "JWT_SECRET 未正确配置（至少32字符）"
    exit 1
  fi

  log_success ".env 配置检查通过 (环境: ${NODE_ENV}, 端口: ${PORT})"
}

git_update() {
  log_info "检查 Git 工作区状态..."

  if ! command -v git >/dev/null 2>&1; then
    log_warn "Git 未安装，跳过代码更新"
    return 0
  fi

  if [ -d .git ] && git rev-parse --git-dir >/dev/null 2>&1; then
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
      log_warn "检测到未提交的更改"
      git status --short
      if confirm_action "是否执行 git stash 暂存更改？" "y"; then
        git stash push -m "deploy-stash-$(date +%Y%m%d%H%M%S)"
        log_success "更改已暂存"
      else
        log_error "用户取消部署"
        exit 1
      fi
    fi

    log_info "拉取最新代码 (origin main)..."
    if ! git pull origin main; then
      log_error "git pull 失败，请检查网络或手动合并冲突"
      exit 1
    fi
    log_success "代码已更新到最新版本"
  else
    log_warn "非 Git 仓库，跳过代码更新"
  fi
}

install_production_deps() {
  log_info "安装生产环境依赖..."
  cd "${PROJECT_DIR}"

  rm -rf node_modules
  npm ci --production
  log_success "生产依赖安装完成"

  if [ -f "backend/package.json" ] && [ ! "${PROJECT_DIR}/package.json" -ef "${PROJECT_DIR}/backend/package.json" ]; then
    cd "${PROJECT_DIR}/backend"
    rm -rf node_modules
    npm ci --production
    cd "${PROJECT_DIR}"
  fi
}

build_project() {
  log_info "构建 TypeScript 项目..."
  cd "${PROJECT_DIR}"
  npx tsc --build
  log_success "构建完成"
}

ensure_certificates() {
  log_info "检查证书文件..."
  local certs_dir="${PROJECT_DIR}/certs"

  if [ ! -f "${certs_dir}/root-ca.key" ] || [ ! -f "${certs_dir}/root-ca.crt" ]; then
    log_info "CA 证书不存在，开始生成..."
    bash "${SCRIPT_DIR}/generate-ca.sh"
  else
    log_info "证书已存在"
  fi
}

reload_service() {
  log_info "重启应用服务..."

  local port
  port=$(grep -E '^PORT=' "${PROJECT_DIR}/.env" | cut -d= -f2- | tr -d '\r' || echo "3000")

  if command -v pm2 >/dev/null 2>&1; then
    log_info "使用 PM2 管理进程"
    local pm2_app="secure-platform"

    if pm2 list --no-color 2>/dev/null | grep -q "${pm2_app}"; then
      pm2 reload "${pm2_app}" --update-env
      log_success "PM2: ${pm2_app} 已重新加载"
    else
      pm2 start dist/index.js \
        --name "${pm2_app}" \
        --env "${ENVIRONMENT}" \
        --cwd "${PROJECT_DIR}"
      pm2 save 2>/dev/null || true
      log_success "PM2: ${pm2_app} 已启动"
    fi
  elif systemctl list-units --type=service --no-legend 2>/dev/null | grep -q "secure-platform"; then
    log_info "使用 systemd 管理服务"
    sudo systemctl restart secure-platform
    log_success "systemd: secure-platform 服务已重启"
  elif command -v systemctl >/dev/null 2>&1; then
    log_warn "未找到 secure-platform systemd 服务，使用通用 restart"
    local service_unit
    service_unit=$(systemctl list-units --type=service --no-legend 2>/dev/null | grep -iE "node|app|secure" | head -1 | awk '{print $1}' || true)
    if [ -n "$service_unit" ]; then
      if confirm_action "是否重启服务: ${service_unit}？" "y"; then
        sudo systemctl restart "$service_unit"
        log_success "服务 ${service_unit} 已重启"
      else
        log_warn "请手动重启服务"
      fi
    else
      log_warn "未找到 node/systemd 服务，请手动启动应用"
    fi
  else
    log_warn "未检测到 PM2 或 systemd，请手动重启应用"
    log_info "  示例: cd ${PROJECT_DIR} && NODE_ENV=${ENVIRONMENT} PORT=${port} npm start &"
  fi
}

health_check() {
  log_info "执行健康检查..."
  local port
  port=$(grep -E '^PORT=' "${PROJECT_DIR}/.env" | cut -d= -f2- | tr -d '\r' || echo "3000")

  local max_retries=10
  local retry=0

  while [ "$retry" -lt "$max_retries" ]; do
    if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then
      log_success "健康检查通过: http://localhost:${port}/health"
      return 0
    fi
    retry=$((retry + 1))
    log_info "等待服务就绪... ($retry/${max_retries})"
    sleep 3
  done

  log_error "健康检查失败：服务在 ${max_retries} 次重试后仍未就绪"
  log_info "请检查日志: pm2 logs 或 journalctl -u secure-platform"
  return 1
}

main() {
  parse_args "$@"

  log_info "=========================================="
  log_info "  Secure Platform 部署脚本"
  log_info "  目标环境: ${ENVIRONMENT}"
  log_info "=========================================="
  log_info "项目目录: ${PROJECT_DIR}"

  precheck_env_file
  git_update
  install_production_deps
  build_project
  ensure_certificates
  reload_service
  sleep 3
  health_check

  log_success "=========================================="
  log_success "  部署完成！"
  log_success "=========================================="
  log_info "环境: ${ENVIRONMENT}"
  local port
  port=$(grep -E '^PORT=' "${PROJECT_DIR}/.env" | cut -d= -f2- | tr -d '\r' || echo "3000")
  log_info "服务地址: http://localhost:${port}"
  log_info "健康检查: http://localhost:${port}/health"
}

main "$@"
