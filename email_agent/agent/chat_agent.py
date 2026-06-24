from typing import List, Optional, Dict, Generator
from dataclasses import dataclass, field
import uuid
import time
from ..llm.base import ChatMessage, Role, BaseLLM


@dataclass
class Conversation:
    id: str
    title: str = ""
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        self.updated_at = time.time()
        if not self.title and message.role == Role.USER:
            self.title = message.content[:30] + ("..." if len(message.content) > 30 else "")


class ChatAgent:
    def __init__(self, llm: BaseLLM, system_prompt: Optional[str] = None):
        self.llm = llm
        self.conversations: Dict[str, Conversation] = {}
        self.default_system_prompt = system_prompt or (
            "你是一个专业的AI助手，可以帮助用户处理各种任务。"
            "请用清晰、准确、友好的方式回答用户的问题。"
        )

    def create_conversation(self, title: str = "") -> str:
        conv_id = str(uuid.uuid4())
        conv = Conversation(id=conv_id, title=title)
        conv.add_message(ChatMessage(role=Role.SYSTEM, content=self.default_system_prompt))
        self.conversations[conv_id] = conv
        return conv_id

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        return self.conversations.get(conv_id)

    def list_conversations(self) -> List[dict]:
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": len(conv.messages),
            }
            for conv in sorted(self.conversations.values(), key=lambda x: x.updated_at, reverse=True)
        ]

    def delete_conversation(self, conv_id: str) -> bool:
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            return True
        return False

    def send_message(
        self,
        conv_id: str,
        user_message: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        if conv_id not in self.conversations:
            conv_id = self.create_conversation()
        conv = self.conversations[conv_id]
        if system_prompt and conv.messages and conv.messages[0].role == Role.SYSTEM:
            conv.messages[0] = ChatMessage(role=Role.SYSTEM, content=system_prompt)
        conv.add_message(ChatMessage(role=Role.USER, content=user_message))
        response = self.llm.chat(conv.messages)
        if response.success:
            conv.add_message(ChatMessage(role=Role.ASSISTANT, content=response.content))
            return response.content
        else:
            error_msg = f"抱歉，发生了错误：{response.error}"
            conv.add_message(ChatMessage(role=Role.ASSISTANT, content=error_msg))
            return error_msg

    def send_message_stream(
        self,
        conv_id: str,
        user_message: str,
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        if conv_id not in self.conversations:
            conv_id = self.create_conversation()
        conv = self.conversations[conv_id]
        if system_prompt and conv.messages and conv.messages[0].role == Role.SYSTEM:
            conv.messages[0] = ChatMessage(role=Role.SYSTEM, content=system_prompt)
        conv.add_message(ChatMessage(role=Role.USER, content=user_message))
        full_content = []
        for chunk in self.llm.chat_stream(conv.messages):
            full_content.append(chunk)
            yield chunk
        conv.add_message(ChatMessage(role=Role.ASSISTANT, content="".join(full_content)))

    def clear_conversation(self, conv_id: str) -> bool:
        if conv_id in self.conversations:
            conv = self.conversations[conv_id]
            conv.messages = [ChatMessage(role=Role.SYSTEM, content=self.default_system_prompt)]
            conv.title = ""
            conv.updated_at = time.time()
            return True
        return False
