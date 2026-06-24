import sys
import os
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, Completion
from ..config import Config
from ..llm import LLMFactory
from ..email_service import EmailService
from ..agent import ChatAgent, EmailAgent


class EmailAgentCompleter(Completer):
    def __init__(self, commands: dict):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if " " not in text:
            for cmd in sorted(self.commands.keys()):
                if cmd.startswith(text.lower()):
                    yield Completion(cmd, start_position=-len(text))


class TerminalShell:
    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        self.llm = None
        self.email_service = None
        self.chat_agent = None
        self.email_agent = None
        self.current_conv_id = None
        self.running = False
        self.commands = {
            "help": "显示帮助信息",
            "exit": "退出程序",
            "chat": "进入聊天模式",
            "email": "进入邮件模式",
            "inbox": "查看收件箱",
            "read": "读取邮件 (read <id>)",
            "reply": "回复邮件 (reply <id>)",
            "compose": "撰写新邮件",
            "summarize": "总结邮件",
            "analyze": "分析邮件 (analyze <id>)",
            "status": "查看状态",
            "clear": "清屏",
            "config": "查看配置",
        }
        self._init_services()

    def _init_services(self):
        try:
            self.llm = LLMFactory.create(self.config.llm)
            self.chat_agent = ChatAgent(self.llm)
            self.current_conv_id = self.chat_agent.create_conversation("默认对话")
        except Exception as e:
            self.console.print(f"[yellow]LLM初始化警告: {e}[/yellow]")
        try:
            self.email_service = EmailService(self.config.email)
            if self.llm:
                self.email_agent = EmailAgent(self.llm, self.email_service, self.config.agent)
        except Exception as e:
            self.console.print(f"[yellow]邮件服务初始化警告: {e}[/yellow]")

    def _print_banner(self):
        banner = Text()
        banner.append("╔══════════════════════════════════════════════╗\n", style="bold cyan")
        banner.append("║       Email AI Agent - 智能邮件助手          ║\n", style="bold cyan")
        banner.append("║            makeentropy@yeah.net              ║\n", style="cyan")
        banner.append("╚══════════════════════════════════════════════╝\n", style="bold cyan")
        banner.append("\n输入 'help' 查看可用命令，输入 'exit' 退出\n", style="dim")
        self.console.print(banner)

    def _print_help(self):
        table = Table(title="可用命令", show_header=True, header_style="bold magenta")
        table.add_column("命令", style="cyan", no_wrap=True)
        table.add_column("描述", style="white")
        for cmd, desc in sorted(self.commands.items()):
            table.add_row(cmd, desc)
        self.console.print(table)

    def _cmd_help(self, args):
        self._print_help()

    def _cmd_exit(self, args):
        self.running = False
        self.console.print("[green]再见！[/green]")

    def _cmd_chat(self, args):
        if not self.chat_agent:
            self.console.print("[red]聊天服务未初始化[/red]")
            return
        self.console.print("[cyan]已进入聊天模式，输入 /back 返回主菜单[/cyan]")
        self._chat_loop()

    def _chat_loop(self):
        history_path = os.path.expanduser("~/.email_agent_chat_history")
        session = PromptSession(history=FileHistory(history_path))
        while True:
            try:
                user_input = session.prompt("🧑 You: ")
                if not user_input.strip():
                    continue
                if user_input.strip() == "/back":
                    break
                if user_input.strip() == "/clear":
                    if self.current_conv_id:
                        self.chat_agent.clear_conversation(self.current_conv_id)
                        self.console.print("[green]对话已清空[/green]")
                    continue
                if user_input.strip() == "/new":
                    self.current_conv_id = self.chat_agent.create_conversation()
                    self.console.print(f"[green]新对话已创建: {self.current_conv_id[:8]}[/green]")
                    continue
                self.console.print("[bold blue]🤖 AI:[/bold blue] ", end="")
                full_response = []
                for chunk in self.chat_agent.send_message_stream(self.current_conv_id, user_input):
                    self.console.print(chunk, end="", style="white")
                    full_response.append(chunk)
                self.console.print()
            except (EOFError, KeyboardInterrupt):
                break

    def _cmd_inbox(self, args):
        if not self.email_service:
            self.console.print("[red]邮件服务未初始化[/red]")
            return
        limit = 10
        if args:
            try:
                limit = int(args[0])
            except ValueError:
                pass
        self.console.print(f"[cyan]正在加载收件箱（最近 {limit} 封）...[/cyan]")
        try:
            emails = self.email_service.fetch_emails(limit=limit)
            if not emails:
                self.console.print("[yellow]收件箱为空或加载失败[/yellow]")
                return
            table = Table(title=f"收件箱 ({len(emails)} 封)", show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", width=6)
            table.add_column("状态", style="white", width=4)
            table.add_column("发件人", style="green", width=25)
            table.add_column("主题", style="white")
            table.add_column("日期", style="yellow", width=19)
            for i, em in enumerate(emails, 1):
                status = "✓" if em.is_read else "✉"
                status_style = "dim" if em.is_read else "bold yellow"
                date_str = em.date.strftime("%Y-%m-%d %H:%M") if em.date else "未知"
                sender = em.sender_name or em.sender
                if len(sender) > 22:
                    sender = sender[:20] + ".."
                subject = em.subject if len(em.subject) < 40 else em.subject[:38] + ".."
                table.add_row(
                    str(i),
                    Text(status, style=status_style),
                    sender,
                    subject,
                    date_str,
                )
            self._last_emails = emails
            self.console.print(table)
        except Exception as e:
            self.console.print(f"[red]加载失败: {e}[/red]")

    def _cmd_read(self, args):
        if not self.email_service or not hasattr(self, '_last_emails') or not self._last_emails:
            self.console.print("[yellow]请先运行 inbox 查看邮件列表[/yellow]")
            return
        if not args:
            self.console.print("[yellow]用法: read <邮件ID>[/yellow]")
            return
        try:
            idx = int(args[0]) - 1
            if idx < 0 or idx >= len(self._last_emails):
                self.console.print("[red]无效的邮件ID[/red]")
                return
            em = self._last_emails[idx]
            self.console.print(Panel(
                f"[bold cyan]主题:[/bold cyan] {em.subject}\n"
                f"[bold green]发件人:[/bold green] {em.sender_name} <{em.sender}>\n"
                f"[bold yellow]日期:[/bold yellow] {em.date.strftime('%Y-%m-%d %H:%M:%S') if em.date else '未知'}\n"
                f"[bold dim]{'─' * 60}[/bold dim]\n\n"
                f"{em.body[:2000]}",
                title=f"邮件 #{idx + 1}",
                border_style="blue",
            ))
        except ValueError:
            self.console.print("[red]无效的邮件ID[/red]")

    def _cmd_analyze(self, args):
        if not self.email_agent or not hasattr(self, '_last_emails') or not self._last_emails:
            self.console.print("[yellow]请先运行 inbox 查看邮件列表[/yellow]")
            return
        if not args:
            self.console.print("[yellow]用法: analyze <邮件ID>[/yellow]")
            return
        try:
            idx = int(args[0]) - 1
            if idx < 0 or idx >= len(self._last_emails):
                self.console.print("[red]无效的邮件ID[/red]")
                return
            em = self._last_emails[idx]
            self.console.print("[cyan]正在分析邮件...[/cyan]")
            analysis = self.email_agent.analyze_email(em)
            if analysis:
                content = (
                    f"[bold cyan]📊 分析结果[/bold cyan]\n\n"
                    f"[bold]摘要:[/bold] {analysis.summary}\n\n"
                    f"[bold]分类:[/bold] {analysis.category}    [bold]优先级:[/bold] {analysis.priority}\n\n"
                    f"[bold]关键点:[/bold]\n"
                )
                for i, point in enumerate(analysis.key_points, 1):
                    content += f"  {i}. {point}\n"
                content += f"\n[bold]行动项:[/bold]\n"
                for i, item in enumerate(analysis.action_items, 1):
                    content += f"  {i}. {item}\n"
                content += f"\n[bold]语气:[/bold] {analysis.sender_tone}"
                self.console.print(Panel(content, title="邮件智能分析", border_style="green"))
        except ValueError:
            self.console.print("[red]无效的邮件ID[/red]")

    def _cmd_reply(self, args):
        if not self.email_agent or not hasattr(self, '_last_emails') or not self._last_emails:
            self.console.print("[yellow]请先运行 inbox 查看邮件列表[/yellow]")
            return
        if not args:
            self.console.print("[yellow]用法: reply <邮件ID>[/yellow]")
            return
        try:
            idx = int(args[0]) - 1
            if idx < 0 or idx >= len(self._last_emails):
                self.console.print("[red]无效的邮件ID[/red]")
                return
            em = self._last_emails[idx]
            instruction = " ".join(args[1:]) if len(args) > 1 else "请礼貌地回复这封邮件"
            self.console.print("[cyan]正在生成回复...[/cyan]")
            reply_body = self.email_agent.generate_reply(em, instruction)
            self.console.print(Panel(reply_body, title=f"回复: {em.subject}", border_style="blue"))
            confirm = input("\n是否发送此回复？(y/N): ").strip().lower()
            if confirm == "y":
                if self.email_agent.send_reply(em, reply_body):
                    self.console.print("[green]✓ 回复已发送[/green]")
                else:
                    self.console.print("[red]发送失败[/red]")
        except ValueError:
            self.console.print("[red]无效的邮件ID[/red]")

    def _cmd_compose(self, args):
        if not self.email_agent:
            self.console.print("[red]邮件智能体未初始化[/red]")
            return
        to = input("收件人: ").strip()
        if not to:
            self.console.print("[yellow]收件人不能为空[/yellow]")
            return
        topic = input("邮件主题/要点: ").strip()
        context = input("附加信息（可选）: ").strip()
        self.console.print("[cyan]正在撰写邮件...[/cyan]")
        result = self.email_agent.compose_email(
            to=[t.strip() for t in to.split(",")],
            topic=topic,
            context=context,
        )
        self.console.print(Panel(
            f"[bold]主题:[/bold] {result.get('subject', '')}\n\n"
            f"{result.get('body', '')}",
            title="撰写邮件",
            border_style="blue",
        ))
        confirm = input("\n是否发送此邮件？(y/N): ").strip().lower()
        if confirm == "y":
            if self.email_service.send_email(
                to=[t.strip() for t in to.split(",")],
                subject=result.get("subject", topic),
                body=result.get("body", ""),
            ):
                self.console.print("[green]✓ 邮件已发送[/green]")
            else:
                self.console.print("[red]发送失败[/red]")

    def _cmd_summarize(self, args):
        if not self.email_agent or not self.email_service:
            self.console.print("[red]邮件服务未初始化[/red]")
            return
        limit = 10
        if args:
            try:
                limit = int(args[0])
            except ValueError:
                pass
        self.console.print(f"[cyan]正在总结最近 {limit} 封邮件...[/cyan]")
        emails = self.email_service.fetch_emails(limit=limit)
        if not emails:
            self.console.print("[yellow]没有邮件[/yellow]")
            return
        summary = self.email_agent.batch_summarize(emails)
        self.console.print(Panel(Markdown(summary), title=f"邮件总结 ({len(emails)} 封)", border_style="magenta"))

    def _cmd_status(self, args):
        lines = []
        lines.append("[bold cyan]系统状态[/bold cyan]\n")
        if self.llm:
            lines.append(f"[green]✓[/green] LLM: {self.config.llm.provider} ({self.config.llm.model})")
        else:
            lines.append("[red]✗[/red] LLM: 未初始化")
        if self.email_service:
            lines.append(f"[green]✓[/green] 邮件服务: {self.config.email.address}")
        else:
            lines.append("[red]✗[/red] 邮件服务: 未初始化")
        if self.chat_agent:
            convs = self.chat_agent.list_conversations()
            lines.append(f"[green]✓[/green] 对话: {len(convs)} 个会话")
        unread = self.email_service.get_unread_count() if self.email_service else 0
        lines.append(f"  未读邮件: {unread} 封")
        self.console.print(Panel("\n".join(lines), title="状态", border_style="cyan"))

    def _cmd_clear(self, args):
        os.system("cls" if os.name == "nt" else "clear")

    def _cmd_config(self, args):
        content = (
            f"[bold]邮箱:[/bold] {self.config.email.address}\n"
            f"[bold]IMAP:[/bold] {self.config.email.imap_server}:{self.config.email.imap_port}\n"
            f"[bold]SMTP:[/bold] {self.config.email.smtp_server}:{self.config.email.smtp_port}\n"
            f"[bold]LLM:[/bold] {self.config.llm.provider} ({self.config.llm.model})\n"
            f"[bold]API Base:[/bold] {self.config.llm.api_base}\n"
            f"[bold]自动回复:[/bold] {'开启' if self.config.agent.auto_reply else '关闭'}\n"
            f"[bold]检查间隔:[/bold] {self.config.agent.check_interval}秒"
        )
        self.console.print(Panel(content, title="配置信息", border_style="yellow"))

    def _process_command(self, user_input: str):
        parts = user_input.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]
        cmd_map = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "chat": self._cmd_chat,
            "inbox": self._cmd_inbox,
            "ls": self._cmd_inbox,
            "read": self._cmd_read,
            "analyze": self._cmd_analyze,
            "reply": self._cmd_reply,
            "compose": self._cmd_compose,
            "write": self._cmd_compose,
            "summarize": self._cmd_summarize,
            "status": self._cmd_status,
            "clear": self._cmd_clear,
            "config": self._cmd_config,
        }
        if cmd in cmd_map:
            cmd_map[cmd](args)
        else:
            self.console.print(f"[yellow]未知命令: {cmd}，输入 help 查看帮助[/yellow]")

    def run(self):
        self.running = True
        self._print_banner()
        history_path = os.path.expanduser("~/.email_agent_history")
        session = PromptSession(
            history=FileHistory(history_path),
            completer=EmailAgentCompleter(self.commands),
        )
        while self.running:
            try:
                user_input = session.prompt("📧 email-agent> ")
                if user_input.strip():
                    self._process_command(user_input)
            except (EOFError, KeyboardInterrupt):
                self.running = False
                self.console.print("\n[green]再见！[/green]")
                break
            except Exception as e:
                self.console.print(f"[red]错误: {e}[/red]")
