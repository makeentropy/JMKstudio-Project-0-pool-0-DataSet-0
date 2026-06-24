from typing import List, Optional, Dict
from dataclasses import dataclass
import re
from ..llm.base import ChatMessage, Role, BaseLLM
from ..email_service import EmailService, EmailMessage
from .chat_agent import ChatAgent


@dataclass
class EmailAnalysis:
    summary: str
    category: str
    priority: str
    key_points: List[str]
    action_items: List[str]
    sender_tone: str


class EmailAgent:
    def __init__(
        self,
        llm: BaseLLM,
        email_service: EmailService,
        config=None,
    ):
        self.llm = llm
        self.email_service = email_service
        self.config = config
        self.chat_agent = ChatAgent(llm)
        self._email_summary_prompt = """你是一个专业的邮件分析助手。请分析以下邮件内容，并以JSON格式返回分析结果，包含以下字段：
- summary: 邮件内容的简短摘要（不超过200字）
- category: 邮件分类（如：工作、个人、广告、通知、社交等）
- priority: 优先级（高、中、低）
- key_points: 关键点列表（3-5个）
- action_items: 需要执行的行动项列表
- sender_tone: 发件人的语气/态度描述

请直接返回JSON，不要包含其他内容。

邮件内容：
{email_content}
"""

        self._reply_prompt = """你是一个专业的邮件回复助手。请根据以下邮件内容和用户要求，撰写一封合适的回复邮件。

原邮件信息：
- 发件人: {sender}
- 主题: {subject}
- 内容:
{email_content}

用户要求: {user_instruction}

请撰写回复邮件的正文内容，保持专业、礼貌的语气。只返回邮件正文内容，不要包含主题、收件人等信息。
"""

    def analyze_email(self, email_msg: EmailMessage) -> Optional[EmailAnalysis]:
        prompt = self._email_summary_prompt.format(email_content=email_msg.body[:3000])
        messages = [
            ChatMessage(role=Role.SYSTEM, content="你是一个专业的邮件分析助手，擅长分析和总结邮件内容。"),
            ChatMessage(role=Role.USER, content=prompt),
        ]
        response = self.llm.chat(messages)
        if not response.success:
            return None
        try:
            import json
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            if content.startswith("```"):
                content = content[3:-3].strip()
            data = json.loads(content)
            return EmailAnalysis(
                summary=data.get("summary", ""),
                category=data.get("category", ""),
                priority=data.get("priority", ""),
                key_points=data.get("key_points", []),
                action_items=data.get("action_items", []),
                sender_tone=data.get("sender_tone", ""),
            )
        except Exception as e:
            print(f"Parse email analysis failed: {e}")
            return EmailAnalysis(
                summary=response.content[:200],
                category="未分类",
                priority="中",
                key_points=[],
                action_items=[],
                sender_tone="",
            )

    def generate_reply(
        self,
        email_msg: EmailMessage,
        user_instruction: str = "请礼貌地回复这封邮件",
    ) -> str:
        prompt = self._reply_prompt.format(
            sender=email_msg.sender,
            subject=email_msg.subject,
            email_content=email_msg.body[:3000],
            user_instruction=user_instruction,
        )
        messages = [
            ChatMessage(role=Role.SYSTEM, content="你是一个专业的邮件写作助手，擅长撰写各种类型的邮件回复。"),
            ChatMessage(role=Role.USER, content=prompt),
        ]
        response = self.llm.chat(messages)
        if response.success:
            return response.content
        return f"生成回复失败: {response.error}"

    def send_reply(
        self,
        email_msg: EmailMessage,
        reply_body: str,
        subject_prefix: str = "Re:",
    ) -> bool:
        subject = email_msg.subject
        if not subject.startswith(("Re:", "回复:")):
            subject = f"{subject_prefix} {subject}"
        signature = self.config.signature if self.config else ""
        full_body = reply_body + signature
        return self.email_service.send_email(
            to=[email_msg.sender],
            subject=subject,
            body=full_body,
            in_reply_to=email_msg.thread_id,
            references=email_msg.thread_id,
        )

    def compose_email(
        self,
        to: List[str],
        topic: str,
        context: str = "",
        tone: str = "professional",
    ) -> dict:
        prompt = f"""请帮我撰写一封邮件。
收件人: {', '.join(to)}
主题/内容要点: {topic}
附加信息/上下文: {context}
语气风格: {tone}

请以JSON格式返回，包含以下字段：
- subject: 邮件主题
- body: 邮件正文

只返回JSON，不要其他内容。"""
        messages = [
            ChatMessage(role=Role.SYSTEM, content="你是一个专业的邮件写作助手，擅长撰写各种类型的邮件。"),
            ChatMessage(role=Role.USER, content=prompt),
        ]
        response = self.llm.chat(messages)
        if not response.success:
            return {"subject": "", "body": f"生成邮件失败: {response.error}"}
        try:
            import json
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            if content.startswith("```"):
                content = content[3:-3].strip()
            data = json.loads(content)
            return data
        except Exception:
            return {"subject": topic, "body": response.content}

    def batch_summarize(self, emails: List[EmailMessage]) -> str:
        email_list = []
        for i, em in enumerate(emails[:20], 1):
            email_list.append(f"""
邮件 {i}:
- 发件人: {em.sender}
- 主题: {em.subject}
- 内容摘要: {em.body[:200]}...
""")
        prompt = f"""以下是最近的邮件列表，请为我做一个总结：
{''.join(email_list)}

请按以下格式总结：
1. 重要邮件（需要立即处理的）
2. 一般邮件（可稍后处理的）
3. 低优先级邮件（广告、通知等）
4. 总体建议

请用中文回答。"""
        messages = [
            ChatMessage(role=Role.SYSTEM, content="你是一个邮件管理助手，帮用户整理和总结邮件。"),
            ChatMessage(role=Role.USER, content=prompt),
        ]
        response = self.llm.chat(messages)
        return response.content if response.success else f"总结失败: {response.error}"

    def get_inbox_summary(self, limit: int = 10) -> dict:
        emails = self.email_service.fetch_emails(limit=limit)
        unread_count = self.email_service.get_unread_count()
        analysis_list = []
        for em in emails[:5]:
            analysis = self.analyze_email(em)
            if analysis:
                analysis_list.append({
                    "id": em.id,
                    "subject": em.subject,
                    "sender": em.sender,
                    "summary": analysis.summary,
                    "category": analysis.category,
                    "priority": analysis.priority,
                    "date": em.date.isoformat() if em.date else "",
                })
        return {
            "total_emails": len(emails),
            "unread_count": unread_count,
            "recent_emails": analysis_list,
        }
