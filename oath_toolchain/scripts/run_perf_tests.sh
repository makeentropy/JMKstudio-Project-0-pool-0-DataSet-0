#!/bin/bash
# 运行性能测试脚本
# 用法: ./scripts/run_perf_tests.sh [选项]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "  Oath Toolchain - 性能测试"
echo "=========================================="
echo ""

# 检查是否安装了 pytest
if ! python -m pytest --version > /dev/null 2>&1; then
    echo "错误: 未找到 pytest，请先安装开发依赖:"
    echo "  pip install -e '.[dev]'"
    exit 1
fi

# 默认参数
TEST_PATH="tests/performance"
OUTPUT_FILE=""
CATEGORY=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --crypto)
            CATEGORY="crypto"
            shift
            ;;
        --tools)
            CATEGORY="tools"
            shift
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --crypto        只运行密码学性能测试"
            echo "  --tools         只运行工具性能测试"
            echo "  --output FILE   将输出保存到文件"
            echo "  -h, --help      显示此帮助信息"
            exit 0
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

# 构建 pytest 命令
PYTEST_ARGS=()
PYTEST_ARGS+=("-v")
PYTEST_ARGS+=("-s")
PYTEST_ARGS+=("-m")
PYTEST_ARGS+=("performance")
PYTEST_ARGS+=("--tb=short")

if [ -n "$CATEGORY" ]; then
    TEST_PATH="tests/performance/test_performance_${CATEGORY}.py"
fi

PYTEST_ARGS+=("$TEST_PATH")

echo "性能测试路径: $TEST_PATH"
echo ""

if [ -n "$OUTPUT_FILE" ]; then
    echo "输出文件: $OUTPUT_FILE"
    echo ""
    python -m pytest "${PYTEST_ARGS[@]}" 2>&1 | tee "$OUTPUT_FILE"
else
    python -m pytest "${PYTEST_ARGS[@]}"
fi

PERF_EXIT=${PIPESTATUS[0]:-$?}

echo ""
if [ $PERF_EXIT -eq 0 ]; then
    echo "✓ 性能测试完成!"
else
    echo "✗ 性能测试失败 (退出码: $PERF_EXIT)"
fi

exit $PERF_EXIT
