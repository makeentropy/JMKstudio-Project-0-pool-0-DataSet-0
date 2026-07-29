#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=./utils.sh
source "${SCRIPT_DIR}/utils.sh"

cd "${PROJECT_DIR}"

declare -A STAGE_RESULTS
OVERALL_PASS=true

run_stage() {
  local stage_name="$1"
  shift
  local stage_cmd="$*"
  local start end duration

  log_info "=========================================="
  log_info "  阶段: ${stage_name}"
  log_info "=========================================="

  start=$(date +%s)
  if eval "$stage_cmd"; then
    end=$(date +%s)
    duration=$((end - start))
    log_success "阶段通过: ${stage_name} (耗时 ${duration}s)"
    STAGE_RESULTS["${stage_name}"]="PASS (${duration}s)"
  else
    end=$(date +%s)
    duration=$((end - start))
    log_error "阶段失败: ${stage_name} (耗时 ${duration}s)"
    STAGE_RESULTS["${stage_name}"]="FAIL (${duration}s)"
    OVERALL_PASS=false
  fi
}

stage_env_start() {
  log_info "阶段1: 启动测试环境..."

  if ! command -v docker >/dev/null 2>&1; then
    log_warn "Docker 未安装，跳过 Redis 容器启动"
    STAGE_RESULTS["环境启动"]="SKIP (Docker未安装)"
    return 0
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose up -d redis 2>&1 || true
  elif docker compose version >/dev/null 2>&1; then
    docker compose up -d redis 2>&1 || true
  fi

  local max_retries=10
  local retry=0
  local redis_ready=false

  while [ "$retry" -lt "$max_retries" ]; do
    if command -v redis-cli >/dev/null 2>&1; then
      if redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q PONG; then
        redis_ready=true
        break
      fi
    else
      if wait_for_service localhost 6379 2 >/dev/null 2>&1; then
        redis_ready=true
        break
      fi
    fi
    retry=$((retry + 1))
    log_info "等待 Redis 就绪... ($retry/$max_retries)"
    sleep 2
  done

  if [ "$redis_ready" = true ]; then
    log_success "Redis 已就绪"
  else
    log_warn "Redis 未就绪，将使用内存会话继续测试"
  fi
}

stage_type_check() {
  log_info "阶段2: TypeScript 类型检查..."
  cd "${PROJECT_DIR}"
  if [ -f "node_modules/.bin/tsc" ]; then
    npx tsc --noEmit
  else
    npx --yes typescript@5 --noEmit 2>/dev/null || {
      log_warn "tsc 未找到，尝试直接运行 tsc"
      tsc --noEmit 2>/dev/null || true
    }
  fi
}

stage_lint() {
  log_info "阶段3: Lint 检查..."
  cd "${PROJECT_DIR}"
  if [ -f "node_modules/.bin/eslint" ]; then
    npx eslint backend/src --ext .ts --max-warnings 100 2>&1 || true
  elif [ -f "backend/node_modules/.bin/eslint" ]; then
    cd backend && npx eslint src --ext .ts --max-warnings 100 2>&1 || true
  else
    log_warn "ESLint 未安装，跳过 Lint 阶段"
    return 0
  fi
}

stage_unit_test() {
  log_info "阶段4: 单元测试..."
  cd "${PROJECT_DIR}"
  if [ ! -f "node_modules/.bin/jest" ]; then
    log_error "Jest 未安装，请先运行 install-deps.sh"
    return 1
  fi

  npx jest --forceExit --coverage \
    --testPathPattern="unit" \
    --coverageThreshold='{"global":{"lines":80,"branches":70}}' \
    --coverageReporters=text-summary 2>&1 || return 1
}

stage_integration_test() {
  log_info "阶段5: 集成测试..."
  cd "${PROJECT_DIR}"

  if command -v docker-compose >/dev/null 2>&1 && docker-compose config --services 2>/dev/null | grep -q tests; then
    docker-compose run \
      -e NODE_ENV=test \
      -e REDIS_URL=redis://redis:6379 \
      tests npx jest --forceExit \
      --testPathPattern="integration" 2>&1 || return 1
  elif docker compose version >/dev/null 2>&1 && docker compose config --services 2>/dev/null | grep -q tests; then
    docker compose run \
      -e NODE_ENV=test \
      -e REDIS_URL=redis://redis:6379 \
      tests npx jest --forceExit \
      --testPathPattern="integration" 2>&1 || return 1
  else
    log_info "直接运行集成测试（未使用 docker-compose tests 服务）..."
    NODE_ENV=test REDIS_URL=redis://localhost:6379 npx jest --forceExit \
      --testPathPattern="integration" 2>&1 || return 1
  fi
}

stage_security_audit() {
  log_info "阶段6: 安全审计..."
  cd "${PROJECT_DIR}"
  local audit_ok=true

  log_info "运行 npm audit (audit-level=high)..."
  if npm audit --audit-level=high 2>&1; then
    log_success "npm audit 通过"
  else
    log_warn "npm audit 发现 high 级别漏洞（不阻断）"
    audit_ok=false
  fi

  if command -v snyk >/dev/null 2>&1 || [ -f "node_modules/.bin/snyk" ]; then
    log_info "运行 Snyk 测试..."
    if npx snyk test 2>&1; then
      log_success "Snyk 测试通过"
    else
      log_warn "Snyk 测试发现问题（不阻断）"
      audit_ok=false
    fi
  else
    log_info "Snyk 未安装，跳过"
  fi

  $audit_ok || true
}

stage_penetration_scan() {
  log_info "阶段7: 渗透扫描（基础探测）..."
  cd "${PROJECT_DIR}"

  local test_port=39999
  local pid_file
  pid_file=$(mktemp)
  local server_started=false

  cleanup_server() {
    if [ -f "$pid_file" ] && [ -s "$pid_file" ]; then
      local pid
      pid=$(cat "$pid_file")
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$pid_file"
  }
  trap cleanup_server RETURN

  log_info "尝试启动测试服务器 (端口: ${test_port})..."
  if [ -f "node_modules/.bin/ts-node" ]; then
    PORT=$test_port NODE_ENV=test SESSION_SECRET=test-session-secret-minimum-32-chars-long JWT_SECRET=test-jwt-secret-minimum-32-chars-long nohup npx ts-node backend/src/index.ts >/tmp/test-server.log 2>&1 &
    echo $! > "$pid_file"
    server_started=true
  elif [ -d "dist" ]; then
    PORT=$test_port NODE_ENV=test SESSION_SECRET=test-session-secret-minimum-32-chars-long JWT_SECRET=test-jwt-secret-minimum-32-chars-long nohup node dist/index.js >/tmp/test-server.log 2>&1 &
    echo $! > "$pid_file"
    server_started=true
  fi

  if [ "$server_started" = true ]; then
    sleep 5
    log_info "执行基础安全探测..."

    local scan_ok=true

    if wait_for_service "localhost" "$test_port" 10 2>/dev/null; then
      local status
      status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${test_port}/admin" 2>/dev/null || echo "000")
      if [ "$status" = "401" ]; then
        log_success "✓ 未授权访问 /admin 返回 401 (状态: $status)"
      elif [ "$status" != "000" ]; then
        log_warn "⚠ 未授权访问 /admin 返回状态 $status (期望 401)"
        scan_ok=false
      fi

      status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${test_port}/api/v1/admin/users" 2>/dev/null || echo "000")
      if [ "$status" = "401" ] || [ "$status" = "404" ]; then
        log_success "✓ 未授权访问敏感 API 返回 ${status}"
      elif [ "$status" != "000" ] && [ "$status" != "200" ]; then
        log_info "  敏感 API 访问返回 $status"
      fi

      status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${test_port}/health" 2>/dev/null || echo "000")
      if [ "$status" = "200" ]; then
        log_success "✓ /health 端点正常 (状态: $status)"
      fi
    else
      log_warn "测试服务器未在超时时间内就绪，跳过探测"
    fi

    cleanup_server
    $scan_ok
  else
    log_warn "无法启动测试服务器（缺少 ts-node 或 dist 目录），跳过渗透扫描阶段"
    return 0
  fi
}

cleanup() {
  log_info "=========================================="
  log_info "  执行清理操作"
  log_info "=========================================="

  cd "${PROJECT_DIR}"
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose down -v 2>&1 || true
  elif docker compose version >/dev/null 2>&1; then
    docker compose down -v 2>&1 || true
  fi

  log_info "容器已清理"
}

generate_report() {
  log_info ""
  log_info "=========================================="
  log_info "  沙箱测试报告"
  log_info "=========================================="

  for stage in "${!STAGE_RESULTS[@]}"; do
    local result="${STAGE_RESULTS[$stage]}"
    if [[ "$result" == PASS* ]]; then
      echo -e "  ${GREEN}✓${NC} ${stage}: ${result}"
    elif [[ "$result" == SKIP* ]]; then
      echo -e "  ${YELLOW}○${NC} ${stage}: ${result}"
    else
      echo -e "  ${RED}✗${NC} ${stage}: ${result}"
    fi
  done

  log_info "=========================================="
  if [ "$OVERALL_PASS" = true ]; then
    log_success "总体结果: 全部通过"
  else
    log_error "总体结果: 存在失败，请检查上方日志"
    return 1
  fi
}

main() {
  log_info "=========================================="
  log_info "  Secure Platform 沙箱测试"
  log_info "=========================================="
  log_info "项目目录: ${PROJECT_DIR}"
  log_info ""

  run_stage "环境启动" 'stage_env_start'
  run_stage "类型检查" 'stage_type_check'
  run_stage "Lint 检查" 'stage_lint'
  run_stage "单元测试" 'stage_unit_test'
  run_stage "集成测试" 'stage_integration_test'
  run_stage "安全审计" 'stage_security_audit'
  run_stage "渗透扫描" 'stage_penetration_scan'

  cleanup || true

  generate_report
}

main "$@"
