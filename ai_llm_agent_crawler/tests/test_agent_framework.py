"""
Agent框架单元测试
"""

import pytest

from ai_llm_agent_crawler.agent_framework import (
    AgentConfig,
    LLMConfig,
    ContextConfig,
    Skill,
    SkillRegistry,
    Agent,
    AgentManager,
)


class TestAgentFrameworkStructure:
    """测试Agent框架结构"""

    def test_agent_config_structure(self):
        """测试Agent配置类结构"""
        llm_config = LLMConfig(model_name="gpt-4", temperature=0.5)
        context_config = ContextConfig(memory_limit=50)
        config = AgentConfig(
            name="TestAgent",
            description="测试Agent",
            llm_config=llm_config,
            context_config=context_config,
            skills=["Skill1", "Skill2"],
        )

        assert hasattr(config, "agent_id")
        assert config.name == "TestAgent"
        assert config.description == "测试Agent"
        assert config.llm_config.model_name == "gpt-4"
        assert config.context_config.memory_limit == 50
        assert "Skill1" in config.skills

    def test_agent_config_serialization(self):
        """测试Agent配置序列化"""
        config = AgentConfig(name="TestAgent")
        config_dict = config.to_dict()

        assert "agent_id" in config_dict
        assert "name" in config_dict
        assert "llm_config" in config_dict
        assert "context_config" in config_dict
        assert "created_at" in config_dict

        restored = AgentConfig.from_dict(config_dict)
        assert restored.name == "TestAgent"
        assert restored.llm_config.model_name == "gpt-4"

    def test_llm_config_defaults(self):
        """测试LLM配置默认值"""
        config = LLMConfig()

        assert config.model_name == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.timeout == 30

    def test_context_config_defaults(self):
        """测试上下文配置默认值"""
        config = ContextConfig()

        assert config.max_context_length == 8192
        assert config.memory_limit == 100
        assert config.enable_long_term_memory is False
        assert config.enable_short_term_memory is True


class TestSkillTemplateGeneration:
    """测试Skill模板生成"""

    def setup_method(self):
        """初始化测试环境"""
        self.registry = SkillRegistry()
        self.registry.clear()

    def test_create_skill_template_with_parameters(self):
        """测试创建带参数的技能模板"""
        parameters = [
            {"name": "query", "type": "string", "required": True},
            {"name": "limit", "type": "integer", "required": False},
        ]
        template = self.registry.create_skill_template(
            name="WebSearch",
            description="网络搜索技能",
            parameters=parameters,
        )

        assert "class WebSearch" in template
        assert 'name="WebSearch"' in template
        assert 'description="网络搜索技能"' in template
        assert '"query"' in template
        assert '"limit"' in template
        assert "execute" in template

    def test_create_skill_template_without_parameters(self):
        """测试创建无参数的技能模板"""
        template = self.registry.create_skill_template(
            name="HelloWorld",
            description="Hello World技能",
        )

        assert "class HelloWorld" in template
        assert 'name="HelloWorld"' in template
        assert "parameters=[]" in template

    def test_skill_template_import_statement(self):
        """测试技能模板导入语句"""
        template = self.registry.create_skill_template(
            name="TestSkill",
            description="测试技能",
        )

        assert "from ai_llm_agent_crawler.agent_framework import Skill" in template


class TestAgentSkillInvocation:
    """测试Agent能够正确调用Skill"""

    def setup_method(self):
        """初始化测试环境"""
        self.skill_registry = SkillRegistry()
        self.skill_registry.clear()
        self.agent_manager = AgentManager()
        self.agent_manager.clear()

    def test_agent_executes_registered_skill(self):
        """测试Agent执行已注册的技能"""

        class GreetSkill(Skill):
            def __init__(self):
                super().__init__(
                    name="GreetSkill",
                    description="问候技能",
                    parameters=[{"name": "name", "type": "string", "required": True}],
                )

            def execute(self, **kwargs):
                name = kwargs.get("name")
                return f"你好, {name}！"

        self.skill_registry.register_skill(GreetSkill)

        config = AgentConfig(
            name="TestAgent",
            skills=["GreetSkill"],
        )
        agent = self.agent_manager.create_agent(config)

        result = agent.execute("执行问候", name="Alice")

        assert "success" in result
        assert result["success"] is True
        assert len(result["plan"]) == 1
        assert result["plan"][0]["skill"] == "GreetSkill"
        assert result["plan"][0]["status"] == "completed"
        assert result["plan"][0]["result"] == "你好, Alice！"

    def test_agent_skips_unregistered_skill(self):
        """测试Agent跳过未注册的技能"""
        config = AgentConfig(
            name="TestAgent",
            skills=["NonExistentSkill"],
        )
        agent = self.agent_manager.create_agent(config)

        result = agent.execute("执行任务")

        assert len(result["plan"]) == 0

    def test_agent_think_method(self):
        """测试Agent思考方法"""
        config = AgentConfig(
            name="TestAgent",
            skills=["Skill1", "Skill2"],
        )
        agent = Agent(config)

        thoughts = agent.think("测试思考")

        assert "收到指令" in thoughts
        assert "可用技能" in thoughts
        assert "分析任务需求" in thoughts

    def test_agent_plan_method(self):
        """测试Agent计划方法"""

        class Skill1(Skill):
            def __init__(self):
                super().__init__(name="Skill1", description="技能1")

            def execute(self, **kwargs):
                return "skill1_result"

        self.skill_registry.register_skill(Skill1)

        config = AgentConfig(
            name="TestAgent",
            skills=["Skill1", "Skill2"],
        )
        agent = Agent(config)

        plan = agent.plan("测试计划")

        assert len(plan) == 1
        assert plan[0]["skill"] == "Skill1"
        assert plan[0]["status"] == "pending"

    def test_agent_communicate(self):
        """测试Agent通信能力"""
        config = AgentConfig(name="TestAgent")
        agent = Agent(config)

        response = agent.communicate("hello")
        assert "你好" in response

        response = agent.communicate("status")
        assert "空闲" in response

        response = agent.communicate("custom message")
        assert "收到消息" in response

    def test_agent_learn(self):
        """测试Agent学习能力"""
        config = AgentConfig(name="TestAgent")
        agent = Agent(config)

        experience = {"task": "测试", "result": "成功"}
        agent.learn(experience)

        context = agent.get_context()
        assert len(context) == 1
        assert context[0]["experience"]["task"] == "测试"

    def test_agent_context_memory_limit(self):
        """测试Agent上下文内存限制"""
        config = AgentConfig(
            name="TestAgent",
            context_config=ContextConfig(memory_limit=2),
        )
        agent = Agent(config)

        for i in range(5):
            agent.learn({"task": f"task_{i}"})

        context = agent.get_context()
        assert len(context) == 2


class TestSkillRegistry:
    """测试技能注册中心"""

    def setup_method(self):
        """初始化测试环境"""
        self.registry = SkillRegistry()
        self.registry.clear()

    def test_register_and_get_skill(self):
        """测试注册和获取技能"""

        class TestSkill(Skill):
            def __init__(self):
                super().__init__(name="TestSkill", description="测试技能")

            def execute(self, **kwargs):
                return "test_result"

        self.registry.register_skill(TestSkill)
        skill_class = self.registry.get_skill("TestSkill")

        assert skill_class is not None
        assert skill_class.__name__ == "TestSkill"

    def test_register_duplicate_skill(self):
        """测试注册重复技能"""

        class TestSkill(Skill):
            def __init__(self):
                super().__init__(name="TestSkill", description="测试技能")

            def execute(self, **kwargs):
                return "test_result"

        self.registry.register_skill(TestSkill)

        with pytest.raises(ValueError, match="已注册"):
            self.registry.register_skill(TestSkill)

    def test_list_skills(self):
        """测试列出技能"""

        class Skill1(Skill):
            def __init__(self):
                super().__init__(name="Skill1", description="技能1")

            def execute(self, **kwargs):
                pass

        class Skill2(Skill):
            def __init__(self):
                super().__init__(name="Skill2", description="技能2")

            def execute(self, **kwargs):
                pass

        self.registry.register_skill(Skill1)
        self.registry.register_skill(Skill2)

        skills = self.registry.list_skills()

        assert len(skills) == 2
        skill_names = [s["name"] for s in skills]
        assert "Skill1" in skill_names
        assert "Skill2" in skill_names

    def test_create_skill_instance(self):
        """测试创建技能实例"""

        class TestSkill(Skill):
            def __init__(self):
                super().__init__(name="TestSkill", description="测试技能")

            def execute(self, **kwargs):
                return "test_result"

        self.registry.register_skill(TestSkill)
        instance = self.registry.create_skill_instance("TestSkill")

        assert instance is not None
        assert instance.name == "TestSkill"


class TestAgentManager:
    """测试Agent管理类"""

    def setup_method(self):
        """初始化测试环境"""
        self.manager = AgentManager()
        self.manager.clear()

    def test_create_and_get_agent(self):
        """测试创建和获取Agent"""
        config = AgentConfig(name="TestAgent")
        agent = self.manager.create_agent(config)

        retrieved = self.manager.get_agent(config.agent_id)
        assert retrieved is not None
        assert retrieved.config.name == "TestAgent"

    def test_list_agents(self):
        """测试列出Agent"""
        config1 = AgentConfig(name="Agent1")
        config2 = AgentConfig(name="Agent2")
        self.manager.create_agent(config1)
        self.manager.create_agent(config2)

        agents = self.manager.list_agents()
        assert len(agents) == 2
        agent_names = [a["name"] for a in agents]
        assert "Agent1" in agent_names
        assert "Agent2" in agent_names

    def test_run_agent(self):
        """测试运行Agent"""
        config = AgentConfig(name="TestAgent", skills=[])
        agent = self.manager.create_agent(config)

        result = self.manager.run_agent(config.agent_id, "测试任务")
        assert "task" in result
        assert result["task"] == "测试任务"

    def test_stop_agent(self):
        """测试停止Agent"""
        config = AgentConfig(name="TestAgent")
        agent = self.manager.create_agent(config)
        agent.is_running = True

        result = self.manager.stop_agent(config.agent_id)
        assert result is True
        assert agent.is_running is False

    def test_delete_agent(self):
        """测试删除Agent"""
        config = AgentConfig(name="TestAgent")
        self.manager.create_agent(config)

        result = self.manager.delete_agent(config.agent_id)
        assert result is True
        assert self.manager.get_agent(config.agent_id) is None