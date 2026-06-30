#!/bin/bash
# 运行测试脚本
# 用法: ./scripts/run_tests.sh [选项]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "  Oath Toolchain - 运行测试"
echo "=========================================="
echo ""

# 检查是否安装了 pytest
if ! python -m pytest --version > /dev/null 2>&1; then
    echo "错误: 未找到 pytest，请先安装开发依赖:"
    echo "  pip install -e '.[dev]'"
    exit 1
fi

# 默认参数
TEST_PATH="tests"
MARKER=""
VERBOSE="-v"
COVERAGE=""
PARALLEL=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--marker)
            MARKER="$2"
            shift 2
            ;;
        -k|--keyword)
            KEYWORD="$2"
            shift 2
            ;;
        --unit)
            MARKER="unit"
            shift
            ;;
        --integration)
            MARKER="integration"
            shift
            ;;
        --performance)
            MARKER="performance"
            shift
            ;;
        --security)
            MARKER="security"
            shift
            ;;
        --coverage)
            COVERAGE="--cov=oath_toolchain --cov-report=term --cov-report=html"
            shift
            ;;
        -q|--quiet)
            VERBOSE="-q"
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -m, --marker MARKER   只运行指定标记的测试"
            echo "  -k, --keyword KEYWORD 只运行匹配关键字的测试"
            echo "  --unit                只运行单元测试"
            echo "  --integration         只运行集成测试"
            echo "  --performance         只运行性能测试"
            echo "  --security            只运行安全测试"
            echo "  --coverage            生成覆盖率报告"
            echo "  -q, --quiet           静默模式"
            echo "  -h, --help            显示此帮助信息"
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
PYTEST_ARGS+=("$VERBOSE")
PYTEST_ARGS+=("--tb=short")

if [ -n "$MARKER" ]; then
    PYTEST_ARGS+=("-m" "$MARKER")
    echo "运行标记: $MARKER"
fi

if [ -n "$KEYWORD" ]; then
    PYTEST_ARGS+=("-k" "$KEYWORD")
    echo "关键字过滤: $KEYWORD"
fi

if [ -n "$COVERAGE" ]; then
    PYTEST_ARGS+=("--cov=oath_toolchain")
    PYTEST_ARGS+=("--cov-report=term")
    PYTEST_ARGS+=("--cov-report=html")
    PYTEST_ARGS+=("--cov-report=xml")
fi

PYTEST_ARGS+=("$TEST_PATH")

echo ""
echo "运行 pytest ${PYTEST_ARGS[*]}"
echo ""

python -m pytest "${PYTEST_ARGS[@]}"

TEST_EXIT=$?

echo ""
if [ $TEST_EXIT -eq 0 ]; then
    echo "✓ 所有测试通过!"
else
    echo "✗ 测试失败 (退出码: $TEST_EXIT)"
fi

exit $TEST_EXIT
