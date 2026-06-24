from .config import Config
from .email_service import EmailService
from .llm import LLMFactory
from .agent import ChatAgent, EmailAgent
from .server import HTTPServer
from .terminal import TerminalShell

__version__ = "1.0.0"
__all__ = [
    "Config",
    "EmailService",
    "LLMFactory",
    "ChatAgent",
    "EmailAgent",
    "HTTPServer",
    "TerminalShell",
]
