#!/usr/bin/env bash
# =============================================================================
#  mic_kit.sh  —  实时麦克风底层监听 Kit (Debian Linux)
#  Real-time Microphone Low-level Listening Kit
#  Shell CLI  ·  Tools Chain  ·  Numbered Menu (键入序号 + 回车执行)
#
#  依赖 / Deps (按需自动检测):
#    alsa-utils (arecord/amixer/aplay)   # 内核级 ALSA 底层
#    pulseaudio-utils (pactl/parecord)   # PulseAudio 声音服务器
#    pipewire (pw-cli/pw-cat/pw-link)    # PipeWire 现代音频服务
#    wireplumber (wpctl)                 # PipeWire 会话管理
#    curl / python3 / nc                 # 服务器模式 (source.sh 分发)
#
#  一键运行 / Quick start:
#    chmod +x mic_kit.sh && ./mic_kit.sh
#  远程拉取 / Fetch from server:
#    curl -fsSL http://SERVER:PORT/source.sh -o mic_kit.sh
# =============================================================================
set -o pipefail

# ---------- 全局配置 / Global config ----------
readonly PROG_NAME="mic_kit"
readonly PROG_VERSION="1.0.0"
SELF_PATH="$(readlink -f "$0" 2>/dev/null || echo "$0")"; readonly SELF_PATH
readonly REC_DIR="${REC_DIR:-$HOME/mic_kit_recordings}"
mkdir -p "$REC_DIR" 2>/dev/null || true

# 默认录音设备 (空=自动选择第一个) / default capture dev
MIC_DEV="${MIC_DEV:-}"
# 默认采样率/格式
MIC_RATE="${MIC_RATE:-48000}"
MIC_FMT="${MIC_FMT:-S16_LE}"
MIC_CHANNELS="${MIC_CHANNELS:-1}"
# 活动检测阈值 (RMS, 0-32767)
ACT_THRESHOLD="${ACT_THRESHOLD:-1500}"

# ---------- 颜色 / Colors ----------
if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_RED=$'\033[31m'
  C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_BLU=$'\033[34m'
  C_MAG=$'\033[35m'; C_CYA=$'\033[36m'; C_DIM=$'\033[2m'
else
  C_RESET=""; C_BOLD=""; C_RED=""; C_GRN=""; C_YEL=""
  C_BLU=""; C_MAG=""; C_CYA=""; C_DIM=""
fi

# ---------- 通用工具 / Helpers ----------
msg()  { printf '%s\n' "$*"; }
info() { printf '%s[INFO]%s %s\n' "$C_CYA" "$C_RESET" "$*"; }
ok()   { printf '%s[ OK ]%s %s\n' "$C_GRN" "$C_RESET" "$*"; }
warn() { printf '%s[WARN]%s %s\n' "$C_YEL" "$C_RESET" "$*" >&2; }
err()  { printf '%s[ERR ]%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
hdr()  { printf '\n%s═══ %s ═══%s\n' "$C_BOLD$C_MAG" "$*" "$C_RESET"; }
pause(){ read -rp "${C_DIM}按回车继续 / Press Enter to continue...${C_RESET}" _; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

require() {
  local missing=()
  for c in "$@"; do
    if ! has_cmd "$c"; then missing+=("$c"); fi
  done
  if ((${#missing[@]})); then
    err "缺少命令 / Missing: ${missing[*]}"
    warn "Debian 安装: sudo apt-get install -y alsa-utils pulseaudio-utils pipewire-audio wireplumber curl"
    return 1
  fi
  return 0
}

# 探测音频子系统 / detect audio subsystem in use
detect_subsystem() {
  if pgrep -x pipewire >/dev/null 2>&1 || pgrep -x pipewire-pulse >/dev/null 2>&1; then
    echo "pipewire"
  elif pgrep -x pulseaudio >/dev/null 2>&1; then
    echo "pulseaudio"
  else
    echo "alsa"
  fi
}

# 选择默认麦克风设备 / pick a default capture device
pick_device() {
  if [[ -n "$MIC_DEV" ]]; then echo "$MIC_DEV"; return; fi
  local sub; sub="$(detect_subsystem)"
  case "$sub" in
    pipewire|pulseaudio)
      if has_cmd pactl; then
        local dev; dev="$(pactl list short sources 2>/dev/null \
          | awk '!/\.monitor$/ && !/^$/ {print $1; exit}')"
        [[ -n "$dev" ]] && { echo "$dev"; return; }
      fi
      ;;
  esac
  # ALSA fallback
  if has_cmd arecord; then
    local dev; dev="$(arecord -l 2>/dev/null \
      | awk -F: '/^card/ {gsub(/card | /,"",$1); print "hw:"$1",0"; exit}')"
    [[ -n "$dev" ]] && { echo "$dev"; return; }
  fi
  echo "default"
}

# =============================================================================
#  Tools Chain —— 工具链各功能
# =============================================================================

# [1] 检测音频设备 (底层) / detect audio devices
tc_detect_devices() {
  hdr "音频设备检测 / Audio Device Detection"
  local sub; sub="$(detect_subsystem)"
  info "活动音频子系统 / Active subsystem: ${C_BOLD}$sub${C_RESET}"

  echo; printf '%s── /proc/asound (内核 ALSA 底层) ──%s\n' "$C_DIM" "$C_RESET"
  if [[ -r /proc/asound/cards ]]; then
    cat /proc/asound/cards
  else
    warn "/proc/asound/cards 不可读 (权限?)"
  fi

  if has_cmd arecord; then
    echo; printf '%s── arecord -l (ALSA 捕获设备) ──%s\n' "$C_DIM" "$C_RESET"
    arecord -l 2>&1 || true
  fi
  if has_cmd pactl; then
    echo; printf '%s── pactl sources (PulseAudio/PipeWire-Pulse) ──%s\n' "$C_DIM" "$C_RESET"
    pactl list short sources 2>&1 || true
  fi
  if has_cmd pw-cli; then
    echo; printf '%s── pw-cli list Node (PipeWire 原生) ──%s\n' "$C_DIM" "$C_RESET"
    pw-cli ls Node 2>&1 | grep -E 'media\.class|node\.description|obj\.id' \
      | head -n 40 || true
  fi
  ok "设备检测完成"
}

# [2] 实时监听 (听到自己的声音) / real-time monitor (loopback)
tc_realtime_monitor() {
  hdr "实时麦克风监听 / Real-time Monitor (loopback)"
  require pactl || return 1
  local sub; sub="$(detect_subsystem)"
  if [[ "$sub" == "pipewire" || "$sub" == "pulseaudio" ]]; then
    info "加载 module-loopback (低延迟 1ms). 按 Ctrl+C 停止并卸载."
    warn "注意啸叫反馈! 请戴耳机或调低扬声器."
    pause
    local id; id="$(pactl load-module module-loopback latency_msec=1 2>&1)"
    if [[ -z "$id" || "$id" == Failure* ]]; then
      err "加载 loopback 失败: $id"; return 1
    fi
    info "loopback 模块 ID=$id 已激活. 监听中..."
    trap 'pactl unload-module "$id" 2>/dev/null; info "已停止监听."; trap - INT; return 0' INT
    # 保持运行直到 Ctrl+C
    while true; do sleep 1; done
  else
    # ALSA 直通: arecord | aplay
    local dev; dev="$(pick_device)"
    warn "ALSA 直通 arecord|aplay, 可能产生反馈啸叫. 戴耳机!"
    info "设备=$dev  Ctrl+C 停止"
    pause
    arecord -D "$dev" -f "$MIC_FMT" -r "$MIC_RATE" -c "$MIC_CHANNELS" -t raw 2>/dev/null \
      | aplay -f "$MIC_FMT" -r "$MIC_RATE" -c "$MIC_CHANNELS" -t raw 2>/dev/null
  fi
}

# [3] 实时电平表 (CLI VU meter) / real-time level meter
tc_level_meter() {
  hdr "实时电平表 / CLI VU Meter"
  local sub; sub="$(detect_subsystem)"
  local dev; dev="$(pick_device)"
  info "设备=$dev  Ctrl+C 退出"
  local bar_width=40
  # 用 arecord 输出 S16_LE raw → od 转 16bit 数值 → awk 计算 RMS 并画条
  if has_cmd arecord; then
    arecord -D "$dev" -f S16_LE -r 8000 -c 1 -t raw 2>/dev/null \
      | od -An -tuS -w2 -v \
      | awk -v W="$bar_width" '
          { v=$1; if(v<0)v=-v; sum+=v*v; n++;
            if(n>=400){
              rms=sqrt(sum/n); pct=rms/32768; if(pct>1)pct=1;
              b=int(pct*W);
              printf "\r["; for(i=0;i<b;i++)printf "#"; for(i=b;i<W;i++)printf " ";
              printf "] %6d  ", int(rms); fflush();
              sum=0; n=0;
            }
          }'
    echo
    ok "电平表结束"
  else
    err "需要 arecord (alsa-utils)"
  fi
}

# [4] 录音到文件 / record to file
tc_record() {
  hdr "录音到文件 / Record to File"
  local ts fname
  ts="$(date +%Y%m%d_%H%M%S)"
  fname="$REC_DIR/rec_${ts}.wav"
  local dev; dev="$(pick_device)"
  info "设备=$dev  采样=$MIC_RATE/$MIC_FMT/$MIC_CHANNELS ch"
  info "输出文件: $fname"
  info "按 Ctrl+C 停止录音"
  if has_cmd arecord; then
    # 不指定 -d 表示持续录音直到 Ctrl+C
    arecord -D "$dev" -f "$MIC_FMT" -r "$MIC_RATE" -c "$MIC_CHANNELS" \
      -v "$fname" 2>&1 | grep -vE '^Recording|^(Done|Aborted)' || true
  else
    err "需要 arecord (alsa-utils)"; return 1
  fi
  [[ -f "$fname" ]] && ok "已保存: $fname (${C_BOLD}$(du -h "$fname" | cut -f1)${C_RESET})" \
                   || err "录音文件未生成"
}

# [5] 麦克风音量控制 / mic volume control
tc_volume() {
  hdr "麦克风音量控制 / Volume Control"
  local sub; sub="$(detect_subsystem)"
  case "$sub" in
    pipewire)
      if has_cmd wpctl; then
        info "捕获设备音量 (wpctl):"
        wpctl status 2>/dev/null | sed -n '/Audio.*Capture/,/^[A-Z]/p' | grep -E 'Source|volume'
        echo
        local id; read -rp "${C_DIM}输入 Source ID (如 41)${C_RESET}: " id
        [[ -z "$id" ]] && return
        local pct; read -rp "${C_DIM}音量百分比 (0-150)${C_RESET}: " pct
        wpctl set-volume "$id" "${pct}%"
        ok "已设置 $id -> ${pct}%"
      else err "需要 wpctl (wireplumber)"; fi
      ;;
    pulseaudio)
      if has_cmd pactl; then
        local src; src="$(pactl list short sources 2>/dev/null | awk '!/\.monitor$/{print $1; exit}')"
        [[ -z "$src" ]] && { err "未找到 source"; return 1; }
        local pct; read -rp "${C_DIM}音量百分比 (0-200)${C_RESET}: " pct
        pactl set-source-volume "$src" "${pct}%"
        ok "source $src -> ${pct}%"
      fi
      ;;
    alsa)
      if has_cmd amixer; then
        amixer sget Capture >/dev/null 2>&1 || { err "无 Capture 控件"; return 1; }
        local pct; read -rp "${C_DIM}音量百分比 (0-100)${C_RESET}: " pct
        amixer -q sset Capture "${pct}%"
        ok "ALSA Capture -> ${pct}%"
      fi
      ;;
  esac
}

# [6] 静音/取消静音 / mute toggle
tc_mute() {
  hdr "静音 / 取消静音 (Mute Toggle)"
  local sub; sub="$(detect_subsystem)"
  case "$sub" in
    pipewire)
      if has_cmd wpctl; then
        local id; read -rp "${C_DIM}输入 Source ID${C_RESET}: " id
        [[ -z "$id" ]] && return
        wpctl set-mute "$id" toggle
        ok "已切换 $id 静音状态"
      fi
      ;;
    pulseaudio)
      if has_cmd pactl; then
        local src; src="$(pactl list short sources 2>/dev/null | awk '!/\.monitor$/{print $1; exit}')"
        pactl set-source-mute "$src" toggle
        ok "已切换 source $src 静音状态"
      fi
      ;;
    alsa)
      if has_cmd amixer; then
        amixer -q sset Capture toggle
        ok "已切换 ALSA Capture 静音"
      fi
      ;;
  esac
}

# [7] 麦克风活动检测 (阈值触发) / activity detection
tc_activity_detect() {
  hdr "麦克风活动检测 / Activity Detection (threshold=$ACT_THRESHOLD)"
  local dev; dev="$(pick_device)"
  info "设备=$dev  阈值=$ACT_THRESHOLD  Ctrl+C 退出"
  require arecord || return 1
  warn "当 RMS 超过阈值时打印 [SOUND] 事件"
  arecord -D "$dev" -f S16_LE -r 8000 -c 1 -t raw 2>/dev/null \
    | od -An -tuS -w2 -v \
    | awk -v TH="$ACT_THRESHOLD" '
        { v=$1; if(v<0)v=-v; sum+=v*v; n++;
          if(n>=800){
            rms=sqrt(sum/n);
            if(rms>TH){
              printf "[%s] [SOUND] rms=%d\n", strftime("%H:%M:%S"), int(rms); fflush();
            }
            sum=0; n=0;
          }
        }'
}

# [8] 音频子系统状态 / subsystem status
tc_subsystem_status() {
  hdr "音频子系统状态 / Subsystem Status"
  local sub; sub="$(detect_subsystem)"
  info "当前活动子系统: $sub"
  echo
  printf '%s── 进程 / Processes ──%s\n' "$C_DIM" "$C_RESET"
  for p in pipewire pipewire-pulse pulseaudio wireplumber alsactl; do
    if pgrep -x "$p" >/dev/null 2>&1; then
      printf '  %s✓%s %-16s pid=%s\n' "$C_GRN" "$C_RESET" "$p" "$(pgrep -x "$p" | head -1)"
    else
      printf '  %s✗%s %-16s %s\n' "$C_RED" "$C_RESET" "$p" "未运行"
    fi
  done
  if has_cmd wpctl; then
    echo; printf '%s── wpctl status ──%s\n' "$C_DIM" "$C_RESET"
    wpctl status 2>/dev/null | head -n 30
  fi
}

# [9] 底层设备信息 (/proc, /dev/snd) / low-level device info
tc_lowlevel_info() {
  hdr "底层设备信息 / Low-level Device Info"
  printf '%s── /proc/asound ──%s\n' "$C_DIM" "$C_RESET"
  for f in /proc/asound/cards /proc/asound/devices /proc/asound/modules /proc/asound/version; do
    [[ -r "$f" ]] && { echo "[$f]"; cat "$f"; echo; }
  done
  printf '%s── /dev/snd ──%s\n' "$C_DIM" "$C_RESET"
  ls -l /dev/snd 2>/dev/null || warn "/dev/snd 不存在"
  printf '\n%s── 控制接口 / Control CTLs ──%s\n' "$C_DIM" "$C_RESET"
  if has_cmd amixer; then
    amixer controls 2>/dev/null | head -n 20
  fi
}

# [10] 服务器模式：curl 分发 / 拉取 source.sh
#      Script Server curl give source.sh
tc_server_mode() {
  hdr "服务器模式 / Server Mode (curl + source.sh)"
  cat <<'EOF'
  1) 启动 HTTP 分发服务 (serve this script as source.sh)
  2) 从远端 curl 拉取 source.sh 覆盖本地
  3) 打印一键安装命令
  0) 返回 / Back
EOF
  local n; read -rp "${C_DIM}选择 / choice${C_RESET}: " n
  case "$n" in
    1) _serve_source ;;
    2) _fetch_source ;;
    3) _print_install_cmd ;;
    *) return 0 ;;
  esac
}

_serve_source() {
  require curl || return 1
  local port; read -rp "${C_DIM}监听端口 / port (默认 8080)${C_RESET}: " port
  port="${port:-8080}"
  # 拷贝自身为 source.sh 并用 python3 / nc 起一个简易服务
  local dir; dir="$(mktemp -d)"
  cp "$SELF_PATH" "$dir/source.sh"
  info "分发目录: $dir  (含 source.sh)"
  info "请在终端B执行下载命令:"
  echo
  printf '  %scurl -fsSL http://<本机IP>:%s/source.sh -o mic_kit.sh && chmod +x mic_kit.sh && ./mic_kit.sh%s\n' \
    "$C_BOLD$C_CYA" "$port" "$C_RESET"
  echo
  info "启动 HTTP 服务 (Ctrl+C 停止)..."
  if has_cmd python3; then
    ( cd "$dir" && python3 -m http.server "$port" --bind 0.0.0.0 )
  elif has_cmd nc; then
    _nc_http_server "$dir" "$port"
  else
    err "需要 python3 或 nc"
  fi
  rm -rf "$dir"
}

# 极简 nc HTTP server (单连接循环)
_nc_http_server() {
  local dir="$1" port="$2"
  local body header
  while true; do
    body="$(cat "$dir/source.sh")"
    header="HTTP/1.1 200 OK\r\nContent-Type: text/x-shellscript\r\nContent-Length: ${#body}\r\nConnection: close\r\n\r\n"
    printf '%b%s' "$header" "$body" | nc -l -p "$port" -q 1 >/dev/null 2>&1
    info "已响应一次请求"
  done
}

_fetch_source() {
  require curl || return 1
  local url; read -rp "${C_DIM}远端 URL (如 http://10.0.0.5:8080/source.sh)${C_RESET}: " url
  [[ -z "$url" ]] && return
  local out; out="${MIC_FETCH_OUT:-./mic_kit.sh}"
  if curl -fsSL "$url" -o "$out"; then
    chmod +x "$out"
    ok "已拉取并保存为 $out"
    info "可执行: ./$out"
  else
    err "拉取失败: $url"
  fi
}

_print_install_cmd() {
  local port; read -rp "${C_DIM}端口 (默认 8080)${C_RESET}: " port; port="${port:-8080}"
  echo
  printf '%s一键安装命令 / one-liner:%s\n' "$C_BOLD" "$C_RESET"
  printf '  curl -fsSL http://<SERVER>:%s/source.sh -o mic_kit.sh \\\n    && chmod +x mic_kit.sh \\\n    && ./mic_kit.sh\n' "$port"
  echo
}

# ---------- 菜单 / Menu ----------
menu_items=(
  "检测音频设备        (Detect audio devices)        [底层 /proc + ALSA + PW]"
  "实时麦克风监听      (Real-time monitor loopback)  [听到自己]"
  "实时电平表          (CLI VU meter)                [RMS bar]"
  "录音到文件          (Record to WAV)               [arecord]"
  "麦克风音量控制      (Volume control)              [wpctl/pactl/amixer]"
  "静音 / 取消静音     (Mute toggle)"
  "麦克风活动检测      (Activity detection)          [阈值触发]"
  "音频子系统状态      (Subsystem status)            [进程 + wpctl]"
  "底层设备信息        (Low-level /proc/asound /dev/snd)"
  "服务器模式          (Server: curl source.sh)      [分发/拉取]"
)

show_menu() {
  printf '\n%s========================================================%s\n' "$C_BOLD$C_BLU" "$C_RESET"
  printf '%s  %s v%s  —  实时麦克风底层监听 Kit (Debian)%s\n' \
    "$C_BOLD$C_CYA" "$PROG_NAME" "$PROG_VERSION" "$C_RESET"
  printf '%s  Tools Chain / Shell CLI  ·  键入序号 + 回车 执行%s\n' "$C_DIM" "$C_RESET"
  printf '%s========================================================%s\n' "$C_BOLD$C_BLU" "$C_RESET"
  local i=1
  for item in "${menu_items[@]}"; do
    printf '  %s%2d%s) %s\n' "$C_BOLD$C_GRN" "$i" "$C_RESET" "$item"
    ((i++))
  done
  printf '  %s 0%s) 退出 / Exit\n' "$C_BOLD$C_RED" "$C_RESET"
  printf '%s--------------------------------------------------------%s\n' "$C_BOLD$C_BLU" "$C_RESET"
}

dispatch() {
  case "$1" in
    1) tc_detect_devices ;;
    2) tc_realtime_monitor ;;
    3) tc_level_meter ;;
    4) tc_record ;;
    5) tc_volume ;;
    6) tc_mute ;;
    7) tc_activity_detect ;;
    8) tc_subsystem_status ;;
    9) tc_lowlevel_info ;;
    10) tc_server_mode ;;
    0|q|Q) info "再见 / bye."; exit 0 ;;
    '') return 0 ;;
    *) err "无效序号 / invalid choice: $1" ;;
  esac
}

main_loop() {
  # 健康检查
  if ! require arecord amixer 2>/dev/null; then
    warn "ALSA 工具缺失, 部分功能不可用. 建议执行:"
    warn "  sudo apt-get install -y alsa-utils pulseaudio-utils pipewire-audio wireplumber curl"
    echo
  fi
  info "当前活动子系统: $(detect_subsystem)  | 录音目录: $REC_DIR"
  while true; do
    show_menu
    local choice
    read -rp "${C_BOLD}键入序号 > ${C_RESET}" choice
    dispatch "$choice"
    pause
  done
}

# ---------- 入口 / Entry ----------
case "${1:-}" in
  -h|--help)
    sed -n '2,18p' "$SELF_PATH"
    exit 0
    ;;
  -v|--version) echo "$PROG_NAME $PROG_VERSION"; exit 0 ;;
  *) main_loop "$@" ;;
esac
