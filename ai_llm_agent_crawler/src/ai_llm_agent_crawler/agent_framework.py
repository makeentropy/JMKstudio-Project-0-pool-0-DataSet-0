"""
LLM Agent开发框架

提供Agent配置、技能系统、Agent核心类和管理功能
"""

from typing import Any, Dict, List, Optional, Type, Callable
from abc import ABC, abstractmethod
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class LLMConfig:
    """LLM模型配置"""
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30


@dataclass
class ContextConfig:
    """上下文配置"""
    max_context_length: int = 8192
    memory_limit: int = 100
    enable_long_term_memory: bool = False
    enable_short_term_memory: bool = True


@dataclass
class AgentConfig:
    """Agent配置类"""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Agent"
    description: str = "LLM Agent"
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    context_config: ContextConfig = field(default_factory=ContextConfig)
    skills: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["llm_config"] = asdict(self.llm_config)
        data["context_config"] = asdict(self.context_config)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """从字典创建配置"""
        data = data.copy()
        data["llm_config"] = LLMConfig(**data.get("llm_config", {}))
        data["context_config"] = ContextConfig(**data.get("context_config", {}))
        data["created_at"] = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        data["updated_at"] = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        return cls(**data)


class Skill(ABC):
    """技能基类"""

    def __init__(self, name: str, description: str, parameters: Optional[List[Dict[str, Any]]] = None):
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        """验证参数定义"""
        for param in self.parameters:
            if "name" not in param:
                raise ValueError(f"参数定义缺少'name'字段: {param}")
            if "type" not in param:
                param["type"] = "string"
            if "required" not in param:
                param["required"] = False

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行技能"""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """获取技能元数据"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "type": self.__class__.__name__,
        }

    def validate_arguments(self, **kwargs) -> bool:
        """验证执行参数"""
        for param in self.parameters:
            param_name = param["name"]
            if param.get("required", False) and param_name not in kwargs:
                raise ValueError(f"缺少必需参数: {param_name}")
        return True


class SkillRegistry:
    """技能注册中心"""

    _instance = None
    _skills: Dict[str, Type[Skill]] = {}

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._skills = {}
        return cls._instance

    def register_skill(self, skill_class: Type[Skill]) -> None:
        """注册技能"""
        if not issubclass(skill_class, Skill):
            raise ValueError("必须继承Skill基类")
        
        skill_instance = skill_class.__new__(skill_class)
        skill_name = getattr(skill_instance, 'name', skill_class.__name__)
        
        if skill_name in self._skills:
            raise ValueError(f"技能 '{skill_name}' 已注册")
        
        self._skills[skill_name] = skill_class

    def get_skill(self, skill_name: str) -> Optional[Type[Skill]]:
        """获取技能类"""
        return self._skills.get(skill_name)

    def create_skill_instance(self, skill_name: str, **kwargs) -> Optional[Skill]:
        """创建技能实例"""
        skill_class = self.get_skill(skill_name)
        if skill_class:
            return skill_class(**kwargs)
        return None

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有技能"""
        result = []
        for name, skill_class in self._skills.items():
            skill_instance = skill_class.__new__(skill_class)
            result.append({
                "name": getattr(skill_instance, 'name', name),
                "description": getattr(skill_instance, 'description', ''),
                "class_name": skill_class.__name__,
            })
        return result

    def create_skill_template(self, name: str, description: str, parameters: Optional[List[Dict[str, Any]]] = None) -> str:
        """创建技能模板"""
        parameters = parameters or []
        params_code = json.dumps(parameters, indent=4, ensure_ascii=False)

        args_doc = ", ".join([f"{p['name']}: {p.get('type', 'Any')}" for p in parameters])

        template = f'''from ai_llm_agent_crawler.agent_framework import Skill


class {name.replace(' ', '')}(Skill):
    """{description}"""

    def __init__(self):
        super().__init__(
            name="{name}",
            description="{description}",
            parameters={params_code}
        )

    def execute(self, **kwargs):
        """
        执行技能
        
        Args:
            {args_doc}
        
        Returns:
            Any: 执行结果
        """
        # 实现技能逻辑
        pass
'''
        return template

    def clear(self) -> None:
        """清空所有注册的技能"""
        self._skills.clear()


class Agent:
    """LLM Agent核心类"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.skill_registry = SkillRegistry()
        self.context: List[Dict[str, Any]] = []
        self.is_running = False

    def think(self, prompt: str) -> str:
        """思考过程"""
        thoughts = [
            f"收到指令: {prompt}",
            f"可用技能: {self.config.skills}",
            "分析任务需求...",
            "确定执行策略...",
        ]
        return "\n".join(thoughts)

    def plan(self, task: str) -> List[Dict[str, Any]]:
        """制定计划"""
        plan: List[Dict[str, Any]] = []
        for skill_name in self.config.skills:
            skill = self.skill_registry.get_skill(skill_name)
            if skill:
                plan.append({
                    "step": len(plan) + 1,
                    "skill": skill_name,
                    "description": f"执行技能: {skill_name}",
                    "status": "pending",
                })
        return plan

    def execute(self, task: str, **kwargs) -> Dict[str, Any]:
        """执行任务"""
        self.is_running = True
        try:
            thoughts = self.think(task)
            plan = self.plan(task)
            
            results = []
            for step in plan:
                skill_name = step["skill"]
                skill_instance = self.skill_registry.create_skill_instance(skill_name)
                if skill_instance:
                    try:
                        result = skill_instance.execute(**kwargs)
                        step["status"] = "completed"
                        step["result"] = result
                    except Exception as e:
                        step["status"] = "failed"
                        step["error"] = str(e)
                results.append(step)
            
            self._update_context(task, results)
            
            return {
                "task": task,
                "thoughts": thoughts,
                "plan": plan,
                "results": results,
                "success": all(step["status"] == "completed" for step in plan),
            }
        finally:
            self.is_running = False

    def learn(self, experience: Dict[str, Any]) -> None:
        """学习能力"""
        learning_entry = {
            "timestamp": datetime.now().isoformat(),
            "experience": experience,
        }
        self.context.append(learning_entry)
        
        if len(self.context) > self.config.context_config.memory_limit:
            self.context = self.context[-self.config.context_config.memory_limit:]

    def communicate(self, message: str, **kwargs) -> str:
        """通信能力"""
        responses = {
            "hello": "你好！我是Agent，很高兴为你服务。",
            "status": f"Agent状态: {'运行中' if self.is_running else '空闲'}",
            "skills": f"可用技能: {', '.join(self.config.skills)}",
        }
        
        for key, response in responses.items():
            if key in message.lower():
                return response
        
        return f"收到消息: {message}"

    def _update_context(self, task: str, results: List[Dict[str, Any]]) -> None:
        """更新上下文"""
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "results": results,
        }
        self.context.append(context_entry)
        
        if len(self.context) > self.config.context_config.memory_limit:
            self.context = self.context[-self.config.context_config.memory_limit:]

    def get_context(self) -> List[Dict[str, Any]]:
        """获取上下文"""
        return self.context

    def clear_context(self) -> None:
        """清空上下文"""
        self.context = []


class AgentManager:
    """Agent管理类"""

    _instance = None
    _agents: Dict[str, Agent] = {}

    def __new__(cls) -> "AgentManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._agents = {}
        return cls._instance

    def create_agent(self, config: AgentConfig) -> Agent:
        """创建Agent"""
        if config.agent_id in self._agents:
            raise ValueError(f"Agent '{config.agent_id}' 已存在")
        
        agent = Agent(config)
        self._agents[config.agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取Agent"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有Agent"""
        result = []
        for agent_id, agent in self._agents.items():
            result.append({
                "agent_id": agent_id,
                "name": agent.config.name,
                "description": agent.config.description,
                "skills": agent.config.skills,
                "is_running": agent.is_running,
            })
        return result

    def run_agent(self, agent_id: str, task: str, **kwargs) -> Dict[str, Any]:
        """运行Agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' 不存在")
        
        return agent.execute(task, **kwargs)

    def stop_agent(self, agent_id: str) -> bool:
        """停止Agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' 不存在")
        
        agent.is_running = False
        return True

    def delete_agent(self, agent_id: str) -> bool:
        """删除Agent"""
        if agent_id not in self._agents:
            raise ValueError(f"Agent '{agent_id}' 不存在")
        
        del self._agents[agent_id]
        return True

    def clear(self) -> None:
        """清空所有Agent"""
        self._agents.clear()