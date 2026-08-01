#!/data/data/com.termux/files/usr/bin/env bash
# ==========================================================
# CHRONOS · Termux 一键安装脚本
# 运行方式：
#   curl -sSL <URL> | bash   或直接 bash install-termux.sh
# ==========================================================
set -euo pipefail

BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; CYN=$'\e[36m'; R=$'\e[0m'

echo -e "${CYN}${BOLD}
  ╔══════════════════════════════════════════════╗
  ║    CHRONOS 时空工作站 · Termux 安装器         ║
  ╠══════════════════════════════════════════════╣
  ║  Workgroup Job + Isochronic Biological Clock ║
  ╚══════════════════════════════════════════════╝
${R}"

step() { echo -e "\n${CYN}▸ ${BOLD}$1${R}"; }
ok()   { echo -e "  ${GRN}✓${R} $1"; }
warn() { echo -e "  ${YEL}!${R} $1"; }

# 0. 升级包
step "更新 Termux 包管理..."
pkg update -y -o Dpkg::Options::="--force-confnew" 2>/dev/null || apt-get update -y 2>/dev/null || warn "跳过 apt update"

# 1. 安装依赖
step "安装系统依赖 (python, curl, git, openssl, 可选音频播放器)..."
DEPS="python curl git"
EXTRA=""
# 建议的音频播放器
for p in termux-api pulseaudio sox; do
  EXTRA="$EXTRA $p"
done
pkg install -y $DEPS $EXTRA 2>/dev/null || apt-get install -y $DEPS 2>/dev/null || warn "部分包安装失败，继续"

# 2. 验证 python
if command -v python3 >/dev/null 2>&1; then
  ok "Python3: $(python3 --version)"
else
  echo -e "${RED}✗ Python 安装失败${R}"; exit 1
fi

# 3. 拉取或使用本地项目
INSTALL_DIR="${HOME}/chronos-project"
step "准备项目目录: $INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
  cd "$INSTALL_DIR"
  git pull --ff-only || warn "git pull 失败，使用本地版本"
  ok "已更新现有项目"
elif [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/cli/chronos_cli.py" ]; then
  ok "已找到本地 chronos-project"
else
  # 尝试从当前脚本目录推断（如果是已存在于手机上）
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -f "$SCRIPT_DIR/../cli/chronos_cli.py" ]; then
    SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    if [ "$SRC_DIR" != "$INSTALL_DIR" ]; then
      mkdir -p "$(dirname "$INSTALL_DIR")"
      cp -r "$SRC_DIR" "$INSTALL_DIR"
      ok "从 $SRC_DIR 复制到 $INSTALL_DIR"
    else
      ok "项目已在正确位置"
    fi
  else
    ok "项目目录不存在，需要手动下载代码到 $INSTALL_DIR"
    echo "   示例: git clone <repo> $INSTALL_DIR"
  fi
fi

# 4. 权限
chmod +x "$INSTALL_DIR/cli/chronos_cli.py" "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true

# 5. 建立 PATH 链接
BINDIR="${PREFIX}/bin"
if [ -d "$BINDIR" ]; then
  ln -sf "$INSTALL_DIR/scripts/start-cli.sh" "$BINDIR/chronos" 2>/dev/null \
    && ln -sf "$INSTALL_DIR/scripts/start-web.sh" "$BINDIR/chronos-web" 2>/dev/null \
    && ok "已创建命令: chronos, chronos-web"
fi

echo
echo -e "${GRN}${BOLD}═══════════════════ 安装完成 ═══════════════════${R}"
echo
echo "  ⚙  命令行 (CLI REPL):"
echo "      ${CYN}chronos${R}            (进入交互模式, 输入 h 查看帮助)"
echo "      ${CYN}chronos tui${R}        (curses 终端 UI)"
echo "      ${CYN}chronos version${R}"
echo "      ${CYN}chronos export${R}     (导出 JSON, 用于 Web 导入)"
echo
echo "  🌐 Web 服务器 (可选):"
echo "      ${CYN}chronos-web${R}        (然后在浏览器打开 http://localhost:8000)"
echo
echo "  📦 数据目录:"
echo "      ~/.chronos/data.json"
echo
echo "  ☕ 快速使用:"
echo "      chronos> ${CYN}focus 25${R}     ← 启动 25 分钟 40Hz 专注声频"
echo "      chronos> ${CYN}jobs${R}         ← 列出全部任务"
echo "      chronos> ${CYN}kanban${R}       ← 查看看板"
echo "      chronos> ${CYN}add-job${R}      ← 新建任务"
