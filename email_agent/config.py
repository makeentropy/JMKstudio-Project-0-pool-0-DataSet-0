import os
import yaml
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class EmailConfig:
    address: str = "makeentropy@yeah.net"
    password: str = ""
    imap_server: str = "imap.yeah.net"
    imap_port: int = 993
    smtp_server: str = "smtp.yeah.net"
    smtp_port: int = 465
    use_ssl: bool = True


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    api_key: str = ""
    api_base: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False


@dataclass
class AgentConfig:
    auto_reply: bool = False
    check_interval: int = 60
    signature: str = "\n\nBest regards,\nEmail AI Assistant"
    language: str = "zh-CN"


@dataclass
class Config:
    email: EmailConfig = field(default_factory=EmailConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        if not os.path.exists(config_path):
            return cls()
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = cls()
        if "email" in data:
            for k, v in data["email"].items():
                if hasattr(config.email, k):
                    setattr(config.email, k, v)
        if "llm" in data:
            for k, v in data["llm"].items():
                if hasattr(config.llm, k):
                    setattr(config.llm, k, v)
        if "server" in data:
            for k, v in data["server"].items():
                if hasattr(config.server, k):
                    setattr(config.server, k, v)
        if "agent" in data:
            for k, v in data["agent"].items():
                if hasattr(config.agent, k):
                    setattr(config.agent, k, v)
        return config

    @classmethod
    def from_env(cls) -> "Config":
        config = cls()
        env_map = {
            "EMAIL_ADDRESS": ("email", "address"),
            "EMAIL_PASSWORD": ("email", "password"),
            "IMAP_SERVER": ("email", "imap_server"),
            "IMAP_PORT": ("email", "imap_port"),
            "SMTP_SERVER": ("email", "smtp_server"),
            "SMTP_PORT": ("email", "smtp_port"),
            "LLM_PROVIDER": ("llm", "provider"),
            "LLM_API_KEY": ("llm", "api_key"),
            "LLM_API_BASE": ("llm", "api_base"),
            "LLM_MODEL": ("llm", "model"),
            "LLM_TEMPERATURE": ("llm", "temperature"),
            "SERVER_HOST": ("server", "host"),
            "SERVER_PORT": ("server", "port"),
            "AGENT_AUTO_REPLY": ("agent", "auto_reply"),
            "AGENT_CHECK_INTERVAL": ("agent", "check_interval"),
        }
        for env_key, (section, attr) in env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                section_obj = getattr(config, section)
                attr_type = type(getattr(section_obj, attr))
                if attr_type == bool:
                    setattr(section_obj, attr, value.lower() in ("true", "1", "yes"))
                elif attr_type == int:
                    setattr(section_obj, attr, int(value))
                elif attr_type == float:
                    setattr(section_obj, attr, float(value))
                else:
                    setattr(section_obj, attr, value)
        return config

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        config = cls()
        if config_path and os.path.exists(config_path):
            config = cls.from_yaml(config_path)
        env_config = cls.from_env()
        for section in ["email", "llm", "server", "agent"]:
            section_obj = getattr(config, section)
            env_section = getattr(env_config, section)
            for attr in dir(env_section):
                if attr.startswith("_"):
                    continue
                env_val = getattr(env_section, attr)
                default_val = getattr(cls(), section)
                if env_val != getattr(default_val, attr):
                    setattr(section_obj, attr, env_val)
        return config
