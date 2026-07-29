#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=./utils.sh
source "${SCRIPT_DIR}/utils.sh"

cd "${PROJECT_DIR}"

declare -A STEP_TIMES
declare -A STEP_STATUS

TOTAL_START=$(date +%s)

run_step() {
  local step_name="$1"
  shift
  local step_fn="$1"
  local start end duration

  log_info ""
  log_info "=========================================="
  log_info "  [CI] 步骤: ${step_name}"
  log_info "=========================================="

  start=$(date +%s)
  set +e
  eval "${step_fn}"
  local rc=$?
  set -e

  end=$(date +%s)
  duration=$((end - start))
  STEP_TIMES["${step_name}"]="${duration}s"

  if [ "$rc" -eq 0 ]; then
    STEP_STATUS["${step_name}"]="PASS"
    log_success "[CI] 步骤通过: ${step_name} (${duration}s)"
  else
    STEP_STATUS["${step_name}"]="FAIL (exit=${rc})"
    log_error "[CI] 步骤失败: ${step_name} (${duration}s, exit=${rc})"
    print_timing_report
    exit "$rc"
  fi
}

step_install_deps() {
  set -e
  bash "${SCRIPT_DIR}/install-deps.sh" <<EOF
n
n
n
EOF
}

step_type_check() {
  set -e
  cd "${PROJECT_DIR}"
  npx tsc --noEmit
}

step_unit_tests() {
  set -e
  cd "${PROJECT_DIR}"
  npx jest --forceExit \
    --testPathPattern="unit" \
    --coverageThreshold='{"global":{"lines":80,"branches":70}}'
}

step_integration_tests() {
  set -e
  cd "${PROJECT_DIR}"

  NODE_ENV=test \
    SESSION_SECRET=ci-session-secret-testing-32-chars-minimum \
    JWT_SECRET=ci-jwt-secret-testing-32-chars-minimum-abcdef \
    REDIS_HOST=localhost REDIS_PORT=6379 \
    npx jest --forceExit --testPathPattern="integration"
}

step_build() {
  set -e
  cd "${PROJECT_DIR}"
  rm -rf dist
  npx tsc --build
  [ -d dist ] && log_info "Build 输出目录: $(du -sh dist | cut -f1)"
}

step_deploy_main_only() {
  set -e
  local branch=""
  local is_main=false

  if command -v git >/dev/null 2>&1 && [ -d .git ]; then
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
      is_main=true
    fi
    if [ -n "${GITHUB_REF:-}" ]; then
      case "$GITHUB_REF" in
        refs/heads/main|refs/heads/master)
          is_main=true
          ;;
      esac
    fi
  fi

  if [ "$is_main" = true ]; then
    log_info "[CI] main 分支，执行部署..."
    bash "${SCRIPT_DIR}/deploy.sh" --env=production
  else
    log_info "[CI] 非 main 分支 (当前: ${branch:-unknown})，跳过部署"
  fi
}

print_timing_report() {
  local total_end total_duration
  total_end=$(date +%s)
  total_duration=$((total_end - TOTAL_START))

  log_info ""
  log_info "=========================================="
  log_info "  CI 流水线 - 时间报告"
  log_info "=========================================="
  for step in install-deps type-check unit-tests integration-tests build deploy; do
    if [ -n "${STEP_TIMES[$step]+x}" ]; then
      local status="${STEP_STATUS[$step]}"
      local time="${STEP_TIMES[$step]}"
      if [ "$status" = "PASS" ]; then
        echo -e "  ${GREEN}✓${NC} ${step}: ${time}"
      else
        echo -e "  ${RED}✗${NC} ${step}: ${status} - ${time}"
      fi
    fi
  done
  log_info "=========================================="
  log_info "总耗时: ${total_duration}s"
  log_info "=========================================="
}

main() {
  log_info "=========================================="
  log_info "  Secure Platform CI 流水线"
  log_info "  开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
  log_info "=========================================="
  log_info "项目目录: ${PROJECT_DIR}"

  export CI=true

  run_step "install-deps"      step_install_deps
  run_step "type-check"        step_type_check
  run_step "unit-tests"        step_unit_tests
  run_step "integration-tests" step_integration_tests
  run_step "build"             step_build
  run_step "deploy"            step_deploy_main_only

  print_timing_report

  log_success ""
  log_success "=========================================="
  log_success "  CI 流水线执行成功！"
  log_success "=========================================="
}

main "$@"
