"""命令行入口。

提供 ``ide`` 子命令启动 H5 内嵌 Jupyter IDE：

    ai-crawler ide --host 0.0.0.0 --port 8000
    ai-crawler ide --embed          # 商用隐藏模式
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence


def _cmd_ide(args: argparse.Namespace) -> int:
    os.environ["IDE_HOST"] = args.host
    os.environ["IDE_PORT"] = str(args.port)
    os.environ["IDE_EMBED"] = "true" if args.embed else "false"
    if args.llama_mode:
        os.environ["LLAMA_MODE"] = args.llama_mode
    if args.js_agent_mode:
        os.environ["JS_AGENT_MODE"] = args.js_agent_mode
    from ai_llm_agent_crawler.ide.server import main

    main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ai-crawler",
        description="AI LLM Agent Crawler —— 智能爬虫、数据集、LLM 引擎与 H5 内嵌 IDE",
    )
    sub = p.add_subparsers(dest="cmd")

    ide = sub.add_parser("ide", help="启动 H5 内嵌 Jupyter IDE")
    ide.add_argument("--host", default="0.0.0.0")
    ide.add_argument("--port", type=int, default=8000)
    ide.add_argument("--embed", action="store_true", help="商用隐藏模式（关闭 docs/标识）")
    ide.add_argument("--llama-mode", default=None, choices=["stub", "local", "remote"])
    ide.add_argument("--js-agent-mode", default=None, choices=["stub", "http"])
    ide.set_defaults(func=_cmd_ide)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
