#!/usr/bin/env python3
"""
Email AI Agent - 智能邮件助手
支持终端Shell交互和HTTP服务两种模式
"""

import argparse
import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from email_agent.config import Config


def main():
    parser = argparse.ArgumentParser(
        description="Email AI Agent - 智能邮件助手",
        prog="email-agent",
    )
    parser.add_argument(
        "-c", "--config",
        help="配置文件路径 (YAML)",
        default=os.environ.get("CONFIG_PATH", "config/config.yaml"),
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    shell_parser = subparsers.add_parser("shell", help="启动终端交互模式")

    server_parser = subparsers.add_parser("server", help="启动HTTP服务")
    server_parser.add_argument("--host", help="监听地址")
    server_parser.add_argument("-p", "--port", type=int, help="监听端口")

    subparsers.add_parser("status", help="查看系统状态")
    subparsers.add_parser("version", help="查看版本号")

    args = parser.parse_args()

    config_path = args.config
    if not os.path.exists(config_path):
        config_path = None
    config = Config.load(config_path)

    if args.command == "version":
        from email_agent import __version__
        print(f"Email AI Agent v{__version__}")
        return 0

    if args.command == "status":
        print_status(config)
        return 0

    if args.command == "server":
        from email_agent.server import HTTPServer
        if args.host:
            config.server.host = args.host
        if args.port:
            config.server.port = args.port
        server = HTTPServer(config)
        server.run()
        return 0

    from email_agent.terminal import TerminalShell
    shell = TerminalShell(config)
    shell.run()
    return 0


def print_status(config):
    from email_agent.llm import LLMFactory
    from email_agent.email_service import EmailService

    print("=" * 50)
    print("  Email AI Agent - 系统状态")
    print("=" * 50)
    print(f"  邮箱: {config.email.address}")
    print(f"  IMAP: {config.email.imap_server}:{config.email.imap_port}")
    print(f"  SMTP: {config.email.smtp_server}:{config.email.smtp_port}")
    print(f"  LLM: {config.llm.provider} ({config.llm.model})")
    print(f"  API Base: {config.llm.api_base}")
    print(f"  服务端口: {config.server.port}")
    print("=" * 50)

    try:
        llm = LLMFactory.create(config.llm)
        print("  LLM: 可用 ✓")
    except Exception as e:
        print(f"  LLM: 不可用 ✗ ({e})")

    try:
        email = EmailService(config.email)
        if email.connect_imap():
            print("  IMAP: 连接成功 ✓")
            email.disconnect_imap()
        else:
            print("  IMAP: 连接失败 ✗")
    except Exception as e:
        print(f"  IMAP: 错误 ✗ ({e})")

    try:
        email = EmailService(config.email)
        if email.connect_smtp():
            print("  SMTP: 连接成功 ✓")
            email.disconnect_smtp()
        else:
            print("  SMTP: 连接失败 ✗")
    except Exception as e:
        print(f"  SMTP: 错误 ✗ ({e})")

    print("=" * 50)


if __name__ == "__main__":
    sys.exit(main())
