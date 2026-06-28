"""
Skill生成引擎模块

基于数据集生成可执行的Skill代码或配置：
- 从数据集模式生成Skill模板
- 从标注规则生成Skill逻辑
- 支持多种Skill类型（爬虫、处理、分析等）
- Skill版本管理和发布
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.schema import (
    AnnotationMethod,
    DataType,
    DatasetSchema,
    DatasetType,
    FieldSchema,
    LabelSchema,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class SkillType(str):
    """Skill类型"""

    CRAWLER = "crawler"  # 爬虫Skill
    PROCESSOR = "processor"  # 数据处理Skill
    ANALYZER = "analyzer"  # 分析Skill
    ANNOTATOR = "annotator"  # 标注Skill
    VALIDATOR = "validator"  # 验证Skill
    TRANSFORMER = "transformer"  # 转换Skill
    EXPORTER = "exporter"  # 导出Skill


class SkillStatus(str):
    """Skill状态"""

    DRAFT = "draft"  # 草稿
    TESTING = "testing"  # 测试中
    ACTIVE = "active"  # 活跃
    DEPRECATED = "deprecated"  # 已弃用
    ARCHIVED = "archived"  # 已归档


class SkillMetadata(BaseModel):
    """Skill元数据"""

    id: str = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill名称")
    version: str = Field(default="1.0.0", description="版本")
    description: str = Field(default="", description="描述")
    skill_type: str = Field(default=SkillType.PROCESSOR, description="Skill类型")
    status: str = Field(default=SkillStatus.DRAFT, description="状态")

    # 来源信息
    dataset_id: str = Field(default="", description="来源数据集ID")
    dataset_name: str = Field(default="", description="来源数据集名称")
    dataset_version: str = Field(default="", description="来源数据集版本")
    generated_from: str = Field(default="dataset", description="生成来源")

    # 依赖和配置
    dependencies: List[str] = Field(default_factory=list, description="依赖列表")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")

    # 性能指标
    accuracy: float = Field(default=0.0, description="准确率")
    efficiency: float = Field(default=0.0, description="效率")
    success_rate: float = Field(default=0.0, description="成功率")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")

    # 标签和分类
    tags: List[str] = Field(default_factory=list, description="标签")
    categories: List[str] = Field(default_factory=list, description="分类")

    # 作者信息
    author: str = Field(default="system", description="作者")
    license: str = Field(default="MIT", description="许可证")


class SkillTemplate(BaseModel):
    """Skill模板"""

    name: str = Field(..., description="模板名称")
    skill_type: str = Field(..., description="Skill类型")
    template_code: str = Field(default="", description="模板代码")
    template_config: Dict[str, Any] = Field(default_factory=dict, description="模板配置")
    variables: Dict[str, Any] = Field(default_factory=dict, description="模板变量")
    description: str = Field(default="", description="模板描述")


class GeneratedSkill(BaseModel):
    """生成的Skill"""

    metadata: SkillMetadata = Field(..., description="Skill元数据")
    code: str = Field(default="", description="Skill代码")
    config: Dict[str, Any] = Field(default_factory=dict, description="Skill配置")
    test_cases: List[Dict[str, Any]] = Field(default_factory=list, description="测试用例")
    documentation: str = Field(default="", description="Skill文档")


class SkillGenerationConfig(BaseModel):
    """Skill生成配置"""

    skill_type: str = Field(default=SkillType.PROCESSOR, description="Skill类型")
    language: str = Field(default="python", description="编程语言")
    output_dir: Path = Field(default=Path("skills"), description="输出目录")
    include_tests: bool = Field(default=True, description="是否包含测试")
    include_docs: bool = Field(default=True, description="是否包含文档")
    optimize_code: bool = Field(default=True, description="是否优化代码")
    template_name: Optional[str] = Field(default=None, description="模板名称")

    class Config:
        arbitrary_types_allowed = True


class SkillCodeGenerator:
    """Skill代码生成器"""

    def __init__(self):
        """初始化代码生成器"""
        self.templates: Dict[str, SkillTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """加载默认模板"""
        # 爬虫Skill模板
        crawler_template = SkillTemplate(
            name="basic_crawler",
            skill_type=SkillType.CRAWLER,
            template_code=self._get_crawler_template(),
            description="基础爬虫Skill模板",
        )
        self.templates["basic_crawler"] = crawler_template

        # 处理器Skill模板
        processor_template = SkillTemplate(
            name="basic_processor",
            skill_type=SkillType.PROCESSOR,
            template_code=self._get_processor_template(),
            description="基础数据处理Skill模板",
        )
        self.templates["basic_processor"] = processor_template

        # 标注器Skill模板
        annotator_template = SkillTemplate(
            name="rule_annotator",
            skill_type=SkillType.ANNOTATOR,
            template_code=self._get_annotator_template(),
            description="规则标注Skill模板",
        )
        self.templates["rule_annotator"] = annotator_template

        # 验证器Skill模板
        validator_template = SkillTemplate(
            name="basic_validator",
            skill_type=SkillType.VALIDATOR,
            template_code=self._get_validator_template(),
            description="基础验证Skill模板",
        )
        self.templates["basic_validator"] = validator_template

    def _get_crawler_template(self) -> str:
        """获取爬虫模板"""
        return '''
"""
{name} - 爬虫Skill

自动生成的爬虫技能，用于{description}
"""

from typing import Any, Dict, List, Optional
from ai_llm_agent_crawler.crawler.base import BaseCrawler
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class {class_name}(BaseCrawler):
    """{name}爬虫"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化爬虫"""
        super().__init__(config or {})
        self.name = "{name}"
        self.version = "{version}"

    async def crawl(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        执行爬取

        Args:
            url: 目标URL
            **kwargs: 额外参数

        Returns:
            爬取结果
        """
        # {crawl_logic}
        result = await self._fetch(url)
        return result

    async def _fetch(self, url: str) -> Dict[str, Any]:
        """获取数据"""
        # 实现具体爬取逻辑
        pass

    def parse(self, response: Any) -> List[Dict[str, Any]]:
        """
        解析响应

        Args:
            response: HTTP响应

        Returns:
            解析后的数据列表
        """
        # {parse_logic}
        data = []
        return data
'''

    def _get_processor_template(self) -> str:
        """获取处理器模板"""
        return '''
"""
{name} - 数据处理Skill

自动生成的处理技能，用于{description}
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from ai_llm_agent_crawler.dataset.processor import DataProcessor
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class {class_name}:
    """{name}数据处理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化处理器"""
        self.config = config or {}
        self.name = "{name}"
        self.version = "{version}"
        self.processor = DataProcessor()

    def process(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        处理数据

        Args:
            data: 输入数据
            **kwargs: 额外参数

        Returns:
            处理后的数据
        """
        # {process_logic}
        self.processor.set_data(data)
        return self.processor.get_result()

    def validate(self, data: pd.DataFrame) -> bool:
        """验证数据"""
        # {validation_logic}
        return True

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """转换数据"""
        # {transform_logic}
        return data
'''

    def _get_annotator_template(self) -> str:
        """获取标注器模板"""
        return '''
"""
{name} - 标注Skill

自动生成的标注技能，用于{description}
"""

from typing import Any, Dict, List, Optional, Tuple, Callable
from ai_llm_agent_crawler.dataset.annotator import RuleBasedAnnotator, AnnotationResult
from ai_llm_agent_crawler.dataset.schema import DatasetRecord, LabelSchema
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class {class_name}(RuleBasedAnnotator):
    """{name}标注器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化标注器"""
        super().__init__(name="{name}")
        self.config = config or {}
        self.version = "{version}"
        self._setup_rules()

    def _setup_rules(self) -> None:
        """设置标注规则"""
        # {rules_setup}
        pass

    def add_custom_rule(self, label_name: str, rule_func: Callable) -> None:
        """添加自定义规则"""
        self.add_rule(label_name, rule_func)
'''

    def _get_validator_template(self) -> str:
        """获取验证器模板"""
        return '''
"""
{name} - 验证Skill

自动生成的验证技能，用于{description}
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from ai_llm_agent_crawler.dataset.quality_validator import QualityValidator, ValidationReport
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class {class_name}:
    """{name}验证器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化验证器"""
        self.config = config or {}
        self.name = "{name}"
        self.version = "{version}"
        self.validator = QualityValidator()

    def validate(self, data: pd.DataFrame) -> ValidationReport:
        """
        验证数据

        Args:
            data: 输入数据

        Returns:
            验证报告
        """
        # {validation_rules}
        report = self.validator.validate(data)
        return report

    def check_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """检查数据质量"""
        report = self.validate(data)
        return {
            "quality_score": report.quality_score,
            "quality_level": report.quality_level,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
        }
'''

    def register_template(self, template: SkillTemplate) -> None:
        """
        注册模板

        Args:
            template: Skill模板
        """
        self.templates[template.name] = template
        logger.info(f"注册Skill模板: {template.name}")

    def get_template(self, name: str) -> Optional[SkillTemplate]:
        """
        获取模板

        Args:
            name: 模板名称

        Returns:
            Skill模板
        """
        return self.templates.get(name)

    def generate_code(
        self,
        template_name: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        生成Skill代码

        Args:
            template_name: 模板名称
            variables: 变量字典

        Returns:
            生成的代码
        """
        template = self.get_template(template_name)
        if template is None:
            logger.error(f"模板 '{template_name}' 不存在")
            return ""

        code = template.template_code

        # 替换变量
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            code = code.replace(placeholder, str(value))

        return code

    def generate_class_name(self, skill_name: str) -> str:
        """生成类名"""
        # 将名称转换为有效的Python类名
        words = skill_name.replace("-", "_").replace(" ", "_").split("_")
        return "".join(word.capitalize() for word in words)


class SkillEngine:
    """Skill生成引擎"""

    def __init__(self, config: Optional[SkillGenerationConfig] = None):
        """
        初始化Skill生成引擎

        Args:
            config: 生成配置
        """
        self.config = config or SkillGenerationConfig()
        self.code_generator = SkillCodeGenerator()
        self.generated_skills: Dict[str, GeneratedSkill] = {}
        self.skill_registry: Dict[str, SkillMetadata] = {}

        # 确保输出目录存在
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """确保输出目录存在"""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_schema(
        self,
        schema: DatasetSchema,
        skill_type: Optional[str] = None,
        custom_rules: Optional[Dict[str, Callable]] = None,
    ) -> GeneratedSkill:
        """
        从数据集模式生成Skill

        Args:
            schema: 数据集模式
            skill_type: Skill类型
            custom_rules: 自定义规则

        Returns:
            生成的Skill
        """
        skill_type = skill_type or self.config.skill_type

        # 确定模板
        template_name = self._select_template(skill_type, schema)

        # 准备变量
        variables = self._prepare_variables(schema, skill_type)

        # 生成代码
        code = self.code_generator.generate_code(template_name, variables)

        # 添加自定义规则逻辑
        if custom_rules:
            code = self._inject_custom_rules(code, custom_rules)

        # 生成元数据
        skill_id = self._generate_skill_id(schema.name, skill_type)
        metadata = SkillMetadata(
            id=skill_id,
            name=f"{schema.name}_{skill_type}",
            description=f"基于数据集 {schema.name} 生成的 {skill_type} Skill",
            skill_type=skill_type,
            dataset_id=schema.name,
            dataset_name=schema.name,
            dataset_version=schema.version,
            generated_from="schema",
        )

        # 生成配置
        skill_config = self._generate_config_from_schema(schema)

        # 生成测试用例
        test_cases = self._generate_test_cases(schema)

        # 生成文档
        documentation = self._generate_documentation(schema, skill_type)

        skill = GeneratedSkill(
            metadata=metadata,
            code=code,
            config=skill_config,
            test_cases=test_cases,
            documentation=documentation,
        )

        # 注册Skill
        self.generated_skills[skill_id] = skill
        self.skill_registry[skill_id] = metadata

        logger.info(f"从模式生成Skill: {skill_id}")

        return skill

    def generate_from_rules(
        self,
        rules: Dict[str, Callable],
        skill_name: str,
        skill_type: str = SkillType.ANNOTATOR,
    ) -> GeneratedSkill:
        """
        从标注规则生成Skill

        Args:
            rules: 标注规则字典
            skill_name: Skill名称
            skill_type: Skill类型

        Returns:
            生成的Skill
        """
        # 选择模板
        template_name = "rule_annotator"

        # 准备变量
        variables = {
            "name": skill_name,
            "class_name": self.code_generator.generate_class_name(skill_name),
            "version": "1.0.0",
            "description": "基于规则的标注Skill",
            "rules_setup": self._generate_rules_setup_code(rules),
        }

        # 生成代码
        code = self.code_generator.generate_code(template_name, variables)

        # 生成元数据
        skill_id = self._generate_skill_id(skill_name, skill_type)
        metadata = SkillMetadata(
            id=skill_id,
            name=skill_name,
            description=f"基于规则生成的 {skill_type} Skill",
            skill_type=skill_type,
            generated_from="rules",
        )

        # 生成配置
        skill_config = {"rules": list(rules.keys())}

        skill = GeneratedSkill(
            metadata=metadata,
            code=code,
            config=skill_config,
            documentation=self._generate_rules_documentation(rules),
        )

        # 注册Skill
        self.generated_skills[skill_id] = skill
        self.skill_registry[skill_id] = metadata

        logger.info(f"从规则生成Skill: {skill_id}")

        return skill

    def _select_template(self, skill_type: str, schema: DatasetSchema) -> str:
        """选择模板"""
        template_mapping = {
            SkillType.CRAWLER: "basic_crawler",
            SkillType.PROCESSOR: "basic_processor",
            SkillType.ANNOTATOR: "rule_annotator",
            SkillType.VALIDATOR: "basic_validator",
        }
        return template_mapping.get(skill_type, "basic_processor")

    def _prepare_variables(self, schema: DatasetSchema, skill_type: str) -> Dict[str, Any]:
        """准备模板变量"""
        class_name = self.code_generator.generate_class_name(f"{schema.name}_{skill_type}")

        variables = {
            "name": f"{schema.name}_{skill_type}",
            "class_name": class_name,
            "version": "1.0.0",
            "description": schema.description or f"基于数据集 {schema.name} 的 {skill_type} Skill",
        }

        # 添加特定类型的逻辑代码
        if skill_type == SkillType.PROCESSOR:
            variables["process_logic"] = self._generate_process_logic(schema)
            variables["validation_logic"] = self._generate_validation_logic(schema)
            variables["transform_logic"] = self._generate_transform_logic(schema)

        elif skill_type == SkillType.ANNOTATOR:
            variables["rules_setup"] = self._generate_annotator_rules_setup(schema)

        elif skill_type == SkillType.VALIDATOR:
            variables["validation_rules"] = self._generate_validation_setup(schema)

        return variables

    def _generate_process_logic(self, schema: DatasetSchema) -> str:
        """生成处理逻辑"""
        logic_lines = []

        for field in schema.fields:
            logic_lines.append(f"# 处理字段 '{field.name}'")
            if field.data_type == "str":
                logic_lines.append(f"self.processor.apply_column('{field.name}', lambda x: str(x).strip() if x else '')")
            elif field.data_type == "int":
                logic_lines.append(f"self.processor.apply_column('{field.name}', lambda x: int(x) if x else 0)")

        return "\n        ".join(logic_lines)

    def _generate_validation_logic(self, schema: DatasetSchema) -> str:
        """生成验证逻辑"""
        logic_lines = ["# 验证数据"]

        required_fields = [f.name for f in schema.fields if not f.nullable]
        if required_fields:
            logic_lines.append(f"required_fields = {required_fields}")
            logic_lines.append("for field in required_fields:")
            logic_lines.append("    if field not in data.columns:")
            logic_lines.append("        return False")

        return "\n        ".join(logic_lines)

    def _generate_transform_logic(self, schema: DatasetSchema) -> str:
        """生成转换逻辑"""
        logic_lines = ["# 转换数据"]

        # 添加类型转换逻辑
        for field in schema.fields:
            logic_lines.append(f"# 转换字段 '{field.name}' 为 {field.data_type}")

        return "\n        ".join(logic_lines)

    def _generate_annotator_rules_setup(self, schema: DatasetSchema) -> str:
        """生成标注器规则设置"""
        setup_lines = ["# 设置标注规则"]

        for label in schema.labels:
            setup_lines.append(f"# 标签 '{label.name}' 的规则")
            if label.annotation_method == AnnotationMethod.RULE_BASED:
                setup_lines.append(f"self.add_rule('{label.name}', self._{label.name}_rule)")

        return "\n        ".join(setup_lines)

    def _generate_validation_setup(self, schema: DatasetSchema) -> str:
        """生成验证设置"""
        setup_lines = ["# 设置验证规则"]

        for field in schema.fields:
            if field.min_value is not None or field.max_value is not None:
                setup_lines.append(f"# 字段 '{field.name}' 范围验证")

        return "\n        ".join(setup_lines)

    def _generate_rules_setup_code(self, rules: Dict[str, Callable]) -> str:
        """生成规则设置代码"""
        setup_lines = ["# 设置标注规则"]

        for label_name in rules.keys():
            setup_lines.append(f"# 标签 '{label_name}' 的规则")
            setup_lines.append(f"self.add_rule('{label_name}', custom_{label_name}_rule)")

        return "\n        ".join(setup_lines)

    def _inject_custom_rules(self, code: str, rules: Dict[str, Callable]) -> str:
        """注入自定义规则"""
        # 在代码中注入自定义规则定义
        rules_code = "\n\n    # 自定义规则定义\n"
        for label_name, rule_func in rules.items():
            rules_code += f"    def custom_{label_name}_rule(self, data: Dict) -> Tuple[Any, float]:\n"
            rules_code += f"        # 自定义规则逻辑\n"
            rules_code += f"        pass\n\n"

        return code + rules_code

    def _generate_config_from_schema(self, schema: DatasetSchema) -> Dict[str, Any]:
        """从模式生成配置"""
        config = {
            "schema_name": schema.name,
            "schema_version": schema.version,
            "fields": [f.name for f in schema.fields],
            "labels": [l.name for l in schema.labels],
            "data_type": schema.data_type,
            "dataset_type": schema.dataset_type,
        }
        return config

    def _generate_test_cases(self, schema: DatasetSchema) -> List[Dict[str, Any]]:
        """生成测试用例"""
        test_cases = []

        # 生成基本测试用例
        test_cases.append({
            "name": "basic_test",
            "description": "基本功能测试",
            "input": self._generate_sample_data(schema),
            "expected_output": "valid",
        })

        # 生成边界测试用例
        test_cases.append({
            "name": "boundary_test",
            "description": "边界值测试",
            "input": self._generate_boundary_data(schema),
            "expected_output": "valid",
        })

        return test_cases

    def _generate_sample_data(self, schema: DatasetSchema) -> Dict[str, Any]:
        """生成样本数据"""
        data = {}
        for field in schema.fields:
            if field.data_type == "str":
                data[field.name] = "sample_text"
            elif field.data_type == "int":
                data[field.name] = 0
            elif field.data_type == "float":
                data[field.name] = 0.0
            elif field.data_type == "bool":
                data[field.name] = False
            elif field.default is not None:
                data[field.name] = field.default
            else:
                data[field.name] = None
        return data

    def _generate_boundary_data(self, schema: DatasetSchema) -> Dict[str, Any]:
        """生成边界数据"""
        data = {}
        for field in schema.fields:
            if field.min_value is not None:
                data[field.name] = field.min_value
            elif field.max_value is not None:
                data[field.name] = field.max_value
            else:
                data[field.name] = None
        return data

    def _generate_documentation(self, schema: DatasetSchema, skill_type: str) -> str:
        """生成文档"""
        doc = f"""
# {schema.name}_{skill_type} Skill

## 描述
{schema.description}

## 来源数据集
- 名称: {schema.name}
- 版本: {schema.version}
- 类型: {schema.dataset_type}
- 数据类型: {schema.data_type}

## 字段
"""
        for field in schema.fields:
            doc += f"- `{field.name}` ({field.data_type}): {field.description}\n"

        doc += "\n## 标签\n"
        for label in schema.labels:
            doc += f"- `{label.name}` ({label.label_type}): {label.description}\n"

        doc += """
## 使用方法
```python
from ai_llm_agent_crawler.skills import {class_name}

skill = {class_name}()
result = skill.process(data)
```

## 配置
"""
        doc += json.dumps(self._generate_config_from_schema(schema), indent=2)

        return doc

    def _generate_rules_documentation(self, rules: Dict[str, Callable]) -> str:
        """生成规则文档"""
        doc = """
# 标注规则Skill

## 描述
基于自定义规则的标注Skill

## 规则
"""
        for label_name in rules.keys():
            doc += f"- `{label_name}`: 自定义规则\n"

        return doc

    def _generate_skill_id(self, base_name: str, skill_type: str) -> str:
        """生成Skill ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_input = f"{base_name}_{skill_type}_{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{base_name}_{skill_type}_{hash_value}"

    def export_skill(
        self,
        skill_id: str,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        导出Skill到文件

        Args:
            skill_id: Skill ID
            output_dir: 输出目录

        Returns:
            导出的文件路径
        """
        skill = self.generated_skills.get(skill_id)
        if skill is None:
            raise ValueError(f"Skill '{skill_id}' 不存在")

        output_dir = output_dir or self.config.output_dir
        skill_dir = output_dir / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 导出代码
        code_file = skill_dir / "skill.py"
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(skill.code)

        # 导出配置
        config_file = skill_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(skill.config, f, ensure_ascii=False, indent=2)

        # 导出元数据
        metadata_file = skill_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(skill.metadata.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        # 导出测试用例
        if skill.test_cases:
            tests_file = skill_dir / "tests.json"
            with open(tests_file, "w", encoding="utf-8") as f:
                json.dump(skill.test_cases, f, ensure_ascii=False, indent=2)

        # 导出文档
        if skill.documentation:
            docs_file = skill_dir / "README.md"
            with open(docs_file, "w", encoding="utf-8") as f:
                f.write(skill.documentation)

        logger.info(f"Skill已导出到: {skill_dir}")
        return skill_dir

    def import_skill(self, skill_dir: Path) -> GeneratedSkill:
        """
        从文件导入Skill

        Args:
            skill_dir: Skill目录

        Returns:
            导入的Skill
        """
        # 读取元数据
        metadata_file = skill_dir / "metadata.json"
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata_dict = json.load(f)
        metadata = SkillMetadata(**metadata_dict)

        # 读取代码
        code_file = skill_dir / "skill.py"
        with open(code_file, "r", encoding="utf-8") as f:
            code = f.read()

        # 读取配置
        config_file = skill_dir / "config.json"
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 读取测试用例
        tests_file = skill_dir / "tests.json"
        test_cases = []
        if tests_file.exists():
            with open(tests_file, "r", encoding="utf-8") as f:
                test_cases = json.load(f)

        # 读取文档
        docs_file = skill_dir / "README.md"
        documentation = ""
        if docs_file.exists():
            with open(docs_file, "r", encoding="utf-8") as f:
                documentation = f.read()

        skill = GeneratedSkill(
            metadata=metadata,
            code=code,
            config=config,
            test_cases=test_cases,
            documentation=documentation,
        )

        # 注册Skill
        self.generated_skills[metadata.id] = skill
        self.skill_registry[metadata.id] = metadata

        logger.info(f"Skill已导入: {metadata.id}")
        return skill

    def list_skills(self) -> List[SkillMetadata]:
        """列出所有Skill"""
        return list(self.skill_registry.values())

    def get_skill(self, skill_id: str) -> Optional[GeneratedSkill]:
        """获取Skill"""
        return self.generated_skills.get(skill_id)

    def update_skill_status(self, skill_id: str, status: str) -> None:
        """
        更新Skill状态

        Args:
            skill_id: Skill ID
            status: 新状态
        """
        metadata = self.skill_registry.get(skill_id)
        if metadata:
            metadata.status = status
            metadata.updated_at = datetime.now()
            if status == SkillStatus.ACTIVE:
                metadata.published_at = datetime.now()
            logger.info(f"Skill '{skill_id}' 状态更新为: {status}")

    def delete_skill(self, skill_id: str) -> None:
        """删除Skill"""
        if skill_id in self.generated_skills:
            del self.generated_skills[skill_id]
        if skill_id in self.skill_registry:
            del self.skill_registry[skill_id]
        logger.info(f"Skill已删除: {skill_id}")

    def generate_skill_package(
        self,
        skill_ids: List[str],
        package_name: str,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        生成Skill包

        Args:
            skill_ids: Skill ID列表
            package_name: 包名称
            output_dir: 输出目录

        Returns:
            包目录路径
        """
        output_dir = output_dir or self.config.output_dir
        package_dir = output_dir / package_name
        package_dir.mkdir(parents=True, exist_ok=True)

        # 创建包结构
        skills_dir = package_dir / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # 导出所有Skill
        for skill_id in skill_ids:
            skill = self.get_skill(skill_id)
            if skill:
                skill_file = skills_dir / f"{skill.metadata.name}.py"
                with open(skill_file, "w", encoding="utf-8") as f:
                    f.write(skill.code)

        # 创建包__init__.py
        init_file = skills_dir / "__init__.py"
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(f'"""\n{package_name} - Skill包\n"""\n\n')

        # 创建包元数据
        package_metadata = {
            "name": package_name,
            "version": "1.0.0",
            "skills": skill_ids,
            "created_at": datetime.now().isoformat(),
        }

        metadata_file = package_dir / "package.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(package_metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"Skill包已生成: {package_dir}")
        return package_dir