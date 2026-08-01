#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHRONOS CLI — Workgroup Job Management + Isochronic Biological Clock
Runs in Termux / Linux / macOS / WSL.
Pure stdlib, no external dependencies required.
Optional audio: tries termux-media-player, aplay, or ffplay for generated WAV.
Optional TUI: uses standard-library curses.
"""

from __future__ import annotations

import argparse
import curses
import datetime as dt
import json
import math
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
import wave
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# ===== Paths =====
DATA_DIR = Path(os.environ.get("CHRONOS_HOME", Path.home() / ".chronos"))
DATA_FILE = DATA_DIR / "data.json"
AUDIO_DIR = DATA_DIR / "audio"
PRESET_DIR = DATA_DIR / "presets"

# ===== Constants =====
STATUS_TEXT = {"todo": "待办", "in_progress": "进行中", "review": "评审", "done": "完成", "blocked": "阻塞"}
PRIORITY_TEXT = {"urgent": "紧急", "high": "高", "medium": "中", "low": "低"}
PROJECT_STATUS_TEXT = {"planning": "规划", "active": "进行", "paused": "暂停", "completed": "完成"}
PURPOSE_ICON = {"focus": "🧠", "relax": "🌊", "meditate": "🧘", "sleep": "🌙", "energy": "⚡", "custom": "🎵"}
TYPE_TEXT = {"isochronic": "等时", "binaural": "双耳", "monaural": "单耳"}

PRESETS = {
    "focus":    {"freq": 40.0,  "carrier": 200, "duration": 25, "purpose": "focus",    "mode": "isochronic"},
    "relax":    {"freq": 8.0,   "carrier": 180, "duration": 20, "purpose": "relax",    "mode": "isochronic"},
    "meditate": {"freq": 6.0,   "carrier": 150, "duration": 30, "purpose": "meditate", "mode": "isochronic"},
    "sleep":    {"freq": 2.5,   "carrier": 100, "duration": 45, "purpose": "sleep",    "mode": "isochronic"},
    "energy":   {"freq": 15.0,  "carrier": 220, "duration": 15, "purpose": "energy",   "mode": "isochronic"},
    "smr":      {"freq": 13.0,  "carrier": 200, "duration": 20, "purpose": "custom",   "mode": "isochronic"},
    "gamma":    {"freq": 40.0,  "carrier": 250, "duration": 15, "purpose": "focus",    "mode": "isochronic"},
}

# ===== ANSI colors (for plain CLI) =====
class C:
    R = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    IT = "\033[3m"
    UL = "\033[4m"
    # fg
    RED = "\033[31m"
    GRN = "\033[32m"
    YEL = "\033[33m"
    BLU = "\033[34m"
    MAG = "\033[35m"
    CYN = "\033[36m"
    WHT = "\033[37m"
    GRY = "\033[90m"
    # bg
    BRED = "\033[41m"
    BGRN = "\033[42m"
    BYEL = "\033[43m"
    BBLU = "\033[44m"

    def on(tty=True):
        return tty and sys.stdout.isatty()

USE_COLOR = sys.stdout.isatty()

def col(*cs, s: str = None) -> str:
    if not USE_COLOR:
        return s if s is not None else ""
    return "".join(cs) + (s if s is not None else "")

# ===== Data Store =====
def _default_data():
    return {
        "version": 1,
        "projects": [],
        "jobs": [],
        "clockSessions": [],
        "attentionRecords": [],
        "sync": {"lastWebSync": None, "lastCliSync": None, "conflicts": []},
        "meta": {"createdAt": _iso_now(), "updatedAt": _iso_now()},
    }

def _iso_now() -> str:
    return dt.datetime.now().astimezone().isoformat()

def _uid() -> str:
    return str(uuid.uuid4())

class Store:
    data: Dict[str, Any]

    @classmethod
    def load(cls) -> "Store":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        PRESET_DIR.mkdir(parents=True, exist_ok=True)
        s = cls()
        if DATA_FILE.exists():
            try:
                s.data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                defd = _default_data()
                for k, v in defd.items():
                    if k not in s.data:
                        s.data[k] = v
                return s
            except Exception:
                pass
        s.data = _default_data()
        s.seed_demo()
        s.save()
        return s

    def seed_demo(self):
        p1 = _uid()
        self.data["projects"].append({
            "id": p1, "name": "Chronos 时空工作站", "description": "生物钟+项目管理双端MVP",
            "createdAt": _iso_now(),
            "startDate": dt.date.today().isoformat(),
            "endDate": (dt.date.today() + dt.timedelta(days=30)).isoformat(),
            "status": "active", "progress": 35, "members": ["你", "AI"], "tags": ["MVP", "核心"],
        })
        self.data["jobs"].append({
            "id": _uid(), "projectId": p1, "title": "搭建CLI数据层", "description": "纯stdlib实现",
            "assignee": "你", "status": "in_progress", "priority": "high",
            "estimatedHours": 3, "actualHours": 2,
            "dueDate": (dt.date.today() + dt.timedelta(days=1)).isoformat(),
            "createdAt": _iso_now(), "updatedAt": _iso_now(),
            "dependsOn": [], "tags": ["后端"],
        })
        self.data["jobs"].append({
            "id": _uid(), "projectId": p1, "title": "实现等时声频WAV生成", "description": "离线声频",
            "assignee": "你", "status": "todo", "priority": "urgent",
            "estimatedHours": 4, "actualHours": 0,
            "dueDate": (dt.date.today() + dt.timedelta(days=2)).isoformat(),
            "createdAt": _iso_now(), "updatedAt": _iso_now(),
            "dependsOn": [], "tags": ["音频"],
        })

    def save(self):
        self.data["meta"]["updatedAt"] = _iso_now()
        tmp = DATA_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DATA_FILE)

    # ===== Projects =====
    def projects(self) -> List[Dict]:
        return sorted(self.data["projects"], key=lambda p: p["createdAt"], reverse=True)

    def add_project(self, **kw):
        kw.setdefault("id", _uid())
        kw.setdefault("createdAt", _iso_now())
        kw.setdefault("progress", 0)
        kw.setdefault("members", [])
        kw.setdefault("tags", [])
        self.data["projects"].append(kw)
        self.save()
        return kw

    def update_project(self, id: str, **kw):
        for p in self.data["projects"]:
            if p["id"] == id:
                p.update(kw)
                self.save()
                return p
        return None

    def del_project(self, id: str):
        self.data["projects"] = [p for p in self.data["projects"] if p["id"] != id]
        self.data["jobs"] = [j for j in self.data["jobs"] if j.get("projectId") != id]
        self.save()

    # ===== Jobs =====
    def jobs(self, project_id=None, status=None, priority=None) -> List[Dict]:
        r = list(self.data["jobs"])
        if project_id: r = [j for j in r if j.get("projectId") == project_id]
        if status: r = [j for j in r if j.get("status") == status]
        if priority: r = [j for j in r if j.get("priority") == priority]
        return sorted(r, key=lambda j: j.get("updatedAt", ""), reverse=True)

    def add_job(self, **kw):
        kw.setdefault("id", _uid())
        kw.setdefault("createdAt", _iso_now())
        kw.setdefault("updatedAt", _iso_now())
        kw.setdefault("dependsOn", [])
        kw.setdefault("tags", [])
        kw.setdefault("status", "todo")
        kw.setdefault("priority", "medium")
        kw.setdefault("actualHours", 0)
        kw.setdefault("estimatedHours", 1)
        self.data["jobs"].append(kw)
        self._recompute_progress(kw.get("projectId"))
        self.save()
        return kw

    def update_job(self, id: str, **kw):
        for j in self.data["jobs"]:
            if j["id"] == id:
                j.update(kw)
                j["updatedAt"] = _iso_now()
                self._recompute_progress(j.get("projectId"))
                self.save()
                return j
        return None

    def move_job(self, id: str, new_status: str):
        return self.update_job(id, status=new_status)

    def del_job(self, id: str):
        j = next((x for x in self.data["jobs"] if x["id"] == id), None)
        self.data["jobs"] = [x for x in self.data["jobs"] if x["id"] != id]
        if j: self._recompute_progress(j.get("projectId"))
        self.save()

    def _recompute_progress(self, project_id: str):
        if not project_id: return
        jobs = [j for j in self.data["jobs"] if j.get("projectId") == project_id]
        if not jobs: return
        done = sum(1 for j in jobs if j.get("status") == "done")
        rev = sum(1 for j in jobs if j.get("status") == "review")
        pct = int(round(((done + rev * 0.5) / len(jobs)) * 100))
        for p in self.data["projects"]:
            if p["id"] == project_id:
                p["progress"] = pct
                return

    # ===== Sessions =====
    def add_session(self, **kw):
        kw.setdefault("id", _uid())
        kw.setdefault("startedAt", _iso_now())
        self.data["clockSessions"].append(kw)
        self.save()
        return kw

    def update_session(self, id: str, **kw):
        for s in self.data["clockSessions"]:
            if s["id"] == id:
                s.update(kw)
                self.save()
                return s
        return None

    def sessions(self, limit=20):
        return sorted(self.data["clockSessions"], key=lambda s: s["startedAt"], reverse=True)[:limit]

    # ===== Attention =====
    def add_attention(self, **kw):
        kw.setdefault("id", _uid())
        kw.setdefault("timestamp", _iso_now())
        self.data["attentionRecords"].append(kw)
        self.save()
        return kw

    def list_attention(self, limit=50):
        return sorted(self.data["attentionRecords"], key=lambda r: r["timestamp"], reverse=True)[:limit]

    # ===== Export / Import =====
    def export_json(self) -> str:
        self.data["sync"]["lastCliSync"] = _iso_now()
        self.save()
        return json.dumps(self.data, ensure_ascii=False, indent=2)

    def import_json(self, incoming: Dict, merge=True):
        if not merge:
            self.data = incoming
            self.save()
            return
        def merge_list(key: str, ts_key: str):
            existing = self.data.get(key) or []
            inc = incoming.get(key) or []
            m = {item["id"]: item for item in existing}
            for item in inc:
                cur = m.get(item["id"])
                if not cur:
                    m[item["id"]] = item
                    continue
                cur_t = cur.get(ts_key) or cur.get("createdAt") or ""
                inc_t = item.get(ts_key) or item.get("createdAt") or ""
                if inc_t >= cur_t:
                    m[item["id"]] = item
            self.data[key] = list(m.values())
        merge_list("projects", "updatedAt")
        merge_list("jobs", "updatedAt")
        merge_list("clockSessions", "endedAt")
        merge_list("attentionRecords", "timestamp")
        sync = {**(self.data.get("sync") or {}), **(incoming.get("sync") or {})}
        sync["lastCliSync"] = _iso_now()
        self.data["sync"] = sync
        self.data["version"] = max(int(self.data.get("version") or 1), int(incoming.get("version") or 1) + 1)
        self.save()

# ===== Audio (Isochronic WAV generator) =====
def _write_wav(path: Path, samples: List[float], sample_rate: int = 44100, channels: int = 1):
    """Write float samples in [-1,1] to 16-bit PCM WAV."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        n = len(samples)
        frames = bytearray()
        for i in range(0, n, channels):
            for c in range(channels):
                v = samples[i + c] if i + c < n else 0.0
                v = max(-1.0, min(1.0, v))
                frames += int(v * 32767).to_bytes(2, "little", signed=True)
        w.writeframes(bytes(frames))

def _find_audio_player() -> Optional[str]:
    for c in ["termux-media-player", "play", "aplay", "paplay", "ffplay", "mpv", "afplay"]:
        if shutil.which(c):
            return c
    return None

def _play_wav(path: Path, player: str) -> Optional[subprocess.Popen]:
    try:
        if player == "termux-media-player":
            return subprocess.Popen(["termux-media-player", "play", str(path)])
        if player == "ffplay":
            return subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)])
        if player == "mpv":
            return subprocess.Popen(["mpv", "--no-video", "--term-osd=off", str(path)])
        return subprocess.Popen([player, str(path)])
    except Exception:
        return None

def generate_isochronic_wav(freq: float, carrier: float, duration_sec: float,
                            vol: float = 0.7, mode: str = "isochronic",
                            sample_rate: int = 44100) -> Path:
    """Generate isochronic/monaural/binaural WAV and return path."""
    filename = f"bio_{mode}_{freq:.1f}Hz_{carrier}Hz_{int(duration_sec)}s_{int(time.time())}.wav"
    out = AUDIO_DIR / filename
    n = int(sample_rate * duration_sec)
    fade = min(0.5, duration_sec * 0.05)  # fade-in/out 5% or 0.5s
    fade_n = int(sample_rate * fade)

    if mode == "binaural":
        samples = [0.0] * (2 * n)  # interleaved L,R
        for i in range(n):
            t = i / sample_rate
            # Fade
            f = 1.0
            if i < fade_n: f = i / fade_n
            elif i > n - fade_n: f = (n - i) / fade_n
            L = math.sin(2 * math.pi * carrier * t)
            R = math.sin(2 * math.pi * (carrier + freq) * t)
            samples[2 * i]     = vol * f * 0.5 * L
            samples[2 * i + 1] = vol * f * 0.5 * R
        _write_wav(out, samples, sample_rate, 2)
        return out

    # isochronic / monaural -> mono
    samples = [0.0] * n
    if mode == "monaural":
        # sine amplitude modulation (smooth beating)
        for i in range(n):
            t = i / sample_rate
            f = 1.0
            if i < fade_n: f = i / fade_n
            elif i > n - fade_n: f = (n - i) / fade_n
            envelope = 0.5 + 0.45 * math.sin(2 * math.pi * freq * t)
            carrier_s = math.sin(2 * math.pi * carrier * t)
            samples[i] = vol * f * envelope * carrier_s
    else:  # isochronic (square-pulse modulation)
        period = 1.0 / freq
        # Pulse duty cycle ~ 50% but very quick risetime to give sharp clicks
        # Use trapezoidal pulse with short 2ms transitions
        tr = 0.002  # transition 2ms
        for i in range(n):
            t = i / sample_rate
            f = 1.0
            if i < fade_n: f = i / fade_n
            elif i > n - fade_n: f = (n - i) / fade_n
            phase = (t % period) / period  # 0..1
            # trapezoid envelope from ~0 to 1
            if phase < 0.5:
                if phase < tr / period:
                    env = phase * period / tr  # 0..1 in tr
                elif phase < 0.5 - tr / period:
                    env = 1.0
                else:
                    env = max(0.0, 1.0 - (phase - (0.5 - tr / period)) * period / tr)
            else:
                env = 0.0
            samples[i] = vol * f * (0.02 + 0.96 * env) * math.sin(2 * math.pi * carrier * t)
    _write_wav(out, samples, sample_rate, 1)
    return out

# ===== Pretty printing =====
def _fmt_time(iso: str) -> str:
    try:
        d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.astimezone().strftime("%m-%d %H:%M")
    except Exception:
        return iso

def _status_color(status: str) -> str:
    return {"todo": C.GRY, "in_progress": C.BLU, "review": C.MAG, "done": C.GRN, "blocked": C.RED}.get(status, "")

def _priority_color(p: str) -> str:
    return {"urgent": C.RED, "high": C.YEL, "medium": C.CYN, "low": C.GRY}.get(p, "")

def header(s: str, width=78, char="═"):
    s = f" {s} "
    pad = max(0, width - len(s))
    l = pad // 2
    r = pad - l
    print(col(C.BOLD, C.CYN) + char * l + s + char * r + col(C.R))

def bar(pct: int, w: int = 30) -> str:
    n = int(round(pct / 100 * w))
    filled = col(C.BGRN, " " * n, C.R)
    empty = col(C.DIM) + "░" * (w - n) + col(C.R)
    return filled + empty + f" {pct:3d}%"

def box(title: str = None):
    print()

# ===== Interactive REPL =====
class REPL:
    def __init__(self, store: Store):
        self.store = store
        self._player_proc = None

    def run(self):
        print(col(C.BOLD, C.CYN) + r"""
  ________                             ________    ____
 / ____/ /_  _________  ____  ____  __/ __/ __ \  / __/
/ /   / __ \/ ___/ __ \/ __ \/ __ \/ / / / / / / / /_
/ /___/ / / / /  / /_/ / / / / /_/ / / / /_/ / / / __/
\____/_/ /_/_/   \____/_/ /_/\__, /  \_/\____(_)_/
                            /____/
""" + col(C.R))
        print(col(C.DIM) + "  时空工作站 · Termux CLI v1.0  |  h 查看帮助  |  q 退出" + col(C.R))
        print()
        self._welcome_stats()
        while True:
            try:
                line = input(col(C.BOLD, C.CYN) + "chronos" + col(C.R) + col(C.BOLD) + "> " + col(C.R)).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line in ("quit", "exit", "q", "bye"):
                break
            self._dispatch(line)

    def _welcome_stats(self):
        s = self.store
        active_p = sum(1 for p in s.projects() if p.get("status") == "active")
        pending_j = sum(1 for j in s.jobs() if j.get("status") != "done")
        today = dt.date.today().isoformat()
        tod_focus = sum(int(x.get("durationMinutes") or 0) for x in s.sessions(500)
                        if x.get("completed") and x["startedAt"][:10] == today
                        and x.get("purpose") in ("focus", "energy"))
        print(col(C.DIM) + f"  📁 活跃项目 {active_p}  |  📝 待办任务 {pending_j}  |  🧠 今日专注 {tod_focus} 分钟" + col(C.R))
        print()

    def _dispatch(self, line: str):
        parts = shlex.split(line)
        cmd = parts[0].lower()
        args = parts[1:]
        try:
            if cmd in ("help", "h", "?"):
                self._help()
            elif cmd in ("dashboard", "db", "home"):
                self._welcome_stats(); self._cmd_dashboard()
            elif cmd in ("projects", "p", "ps"):
                self._cmd_projects(args)
            elif cmd in ("project", "proj"):
                self._cmd_project_detail(args)
            elif cmd in ("add-project", "new-project", "np"):
                self._cmd_add_project(args)
            elif cmd in ("edit-project", "ep"):
                self._cmd_edit_project(args)
            elif cmd in ("del-project", "dp", "rm-project"):
                self._cmd_del_project(args)
            elif cmd in ("jobs", "j", "ls"):
                self._cmd_jobs(args)
            elif cmd in ("add-job", "nj", "new-job"):
                self._cmd_add_job(args)
            elif cmd in ("edit-job", "ej"):
                self._cmd_edit_job(args)
            elif cmd in ("move-job", "mvj"):
                self._cmd_move_job(args)
            elif cmd in ("del-job", "dj", "rm-job"):
                self._cmd_del_job(args)
            elif cmd in ("kanban", "kb", "board"):
                self._cmd_kanban()
            elif cmd in ("bioclock", "bio", "bc"):
                self._cmd_list_sessions(args)
            elif cmd in ("focus", "relax", "meditate", "sleep", "energy", "smr", "gamma"):
                self._cmd_preset_session(cmd, args)
            elif cmd in ("play", "session", "run"):
                self._cmd_play_session(args)
            elif cmd in ("stop-session", "stop"):
                self._cmd_stop_session()
            elif cmd in ("attention", "att", "a"):
                self._cmd_attention(args)
            elif cmd in ("add-attention", "na", "note-att"):
                self._cmd_add_attention(args)
            elif cmd in ("sync", "sync-status"):
                self._cmd_sync_status()
            elif cmd in ("export", "exp"):
                self._cmd_export(args)
            elif cmd in ("import", "imp"):
                self._cmd_import(args)
            elif cmd in ("tui", "ncurses", "gui"):
                run_tui(self.store)
            elif cmd in ("clear", "cls"):
                print("\033c", end="")
            elif cmd in ("version", "v"):
                print("CHRONOS CLI 1.0.0 — pure stdlib")
                print(f"  数据文件: {DATA_FILE}")
                print(f"  音频目录: {AUDIO_DIR}")
            else:
                print(col(C.RED) + f"未知命令: {cmd}  — 输入 h 查看帮助" + col(C.R))
        except Exception as e:
            print(col(C.RED) + f"执行出错: {e}" + col(C.R))
            if os.environ.get("CHRONOS_DEBUG"):
                import traceback
                traceback.print_exc()

    def _help(self):
        hlp = """
项目管理:
  projects / p              项目列表
  project <ID|#N>           项目详情
  add-project 交互式新建项目（或 add-project -n 名称 [-s status] [-m 成员...]）
  edit-project <ID|#N> [-f k=v ...]  编辑项目
  del-project  <ID|#N>      删除项目

任务管理:
  jobs / j [--project ID] [--status S] [--priority P]   任务列表
  kanban / kb              看板视图
  add-job  交互式新建任务
  edit-job <ID|#N> [-f k=v ...]
  move-job <ID|#N> <todo|in_progress|review|done|blocked>
  del-job  <ID|#N>

生物钟 / 声频:
  bioclock / bc [--limit N]        历史 session
  focus [分钟] [freq]              快速启动专注模式 (默认40Hz 25min)
  relax | meditate | sleep | energy | smr | gamma   其他预设
  play --freq 40 --carrier 200 --min 15 [--mode isochronic|binaural|monaural]
  stop-session                     停止正在播放的音频

注意力 / 状态:
  attention [--limit N]            历史注意力记录
  add-attention                    交互式记录当前状态

同步 / 数据:
  sync-status / sync               同步状态概览
  export [路径]                    导出 JSON (默认 stdout)
  import <路径或->                 从文件 / stdin 合并 JSON
  tui / ncurses                    启动 curses 终端 UI
  clear / cls                      清屏
  version / v                      版本信息
  quit / q                         退出
"""
        print(hlp)

    # ==== Projects ====
    def _cmd_projects(self, args):
        ps = self.store.projects()
        if not ps:
            print(col(C.YEL) + "无项目。使用 add-project 新建。" + col(C.R))
            return
        header(f"项目列表  共 {len(ps)} 项")
        for i, p in enumerate(ps, 1):
            jobs = self.store.jobs(project_id=p["id"])
            done = sum(1 for j in jobs if j.get("status") == "done")
            st = PROJECT_STATUS_TEXT.get(p.get("status"), p.get("status","?"))
            sc = {"planning": C.YEL, "active": C.BLU, "paused": C.GRY, "completed": C.GRN}.get(p.get("status"), "")
            members = ",".join(p.get("members") or []) or "-"
            tags = " ".join(f"#{t}" for t in (p.get("tags") or []))
            print(f"{col(C.BOLD)}{i:2}. {col(C.R)}{col(sc)}{st:<4}{col(C.R)}  {col(C.BOLD)}{p['name']}{col(C.R)}  "
                  f"{col(C.DIM)}{p.get('startDate','?')}~{p.get('endDate','?')}{col(C.R)}")
            print(f"     ID: {col(C.CYN)}{p['id'][:12]}…{col(C.R)}  👥 {members}  "
                  f"📋 {len(jobs)}任务 ({done}完成)  {col(C.DIM)}{tags}{col(C.R)}")
            print(f"     进度: {bar(int(p.get('progress',0)), 40)}")
            if p.get("description"):
                for ln in textwrap.wrap(p["description"], width=72, initial_indent="     ", subsequent_indent="     "):
                    print(col(C.DIM) + ln + col(C.R))
            print()

    def _cmd_project_detail(self, args):
        if not args:
            print(col(C.RED) + "需要项目 ID 或编号" + col(C.R))
            return
        p = self._resolve_project(args[0])
        if not p:
            print(col(C.RED) + "项目不存在" + col(C.R)); return
        header(f"项目详情: {p['name']}")
        for k, v in p.items():
            if k == "id": continue
            print(f"  {k:>14}: {v}")
        jobs = self.store.jobs(project_id=p["id"])
        print(f"\n  {col(C.BOLD)}关联任务 {len(jobs)}:{col(C.R)}")
        for j in jobs:
            sc = _status_color(j.get("status"))
            print(f"    · {col(sc)}{STATUS_TEXT.get(j.get('status'),j.get('status')):<5}{col(C.R)} "
                  f"{col(_priority_color(j.get('priority')))}[{PRIORITY_TEXT.get(j.get('priority'),'')}]{col(C.R)} "
                  f"{j['title']} {col(C.DIM)}({j.get('assignee','-')}, {j.get('actualHours',0)}/{j.get('estimatedHours',0)}h){col(C.R)}")

    def _resolve_project(self, ref: str) -> Optional[Dict]:
        ps = self.store.projects()
        if ref.startswith("#") and ref[1:].isdigit():
            idx = int(ref[1:]) - 1
            if 0 <= idx < len(ps): return ps[idx]
        if ref.isdigit():
            idx = int(ref) - 1
            if 0 <= idx < len(ps): return ps[idx]
        for p in ps:
            if p["id"] == ref or p["id"].startswith(ref):
                return p
        return None

    def _resolve_job(self, ref: str) -> Optional[Dict]:
        js = self.store.jobs()
        if ref.startswith("#") and ref[1:].isdigit():
            idx = int(ref[1:]) - 1
            if 0 <= idx < len(js): return js[idx]
        if ref.isdigit():
            idx = int(ref) - 1
            if 0 <= idx < len(js): return js[idx]
        for j in js:
            if j["id"] == ref or j["id"].startswith(ref):
                return j
        return None

    def _prompt(self, msg: str, default: str = "") -> str:
        d = f" [{default}]" if default else ""
        v = input(f"{msg}{d}: ").strip()
        return v or default

    def _cmd_add_project(self, args):
        ap = argparse.ArgumentParser(prog="add-project")
        ap.add_argument("-n", "--name", default=None)
        ap.add_argument("-d", "--desc", default=None)
        ap.add_argument("-s", "--status", default="planning", choices=list(PROJECT_STATUS_TEXT))
        ap.add_argument("--start", default=None)
        ap.add_argument("--end", default=None)
        ap.add_argument("-m", "--members", nargs="*", default=[])
        ap.add_argument("-t", "--tags", nargs="*", default=[])
        try:
            ns = ap.parse_args(args)
        except SystemExit: return
        interactive = not ns.name
        name = ns.name or self._prompt("项目名称")
        if not name:
            print(col(C.RED) + "名称必填" + col(C.R)); return
        desc = ns.desc or (self._prompt("描述", "") if interactive else "")
        status = ns.status
        start = ns.start or (self._prompt("开始日期 YYYY-MM-DD", dt.date.today().isoformat()) if interactive else dt.date.today().isoformat())
        end = ns.end or (self._prompt("结束日期 YYYY-MM-DD", (dt.date.today()+dt.timedelta(days=14)).isoformat()) if interactive else (dt.date.today()+dt.timedelta(days=14)).isoformat())
        members = ns.members or ([s.strip() for s in self._prompt("成员 逗号分隔", "").split(",") if s.strip()] if interactive else [])
        tags = ns.tags or ([s.strip() for s in self._prompt("标签 逗号分隔", "").split(",") if s.strip()] if interactive else [])
        p = self.store.add_project(name=name, description=desc, status=status, startDate=start, endDate=end, members=members, tags=tags)
        print(col(C.GRN) + f"✅ 已创建项目: {p['name']}  ID={p['id']}" + col(C.R))

    def _cmd_edit_project(self, args):
        if not args:
            print(col(C.RED) + "需要项目 ID 或编号" + col(C.R)); return
        p = self._resolve_project(args[0])
        if not p:
            print(col(C.RED) + "项目不存在" + col(C.R)); return
        ap = argparse.ArgumentParser(prog="edit-project")
        ap.add_argument("-f", "--field", action="append", default=[])
        try:
            ns = ap.parse_args(args[1:])
        except SystemExit: return
        fields = {}
        for f in ns.field:
            if "=" in f:
                k, v = f.split("=", 1)
                if k in ("members", "tags"):
                    fields[k] = [s.strip() for s in v.split(",") if s.strip()]
                else:
                    fields[k] = v
        if not fields:
            # interactive
            for k in ["name", "description", "status", "startDate", "endDate"]:
                cur = p.get(k, "")
                if isinstance(cur, list): cur = ",".join(cur)
                v = self._prompt(f"  {k}", str(cur) if cur is not None else "")
                if k in ("members", "tags"):
                    fields[k] = [s.strip() for s in v.split(",") if s.strip()]
                else:
                    fields[k] = v
        self.store.update_project(p["id"], **fields)
        print(col(C.GRN) + "✅ 已更新" + col(C.R))

    def _cmd_del_project(self, args):
        if not args:
            print(col(C.RED) + "需要项目 ID 或编号" + col(C.R)); return
        p = self._resolve_project(args[0])
        if not p:
            print(col(C.RED) + "项目不存在" + col(C.R)); return
        c = input(f"确定删除项目 [{p['name']}] 及其全部任务? (y/N): ").strip().lower()
        if c == "y":
            self.store.del_project(p["id"])
            print(col(C.GRN) + "已删除" + col(C.R))

    # ==== Jobs ====
    def _cmd_jobs(self, args):
        ap = argparse.ArgumentParser(prog="jobs")
        ap.add_argument("-p", "--project", default=None)
        ap.add_argument("-s", "--status", default=None)
        ap.add_argument("-P", "--priority", default=None)
        ap.add_argument("-l", "--limit", type=int, default=None)
        try:
            ns = ap.parse_args(args)
        except SystemExit: return
        project_id = None
        if ns.project:
            p = self._resolve_project(ns.project)
            project_id = p["id"] if p else None
        jobs = self.store.jobs(project_id=project_id, status=ns.status, priority=ns.priority)
        if ns.limit: jobs = jobs[:ns.limit]
        if not jobs:
            print(col(C.YEL) + "无匹配任务" + col(C.R)); return
        header(f"任务列表  {len(jobs)} 项")
        for i, j in enumerate(jobs, 1):
            p = next((x for x in self.store.projects() if x["id"] == j.get("projectId")), None)
            sc = _status_color(j.get("status"))
            pc = _priority_color(j.get("priority"))
            st = STATUS_TEXT.get(j.get("status"), j.get("status", "?"))
            pr = PRIORITY_TEXT.get(j.get("priority"), j.get("priority", "?"))
            due = j.get("dueDate") or ""
            due_s = ""
            if due:
                try:
                    dd = dt.date.fromisoformat(due)
                    days = (dd - dt.date.today()).days
                    if days < 0: due_s = col(C.RED) + f" 逾期{-days}d" + col(C.R)
                    elif days == 0: due_s = col(C.YEL) + " 今天到期" + col(C.R)
                    else: due_s = f" 还剩{days}d"
                except Exception: pass
            print(f"{col(C.BOLD)}{i:3}. {col(C.R)}"
                  f"{col(sc)}{st:<5}{col(C.R)} "
                  f"{col(pc)}[{pr:<2}]{col(C.R)} "
                  f"{col(C.BOLD)}{j['title']}{col(C.R)}")
            print(f"     {col(C.DIM)}ID {j['id'][:12]}…{col(C.R)}  "
                  f"📁 {p['name'] if p else '-'}  👤 {j.get('assignee','-')}  "
                  f"⏱ {j.get('actualHours',0)}/{j.get('estimatedHours',0)}h  📅 {due or '-'}{due_s}  "
                  f"{col(C.DIM)}{_fmt_time(j.get('updatedAt',''))}{col(C.R)}")
            if j.get("description"):
                for ln in textwrap.wrap(j["description"], width=72, initial_indent="     ", subsequent_indent="     "):
                    print(col(C.DIM, C.IT) + ln + col(C.R))
            print()

    def _cmd_kanban(self):
        cols = [("todo", "待办"), ("in_progress", "进行"), ("review", "评审"), ("done", "完成")]
        width = 34
        header("KANBAN 看板", width=width * 4 + len(cols) + 1, char="─")
        def pad(s: str, n: int) -> str:
            s = str(s)
            if len(s) > n:
                return s[:n-1] + "…"
            return s + " " * (n - len(s))
        print("│" + "│".join(f"{col(C.BOLD,C.CYN)}{pad(t, width)}{col(C.R)}" for _, t in cols) + "│")
        col_lists = {s: self.store.jobs(status=s) for s, _ in cols}
        for _, name in cols:
            print("├" + "─" * width, end="")
        print("┤")
        max_rows = max((len(v) for v in col_lists.values()), default=0)
        for r in range(max_rows):
            row_parts = []
            for s, _ in cols:
                jobs = col_lists[s]
                if r < len(jobs):
                    j = jobs[r]
                    pc = _priority_color(j.get("priority"))
                    pr = PRIORITY_TEXT.get(j.get("priority"), j.get("priority",""))
                    txt = f"{col(pc)}[{pr[:1]}]{col(C.R)} {j['title'][:width-5]}"
                    ansi_stripped = j['title'][:width-5] + "[X]"
                    pad_n = width - 2 - len(ansi_stripped) + len(f"[{pr[:1]}] ")
                    # simple padding
                    visible_len = len(j['title'][:width-5]) + 3
                    txt += " " * max(0, width - visible_len - 2)
                else:
                    txt = " " * (width - 2)
                row_parts.append(txt)
            print("│ " + " │ ".join(row_parts) + " │")

    def _cmd_add_job(self, args):
        projects = self.store.projects()
        if not projects:
            print(col(C.RED) + "请先创建项目" + col(C.R)); return
        title = self._prompt("任务标题")
        if not title:
            print(col(C.RED) + "标题必填" + col(C.R)); return
        print("选择项目:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p['name']}")
        idx = int(self._prompt("序号", "1")) - 1
        project_id = projects[max(0, min(idx, len(projects)-1))]["id"]
        desc = self._prompt("描述", "")
        print("状态: todo in_progress review done blocked")
        status = self._prompt("状态", "todo")
        print("优先级: urgent high medium low")
        priority = self._prompt("优先级", "medium")
        assignee = self._prompt("负责人", "你")
        due = self._prompt("截止日期 YYYY-MM-DD", (dt.date.today()+dt.timedelta(days=7)).isoformat())
        est = float(self._prompt("预估工时 (h)", "1"))
        act = float(self._prompt("实际工时 (h)", "0"))
        tags = [s.strip() for s in self._prompt("标签 逗号分隔", "").split(",") if s.strip()]
        j = self.store.add_job(projectId=project_id, title=title, description=desc, status=status,
                               priority=priority, assignee=assignee, dueDate=due,
                               estimatedHours=est, actualHours=act, tags=tags)
        print(col(C.GRN) + f"✅ 任务已创建 ID={j['id']}" + col(C.R))

    def _cmd_edit_job(self, args):
        if not args:
            print(col(C.RED) + "需要任务 ID 或编号" + col(C.R)); return
        j = self._resolve_job(args[0])
        if not j:
            print(col(C.RED) + "任务不存在" + col(C.R)); return
        ap = argparse.ArgumentParser(prog="edit-job")
        ap.add_argument("-f", "--field", action="append", default=[])
        try:
            ns = ap.parse_args(args[1:])
        except SystemExit: return
        fields = {}
        for f in ns.field:
            if "=" in f:
                k, v = f.split("=", 1)
                if k == "tags":
                    fields[k] = [s.strip() for s in v.split(",") if s.strip()]
                elif k in ("estimatedHours", "actualHours"):
                    try: fields[k] = float(v)
                    except: pass
                else:
                    fields[k] = v
        if not fields:
            for k in ["title", "description", "status", "priority", "assignee", "dueDate", "estimatedHours", "actualHours"]:
                cur = j.get(k, "")
                if isinstance(cur, float): cur = f"{cur}"
                v = self._prompt(f"  {k}", str(cur) if cur is not None else "")
                if k in ("estimatedHours", "actualHours"):
                    try: fields[k] = float(v)
                    except: pass
                elif k == "tags":
                    fields[k] = [s.strip() for s in v.split(",") if s.strip()]
                else:
                    fields[k] = v
        self.store.update_job(j["id"], **fields)
        print(col(C.GRN) + "✅ 已更新" + col(C.R))

    def _cmd_move_job(self, args):
        if len(args) < 2:
            print(col(C.RED) + "用法: move-job <ID> <todo|in_progress|review|done|blocked>" + col(C.R)); return
        j = self._resolve_job(args[0])
        if not j:
            print(col(C.RED) + "任务不存在" + col(C.R)); return
        new_s = args[1]
        if new_s not in STATUS_TEXT:
            print(col(C.RED) + f"非法状态: {new_s}  可选: {', '.join(STATUS_TEXT)}" + col(C.R)); return
        self.store.move_job(j["id"], new_s)
        print(col(C.GRN) + f"✅ 已更新为 {STATUS_TEXT[new_s]}" + col(C.R))

    def _cmd_del_job(self, args):
        if not args: return
        j = self._resolve_job(args[0])
        if not j: print(col(C.RED) + "任务不存在" + col(C.R)); return
        c = input(f"删除任务 [{j['title']}]? (y/N): ").strip().lower()
        if c == "y":
            self.store.del_job(j["id"])
            print(col(C.GRN) + "已删除" + col(C.R))

    # ==== Sessions ====
    def _cmd_list_sessions(self, args):
        ap = argparse.ArgumentParser(prog="bioclock")
        ap.add_argument("-l", "--limit", type=int, default=15)
        try:
            ns = ap.parse_args(args)
        except SystemExit: return
        sessions = self.store.sessions(ns.limit)
        if not sessions:
            print(col(C.YEL) + "无 session 历史。使用 focus|play 启动。" + col(C.R)); return
        header(f"生物钟历史  {len(sessions)} 项")
        for s in sessions:
            icon = PURPOSE_ICON.get(s.get("purpose"), "🎵")
            ttype = TYPE_TEXT.get(s.get("type"), s.get("type", "?"))
            done = "✅" if s.get("completed") else "⏹"
            print(f"  {icon} {col(C.BOLD)}{s.get('frequencyHz'):>5.1f}{col(C.R)}Hz "
                  f"({ttype}, 载波{s.get('carrierFrequencyHz')}Hz) · "
                  f"{s.get('durationMinutes')}分钟 {done} · {col(C.DIM)}{_fmt_time(s['startedAt'])}{col(C.R)}")

    def _cmd_preset_session(self, preset: str, args):
        ps = PRESETS.get(preset)
        if not ps:
            print(col(C.RED) + "未知预设" + col(C.R)); return
        duration = ps["duration"]
        freq = ps["freq"]
        if args and args[0].replace(".", "").isdigit():
            v = float(args[0])
            if v < 60:  # treat as minutes if < 60
                duration = int(v)
            else:
                freq = v
            if len(args) > 1 and args[1].replace(".", "").isdigit():
                freq = float(args[1])
        carrier = ps["carrier"]
        mode = ps["mode"]
        purpose = ps["purpose"]
        self._run_session(freq=freq, carrier=carrier, duration_min=duration, mode=mode, purpose=purpose)

    def _cmd_play_session(self, args):
        ap = argparse.ArgumentParser(prog="play")
        ap.add_argument("--freq", type=float, default=10.0)
        ap.add_argument("--carrier", type=int, default=200)
        ap.add_argument("--min", type=int, default=15)
        ap.add_argument("--mode", default="isochronic", choices=["isochronic", "binaural", "monaural"])
        ap.add_argument("--vol", type=float, default=0.7)
        ap.add_argument("--purpose", default="custom")
        try:
            ns = ap.parse_args(args)
        except SystemExit: return
        self._run_session(freq=ns.freq, carrier=ns.carrier, duration_min=ns.min,
                          mode=ns.mode, purpose=ns.purpose, vol=ns.vol)

    def _run_session(self, freq: float, carrier: int, duration_min: int,
                     mode: str, purpose: str, vol: float = 0.7):
        duration_sec = duration_min * 60
        print(col(C.BOLD, C.MAG) +
              f"🎵 启动 {TYPE_TEXT.get(mode,mode)}声频 | {freq:.1f}Hz | 载波 {carrier}Hz | {duration_min} 分钟 | 目标: {purpose}" +
              col(C.R))
        player = _find_audio_player()
        print(col(C.DIM) + f"  音频播放器: {player or '未检测到 (仅视觉脉冲)'}" + col(C.R))

        # Record session
        sess = self.store.add_session(
            type=mode, frequencyHz=freq, carrierFrequencyHz=carrier,
            durationMinutes=duration_min, purpose=purpose,
            volume=int(vol * 100), completed=False
        )

        # Generate WAV first (so we can begin playback at t=0)
        wav_path: Optional[Path] = None
        proc: Optional[subprocess.Popen] = None
        try:
            wav_path = generate_isochronic_wav(freq=freq, carrier=carrier,
                                               duration_sec=duration_sec,
                                               vol=vol, mode=mode)
            print(col(C.DIM) + f"  生成 WAV: {wav_path} ({wav_path.stat().st_size//1024} KB)" + col(C.R))
            if player:
                proc = _play_wav(wav_path, player)
                if proc:
                    self._player_proc = proc
                    print(col(C.GRN) + f"  ▶ 已启动 {player}" + col(C.R))
        except Exception as e:
            print(col(C.YEL) + f"  ⚠ WAV 生成/播放失败: {e} (继续视觉节拍)" + col(C.R))

        # Visual progress with pulse aligned to beat
        print()
        print(col(C.DIM) + "  Ctrl+C 结束" + col(C.R))
        pulse_period = 1.0 / freq
        start_t = time.time()
        ended_by_user = False
        try:
            while True:
                elapsed = time.time() - start_t
                if elapsed >= duration_sec:
                    break
                rem = duration_sec - elapsed
                em, es = divmod(int(elapsed), 60)
                rm, rs = divmod(int(rem), 60)
                # Pulse indicator
                phase = (time.time() % pulse_period) / pulse_period
                # Bright at pulse peak
                is_peak = phase < 0.08
                pulse_char = col(C.BOLD, C.MAG) + ("▓" if is_peak else "░") + col(C.R)
                # Progress bar
                pct = int(elapsed / duration_sec * 100)
                bar_w = 40
                n = int(pct / 100 * bar_w)
                pb = col(C.BGRN) + " " * n + col(C.R) + col(C.DIM) + "░" * (bar_w - n) + col(C.R)
                sys.stdout.write(
                    f"\r  {pulse_char}  {em:02d}:{es:02d} / {rm:02d}:{rs:02d} |{pb}| {pct:3d}%  "
                    f" {PURPOSE_ICON.get(purpose,'')} {purpose}  "
                )
                sys.stdout.flush()
                time.sleep(0.08)
        except KeyboardInterrupt:
            ended_by_user = True
            print()
            print(col(C.YEL) + "  ⏹ 用户中断" + col(C.R))

        # Clean up player
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try: proc.kill()
                except Exception: pass
        # termux-media-player has no process handle we wait on; try to stop it
        try:
            if shutil.which("termux-media-player"):
                subprocess.run(["termux-media-player", "stop"], capture_output=True)
        except Exception: pass
        self._player_proc = None
        elapsed_final = time.time() - start_t
        completed_frac = elapsed_final / duration_sec
        self.store.update_session(sess["id"], endedAt=_iso_now(), completed=completed_frac >= 0.9)
        if completed_frac >= 0.9 or (not ended_by_user):
            print(col(C.GRN) + "\n✅ 疗程完成" + col(C.R))
        else:
            print(col(C.YEL) + f"\n⏹ 已停止 (完成度 {int(completed_frac*100)}%)" + col(C.R))
        # cleanup old wavs (keep last 5)
        try:
            wavs = sorted(AUDIO_DIR.glob("bio_*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in wavs[5:]:
                old.unlink()
        except Exception: pass

    def _cmd_stop_session(self):
        if self._player_proc:
            try: self._player_proc.terminate()
            except Exception: pass
            self._player_proc = None
        if shutil.which("termux-media-player"):
            try: subprocess.run(["termux-media-player", "stop"], capture_output=True)
            except Exception: pass
        print(col(C.GRN) + "已停止播放" + col(C.R))

    # ==== Attention ====
    def _cmd_attention(self, args):
        ap = argparse.ArgumentParser(prog="attention")
        ap.add_argument("-l", "--limit", type=int, default=15)
        try:
            ns = ap.parse_args(args)
        except SystemExit: return
        recs = self.store.list_attention(ns.limit)
        if not recs:
            print(col(C.YEL) + "无注意力记录。使用 add-attention 新建。" + col(C.R)); return
        header(f"注意力记录  {len(recs)} 项")
        faces = ["", "😴", "🥱", "🙂", "💪", "🔥"]
        for r in recs:
            ar = r.get("arousalLevel") or 3
            ar = max(1, min(5, int(ar)))
            print(f"  {faces[ar]}  专注{r.get('attentionScore','?'):>3}分  {col(C.BOLD)}{r.get('task','')}{col(C.R)}  "
                  f"{col(C.DIM)}{_fmt_time(r['timestamp'])}{col(C.R)}")
            if r.get("note"):
                for ln in textwrap.wrap(r["note"], 72, initial_indent="     ", subsequent_indent="     "):
                    print(col(C.IT, C.DIM) + ln + col(C.R))

    def _cmd_add_attention(self, args):
        task = self._prompt("当前任务 (e.g. 写代码/阅读/开会)")
        if not task:
            print(col(C.RED) + "任务必填" + col(C.R)); return
        score = int(self._prompt("专注程度 0-100", "70"))
        print("唤醒水平: 1😴 2🥱 3🙂 4💪 5🔥")
        arousal = int(self._prompt("选择", "3"))
        arousal = max(1, min(5, arousal))
        note = self._prompt("备注", "")
        self.store.addAttention if hasattr(self.store, "addAttention") else None
        self.store.add_attention(attentionScore=score, arousalLevel=arousal, task=task, note=note, sessionId=None)
        print(col(C.GRN) + "✅ 已记录" + col(C.R))

    # ==== Sync ====
    def _cmd_sync_status(self):
        s = self.store.data.get("sync") or {}
        header("同步状态")
        print(f"  数据文件:   {col(C.CYN)}{DATA_FILE}{col(C.R)}")
        print(f"  数据版本:   {self.store.data.get('version',1)}")
        print(f"  Web 同步:   {s.get('lastWebSync') or '-'}")
        print(f"  CLI 同步:   {s.get('lastCliSync') or '-'}")
        print(f"  冲突数量:   {len(s.get('conflicts') or [])}")
        print(f"  项目数:     {len(self.store.projects())}")
        print(f"  任务数:     {len(self.store.jobs())}")
        print(f"  Sessions:   {len(self.store.sessions(10**9))}")
        print(f"  注意力记录: {len(self.store.list_attention(10**9))}")

    def _cmd_export(self, args):
        js = self.store.export_json()
        if args:
            p = Path(args[0])
            p.write_text(js, encoding="utf-8")
            print(col(C.GRN) + f"✅ 已导出到 {p.resolve()} ({p.stat().st_size//1024} KB)" + col(C.R))
        else:
            sys.stdout.write(js)
            if not js.endswith("\n"): sys.stdout.write("\n")

    def _cmd_import(self, args):
        if not args:
            print(col(C.RED) + "import <文件路径> 或  import -  (从 stdin)" + col(C.R)); return
        if args[0] == "-":
            raw = sys.stdin.read()
        else:
            p = Path(args[0])
            if not p.exists():
                print(col(C.RED) + f"文件不存在: {p}" + col(C.R)); return
            raw = p.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except Exception as e:
            print(col(C.RED) + f"JSON 解析失败: {e}" + col(C.R)); return
        self.store.import_json(data, merge=True)
        print(col(C.GRN) + "✅ 已合并导入" + col(C.R))

    def _cmd_dashboard(self):
        self._cmd_sync_status()
        print()
        # Mini stats
        recent = self.store.jobs()[:5]
        if recent:
            header("最近任务", char="─")
            for j in recent:
                sc = _status_color(j.get("status"))
                print(f"  · {col(sc)}{STATUS_TEXT.get(j.get('status'),j.get('status','?')):<5}{col(C.R)} "
                      f"{j['title']} {col(C.DIM)}({_fmt_time(j.get('updatedAt',''))}){col(C.R)}")
        today = dt.date.today().isoformat()
        # circadian hints
        print()
        header("今日节律", char="─")
        hour = dt.datetime.now().hour
        phases = [
            ((0,5),  "深度睡眠期", "δ 0.5-4Hz",   "var(--purple)"),
            ((5,7),  "浅眠→清醒",  "θ→α 过渡",    "var(--accent-2)"),
            ((7,9),  "认知高峰",   "β 15-20Hz",   "var(--accent)"),
            ((9,12), "专注期",     "γ 40Hz",      "var(--green)"),
            ((12,14),"午后低谷",   "α 放松",      "var(--warn)"),
            ((14,17),"创意期",     "SMR 8-12Hz",  "var(--pink)"),
            ((17,20),"运动期",     "-",            "var(--red)"),
            ((20,22),"放松期",     "α 8Hz",       "var(--purple)"),
            ((22,24),"睡眠准备",   "δ 2-4Hz",     "var(--accent-2)"),
        ]
        for rg, name, tip, _ in phases:
            now = rg[0] <= hour < rg[1]
            tag = col(C.YEL) + " ▼当前" + col(C.R) if now else ""
            print(f"  {rg[0]:02d}:00-{rg[1]:02d}:00 {col(C.BOLD if now else '')}{name:<10}{col(C.R)}  "
                  f"{col(C.DIM)}{tip:<12}{col(C.R)}{tag}")

# ===== Curses TUI =====
@dataclass
class TuiState:
    store: Store
    mode: str = "home"     # home, projects, jobs, sessions, attention, help
    cursor: int = 0
    offset: int = 0
    status: str = "欢迎 Chronos TUI · ←→切页 · ↑↓选择 · Enter详情 · q退出"
    detail: Optional[Dict] = None

def run_tui(store: Store):
    """Attempt curses TUI; fall back gracefully."""
    try:
        curses.wrapper(_tui_main, store)
    except Exception as e:
        print(col(C.RED) + f"TUI 不可用: {e}" + col(C.R))
        print(col(C.DIM) + "继续使用普通 REPL..." + col(C.R))

def _tui_main(stdscr, store: Store):
    curses.curs_set(0)
    # Try colors
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for i, (fg, bg) in enumerate([
            (-1, -1),          # 0 default
            (curses.COLOR_CYAN, -1), # 1 cyan
            (curses.COLOR_GREEN, -1),# 2 green
            (curses.COLOR_YELLOW,-1),# 3 yellow
            (curses.COLOR_RED, -1),  # 4 red
            (curses.COLOR_MAGENTA,-1),#5 magenta
            (curses.COLOR_BLUE, -1), # 6 blue
            (curses.COLOR_WHITE, -1),# 7 white
            (curses.COLOR_BLACK, curses.COLOR_GREEN), # 8 selection
        ], start=0):
            try: curses.init_pair(i + 1, fg, bg)
            except Exception: pass

    state = TuiState(store=store)
    modes = ["home", "projects", "jobs", "sessions", "attention", "help"]
    mode_labels = {"home":"🏠 主页", "projects":"📁 项目", "jobs":"📋 任务",
                   "sessions":"🎵 生物钟", "attention":"🧠 注意力", "help":"❓ 帮助"}

    while True:
        H, W = stdscr.getmaxyx()
        stdscr.erase()
        # Top bar
        _tui_title(stdscr, W, state, mode_labels)
        # Status bar
        _tui_status(stdscr, H, W, state)
        # Body
        try:
            body = stdscr.derwin(H - 4, W, 2, 0)
        except curses.error:
            body = stdscr
        bh, bw = body.getmaxyx()
        if state.mode == "home":
            _tui_home(body, bh, bw, state)
        elif state.mode == "projects":
            _tui_projects(body, bh, bw, state)
        elif state.mode == "jobs":
            _tui_jobs(body, bh, bw, state)
        elif state.mode == "sessions":
            _tui_sessions(body, bh, bw, state)
        elif state.mode == "attention":
            _tui_attention(body, bh, bw, state)
        elif state.mode == "help":
            _tui_help(body, bh, bw)
        stdscr.refresh()
        # Input
        try:
            k = stdscr.getch()
        except KeyboardInterrupt:
            break
        if k in (ord("q"), ord("Q"), 27):
            if state.detail:
                state.detail = None
            else:
                break
        elif k == curses.KEY_LEFT:
            idx = modes.index(state.mode)
            state.mode = modes[(idx - 1) % len(modes)]
            state.cursor = 0; state.offset = 0; state.detail = None
        elif k == curses.KEY_RIGHT:
            idx = modes.index(state.mode)
            state.mode = modes[(idx + 1) % len(modes)]
            state.cursor = 0; state.offset = 0; state.detail = None
        elif k == curses.KEY_UP:
            state.cursor = max(0, state.cursor - 1)
        elif k == curses.KEY_DOWN:
            state.cursor += 1
        elif k in (curses.KEY_ENTER, 10, 13):
            _tui_enter(state)
        elif k == ord("r") or k == ord("R"):
            state.status = "已刷新数据"
        else:
            # digit navigation
            if 48 <= k <= 57:  # 0-9
                pass  # ignore for now

def _tui_title(stdscr, W, state: TuiState, labels: Dict):
    title = f" CHRONOS 时空工作站  v1.0  │  数据: {DATA_FILE.name}  "
    if len(title) > W - 24: title = title[:W-24]
    try:
        stdscr.addstr(0, 0, title.ljust(W), curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass
    # Tabs
    tabs = ["🏠","📁","📋","🎵","🧠","❓"]
    modes = ["home","projects","jobs","sessions","attention","help"]
    x = 0
    for i, t in enumerate(tabs):
        active = state.mode == modes[i]
        s = f" {t} {labels[modes[i]]} "
        attr = curses.color_pair(8) if active else curses.A_NORMAL
        try:
            stdscr.addstr(1, x, s, attr)
        except curses.error:
            pass
        x += len(s)
        if x >= W: break

def _tui_status(stdscr, H, W, state: TuiState):
    try:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s = f" {state.status} "
        n = W - len(now) - 2
        if n < 2: n = 2
        s = s[:n].ljust(n) + " " + now + " "
        stdscr.addstr(H-1, 0, s[:W], curses.color_pair(2) | curses.A_REVERSE)
    except curses.error:
        pass

def _tui_home(win, H: int, W: int, state: TuiState):
    s = state.store
    active_p = sum(1 for p in s.projects() if p.get("status") == "active")
    pending_j = sum(1 for j in s.jobs() if j.get("status") != "done")
    today = dt.date.today().isoformat()
    focus = sum(int(x.get("durationMinutes") or 0) for x in s.sessions(500)
                if x.get("completed") and x["startedAt"][:10] == today
                and x.get("purpose") in ("focus","energy"))
    stats = [
        ("📁 活跃项目", str(active_p), curses.color_pair(1)),
        ("📝 待办任务", str(pending_j), curses.color_pair(3)),
        ("🧠 今日专注(分钟)", str(focus), curses.color_pair(2)),
        ("📈 总任务", str(len(s.jobs())), curses.color_pair(6)),
        ("🎵 生物钟次数", str(len(s.sessions(10**9))), curses.color_pair(5)),
    ]
    y = 0
    for name, val, attr in stats:
        if y >= H - 2: break
        try:
            win.addstr(y, 2, f"{name:<20}", curses.A_BOLD)
            win.addstr(y, 24, val, attr | curses.A_BOLD)
        except curses.error: pass
        y += 1
    y += 1
    if y < H - 3:
        try: win.addstr(y, 2, "最近任务:", curses.A_BOLD | curses.color_pair(1))
        except curses.error: pass
        y += 1
        for j in s.jobs()[:max(0, H - y - 1)]:
            st = STATUS_TEXT.get(j.get("status"), j.get("status","?"))
            try:
                win.addstr(y, 4, f"· [{st:<4}] {j['title'][:W-20]}")
            except curses.error: pass
            y += 1

def _tui_projects(win, H: int, W: int, state: TuiState):
    items = state.store.projects()
    state.cursor = min(state.cursor, max(0, len(items)-1))
    y = 0
    for i, p in enumerate(items):
        if y >= H - 1: break
        sel = (i == state.cursor)
        attr = curses.color_pair(8) if sel else curses.A_NORMAL
        st = PROJECT_STATUS_TEXT.get(p.get("status"), p.get("status","?"))
        line = f" {i+1:2}. [{st:<2}] {p['name'][:W-30]}  进度 {p.get('progress',0)}%  任务{len(state.store.jobs(project_id=p['id']))}"
        if len(line) > W - 2: line = line[:W-2]
        try: win.addstr(y, 0, line.ljust(W-1), attr)
        except curses.error: pass
        y += 1

def _tui_jobs(win, H: int, W: int, state: TuiState):
    items = state.store.jobs()
    state.cursor = min(state.cursor, max(0, len(items)-1))
    y = 0
    for i, j in enumerate(items):
        if y >= H - 1: break
        sel = (i == state.cursor)
        attr = curses.color_pair(8) if sel else curses.A_NORMAL
        p = next((x for x in state.store.projects() if x["id"] == j.get("projectId")), None)
        pn = p["name"] if p else "-"
        st = STATUS_TEXT.get(j.get("status"), j.get("status","?"))
        pr = PRIORITY_TEXT.get(j.get("priority"), j.get("priority","?"))
        line = f" {i+1:3}. [{st:<2}|{pr:<1}] {j['title'][:W-42]}  📁{pn[:10]}"
        if len(line) > W - 1: line = line[:W-1]
        try: win.addstr(y, 0, line.ljust(W-1), attr)
        except curses.error: pass
        y += 1

def _tui_sessions(win, H: int, W: int, state: TuiState):
    items = state.store.sessions(50)
    state.cursor = min(state.cursor, max(0, len(items)-1))
    y = 0
    for i, s in enumerate(items):
        if y >= H - 1: break
        sel = (i == state.cursor)
        attr = curses.color_pair(8) if sel else curses.A_NORMAL
        icon = PURPOSE_ICON.get(s.get("purpose"), "🎵")
        ttype = TYPE_TEXT.get(s.get("type"), s.get("type","?"))
        done = "✅" if s.get("completed") else "⏹"
        line = f" {i+1:3}. {icon} {s.get('frequencyHz',0):5.1f}Hz ({ttype}) 载波{s.get('carrierFrequencyHz','?')}Hz  {s.get('durationMinutes',0)}m {done}  {_fmt_time(s['startedAt'])}"
        if len(line) > W - 1: line = line[:W-1]
        try: win.addstr(y, 0, line.ljust(W-1), attr)
        except curses.error: pass
        y += 1

def _tui_attention(win, H: int, W: int, state: TuiState):
    items = state.store.list_attention(50)
    state.cursor = min(state.cursor, max(0, len(items)-1))
    faces = ["","😴","🥱","🙂","💪","🔥"]
    y = 0
    for i, r in enumerate(items):
        if y >= H - 1: break
        sel = (i == state.cursor)
        attr = curses.color_pair(8) if sel else curses.A_NORMAL
        ar = max(1, min(5, int(r.get("arousalLevel") or 3)))
        line = f" {i+1:3}. {faces[ar]} 专注{r.get('attentionScore','?'):>3}分  {str(r.get('task',''))[:W-40]}  {_fmt_time(r['timestamp'])}"
        if len(line) > W - 1: line = line[:W-1]
        try: win.addstr(y, 0, line.ljust(W-1), attr)
        except curses.error: pass
        y += 1

def _tui_help(win, H: int, W: int):
    lines = [
        "CHRONOS TUI 快捷键:",
        "  ← / →   切换页面 (主页→项目→任务→生物钟→注意力→帮助)",
        "  ↑ / ↓   在列表中移动光标",
        "  Enter   查看当前项详情 / 执行操作",
        "  q / Esc 返回上一级 / 退出TUI",
        "  r       刷新数据视图",
        "",
        "如需命令行交互模式:",
        "  在 REPL 中输入 h 查看所有命令",
        "  如: focus 25   — 启动 25 分钟专注声频",
        "      jobs       — 列出所有任务",
        "      kanban     — 看板视图",
        "",
        "数据同步 (Web ↔ CLI):",
        "  CLI侧:  chronos> export 导出 / chronos> import 文件.json",
        "  Web侧:  同步 Tab → 导出 / 导入 JSON 或 粘贴合并",
    ]
    for y, line in enumerate(lines[:H-1]):
        try: win.addstr(y, 2, line)
        except curses.error: pass

def _tui_enter(state: TuiState):
    try:
        if state.mode == "projects":
            items = state.store.projects()
            if items: state.detail = items[state.cursor]; state.status = f"查看项目: {state.detail['name']}"
        elif state.mode == "jobs":
            items = state.store.jobs()
            if items: state.detail = items[state.cursor]; state.status = f"查看任务: {state.detail['title']}"
    except Exception:
        pass

# ===== CLI Entry =====
def main():
    parser = argparse.ArgumentParser(prog="chronos",
                                     description="CHRONOS - 时空工作站 (Workgroup + Biological Clock)")
    parser.add_argument("mode", nargs="?", default="repl",
                        choices=["repl", "tui", "export", "import", "help", "version"],
                        help="运行模式")
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="子命令参数")
    args = parser.parse_args()

    store = Store.load()

    if args.mode == "tui":
        run_tui(store)
        return
    if args.mode == "export":
        # chronos export [path]
        path = args.rest[0] if args.rest else None
        js = store.export_json()
        if path:
            Path(path).write_text(js, encoding="utf-8")
            print(f"已导出到 {path}")
        else:
            sys.stdout.write(js + ("\n" if not js.endswith("\n") else ""))
        return
    if args.mode == "import":
        if not args.rest:
            print("import 需要路径参数或 - (stdin)", file=sys.stderr); sys.exit(1)
        src = args.rest[0]
        raw = sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8")
        store.import_json(json.loads(raw), merge=True)
        print("已合并导入")
        return
    if args.mode == "version":
        print("CHRONOS CLI 1.0.0 — pure stdlib")
        print(f"  数据文件: {DATA_FILE}")
        return
    if args.mode == "help":
        parser.print_help()
        print()
        print("子命令示例 (启动 REPL 后可用完整命令集):")
        print("  chronos repl             启动交互式命令行")
        print("  chronos tui              启动 curses 终端 UI")
        print("  chronos export out.json  导出 JSON")
        print("  chronos import data.json 导入合并")
        print("  chronos help             帮助")
        return
    # REPL
    repl = REPL(store)
    repl.run()

if __name__ == "__main__":
    main()
