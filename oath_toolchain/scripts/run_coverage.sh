#!/bin/bash
# 运行覆盖率脚本
# 用法: ./scripts/run_coverage.sh [选项]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "  Oath Toolchain - 代码覆盖率测试"
echo "=========================================="
echo ""

# 检查是否安装了 pytest-cov
if ! python -c "import pytest_cov" > /dev/null 2>&1; then
    echo "错误: 未找到 pytest-cov，请先安装开发依赖:"
    echo "  pip install -e '.[dev]'"
    exit 1
fi

# 默认参数
MIN_COVERAGE=85
REPORT_TYPE="term"
TEST_PATH="tests"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --min-coverage)
            MIN_COVERAGE="$2"
            shift 2
            ;;
        --html)
            REPORT_TYPE="html"
            shift
            ;;
        --xml)
            REPORT_TYPE="xml"
            shift
            ;;
        --all)
            REPORT_TYPE="all"
            shift
            ;;
        --unit)
            TEST_PATH="tests/test_core tests/test_tools tests/test_sdk"
            shift
            ;;
        --integration)
            TEST_PATH="tests/integration"
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --min-coverage NUM  最小覆盖率阈值 (默认: 85)"
            echo "  --html              生成 HTML 报告"
            echo "  --xml               生成 XML 报告"
            echo "  --all               生成所有格式报告"
            echo "  --unit              只测单元测试覆盖率"
            echo "  --integration       只测集成测试覆盖率"
            echo "  -h, --help          显示此帮助信息"
            exit 0
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

# 构建覆盖率报告参数
COV_ARGS=()
COV_ARGS+=("--cov=oath_toolchain")
COV_ARGS+=("--cov-branch")
COV_ARGS+=("--cov-report=term-missing")
COV_ARGS+=("--fail-under=$MIN_COVERAGE")

if [ "$REPORT_TYPE" = "html" ] || [ "$REPORT_TYPE" = "all" ]; then
    COV_ARGS+=("--cov-report=html")
fi

if [ "$REPORT_TYPE" = "xml" ] || [ "$REPORT_TYPE" = "all" ]; then
    COV_ARGS+=("--cov-report=xml")
fi

echo "测试路径: $TEST_PATH"
echo "最小覆盖率: $MIN_COVERAGE%"
echo "报告类型: $REPORT_TYPE"
echo ""
echo "运行覆盖率测试..."
echo ""

python -m pytest -v --tb=short "${COV_ARGS[@]}" $TEST_PATH

COV_EXIT=$?

echo ""
if [ $COV_EXIT -eq 0 ]; then
    echo "✓ 覆盖率测试通过!"
    if [ "$REPORT_TYPE" = "html" ] || [ "$REPORT_TYPE" = "all" ]; then
        echo "  HTML报告: htmlcov/index.html"
    fi
    if [ "$REPORT_TYPE" = "xml" ] || [ "$REPORT_TYPE" = "all" ]; then
        echo "  XML报告: coverage.xml"
    fi
else
    echo "✗ 覆盖率未达到阈值或测试失败 (退出码: $COV_EXIT)"
fi

exit $COV_EXIT
