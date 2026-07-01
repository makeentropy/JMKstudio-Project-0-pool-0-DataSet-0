"""
两仪生成引擎（LiangYi Generator）

太极生两仪，两仪生四象。
本模块实现 dataset（阴）与 skill（阳）的双向生成、迭代优化机制。

两仪理念：
- 阳仪（Skill）：主动、功能、操作 → 生成数据集的规则和模式
- 阴仪（Dataset）：被动、数据、载体 → 孕育技能的素材和基础
- 阴阳互根：Skill 生成 Dataset，Dataset 优化 Skill
- 阴阳转化：数据积累到临界点触发技能升维，技能成熟后催生新数据
"""

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.schema import DatasetSchema, FieldSchema, LabelSchema, DataType, DatasetType
from ai_llm_agent_crawler.dataset.skill_engine import (
    GeneratedSkill,
    SkillEngine,
    SkillGenerationConfig,
    SkillMetadata,
    SkillType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class LiangYiMode(str, Enum):
    """两仪生成模式"""

    YANG_TO_YIN = "yang_to_yin"
    YIN_TO_YANG = "yin_to_yang"
    MUTUAL_GENERATION = "mutual_generation"
    CIRCULAR_ITERATION = "circular_iteration"


class LiangYiStatus(str, Enum):
    """两仪生成状态"""

    IDLE = "idle"
    GENERATING_YANG = "generating_yang"
    GENERATING_YIN = "generating_yin"
    VALIDATING = "validating"
    ITERATING = "iterating"
    COMPLETED = "completed"
    FAILED = "failed"


class YinYangPair(BaseModel):
    """阴阳对（Dataset-Skill 对）"""

    pair_id: str = Field(default_factory=lambda: f"liangyi_{uuid.uuid4().hex[:8]}")
    name: str
    dataset_id: str = ""
    skill_id: str = ""
    dataset_version: str = "1.0.0"
    skill_version: str = "1.0.0"
    iteration: int = 0
    quality_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class GenerationResult(BaseModel):
    """两仪生成结果"""

    success: bool
    mode: str
    pair: Optional[YinYangPair] = None
    dataset_result: Optional[Any] = None
    skill_result: Optional[GeneratedSkill] = None
    iterations: int = 0
    quality_score: float = 0.0
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class LiangYiConfig(BaseModel):
    """两仪生成配置"""

    max_iterations: int = 10
    quality_threshold: float = 0.8
    min_dataset_size: int = 100
    dataset_growth_rate: float = 1.5
    skill_optimization_rate: float = 0.1
    auto_iterate: bool = True
    validate_after_generation: bool = True
    output_dir: Path = Path("output/liangyi")
    mode: str = LiangYiMode.MUTUAL_GENERATION

    class Config:
        arbitrary_types_allowed = True


class YangGenerator:
    """
    阳仪生成器（Skill → Dataset）

    从 Skill 生成 Dataset，通过技能规则和逻辑生成训练数据。
    """

    def __init__(self, skill_engine: Optional[SkillEngine] = None):
        """
        初始化阳仪生成器

        Args:
            skill_engine: 技能引擎
        """
        self.skill_engine = skill_engine or SkillEngine()
        self.logger = get_logger(f"{__name__}.YangGenerator")

    def generate_from_skill(
        self,
        skill: GeneratedSkill,
        dataset_size: int = 100,
        dataset_name: Optional[str] = None,
    ) -> Tuple[Optional[pd.DataFrame], Optional[DatasetSchema]]:
        """
        从 Skill 生成数据集

        Args:
            skill: 源 Skill
            dataset_size: 数据集大小
            dataset_name: 数据集名称

        Returns:
            (数据集 DataFrame, 数据集模式)
        """
        skill_meta = skill.metadata
        name = dataset_name or f"{skill_meta.name}_dataset"

        self.logger.info(f"阳仪生成: 从 Skill '{skill_meta.name}' 生成数据集 '{name}'")

        try:
            schema = self._derive_schema_from_skill(skill, name)
            dataset = self._generate_dataset_from_schema(schema, dataset_size, skill)

            self.logger.info(f"阳仪生成完成: {len(dataset)} 条记录")
            return dataset, schema

        except Exception as e:
            self.logger.error(f"阳仪生成失败: {e}", exc_info=True)
            return None, None

    def _derive_schema_from_skill(
        self,
        skill: GeneratedSkill,
        dataset_name: str,
    ) -> DatasetSchema:
        """从 Skill 派生数据集模式"""
        config = skill.config
        fields = []

        if "fields" in config:
            for field_name in config["fields"]:
                fields.append(FieldSchema(
                    name=field_name,
                    data_type="str",
                    description=f"Field generated from skill field: {field_name}",
                    nullable=True,
                ))
        else:
            fields.extend([
                FieldSchema(name="input", data_type="str", description="输入数据"),
                FieldSchema(name="output", data_type="str", description="输出数据"),
                FieldSchema(name="confidence", data_type="float", description="置信度"),
            ])

        labels = []
        if "labels" in config:
            for label_name in config["labels"]:
                labels.append(LabelSchema(
                    name=label_name,
                    label_type="classification",
                    description=f"Label from skill: {label_name}",
                ))

        schema = DatasetSchema(
            name=dataset_name,
            description=f"Dataset generated from skill: {skill.metadata.name}",
            version="1.0.0",
            dataset_type=DatasetType.TRAINING,
            data_type=DataType.TABULAR,
            fields=fields,
            labels=labels,
        )

        return schema

    def _generate_dataset_from_schema(
        self,
        schema: DatasetSchema,
        size: int,
        skill: GeneratedSkill,
    ) -> pd.DataFrame:
        """根据模式生成数据集"""
        data = []

        for i in range(size):
            record = {}
            for field in schema.fields:
                record[field.name] = self._generate_field_value(field, i, skill)
            data.append(record)

        df = pd.DataFrame(data)
        return df

    def _generate_field_value(
        self,
        field: FieldSchema,
        index: int,
        skill: GeneratedSkill,
    ) -> Any:
        """生成字段值"""
        data_type = str(field.data_type).lower()
        if data_type in ["str", "string", "text"]:
            return f"{field.name}_value_{index}"
        elif data_type in ["int", "integer"]:
            return index
        elif data_type in ["float", "double", "number"]:
            return round(index * 1.0 / 100, 2)
        elif data_type in ["bool", "boolean"]:
            return index % 2 == 0
        else:
            return None


class YinGenerator:
    """
    阴仪生成器（Dataset → Skill）

    从 Dataset 生成 Skill，基于数据模式和分布生成处理技能。
    """

    def __init__(self, skill_engine: Optional[SkillEngine] = None):
        """
        初始化阴仪生成器

        Args:
            skill_engine: 技能引擎
        """
        self.skill_engine = skill_engine or SkillEngine()
        self.logger = get_logger(f"{__name__}.YinGenerator")

    def generate_from_dataset(
        self,
        dataset: pd.DataFrame,
        schema: DatasetSchema,
        skill_type: str = SkillType.PROCESSOR,
        skill_name: Optional[str] = None,
    ) -> Optional[GeneratedSkill]:
        """
        从数据集生成 Skill

        Args:
            dataset: 源数据集
            schema: 数据集模式
            skill_type: Skill 类型
            skill_name: Skill 名称

        Returns:
            生成的 Skill
        """
        name = skill_name or f"{schema.name}_skill"

        self.logger.info(f"阴仪生成: 从 Dataset '{schema.name}' 生成 Skill '{name}'")

        try:
            skill = self.skill_engine.generate_from_schema(
                schema=schema,
                skill_type=skill_type,
            )

            self._enhance_skill_from_data(skill, dataset, schema)

            self.logger.info(f"阴仪生成完成: {skill.metadata.id}")
            return skill

        except Exception as e:
            self.logger.error(f"阴仪生成失败: {e}", exc_info=True)
            return None

    def _enhance_skill_from_data(
        self,
        skill: GeneratedSkill,
        dataset: pd.DataFrame,
        schema: DatasetSchema,
    ) -> None:
        """根据数据特征增强 Skill"""
        stats = {}
        for col in dataset.columns:
            if pd.api.types.is_numeric_dtype(dataset[col]):
                stats[col] = {
                    "mean": float(dataset[col].mean()),
                    "std": float(dataset[col].std()),
                    "min": float(dataset[col].min()),
                    "max": float(dataset[col].max()),
                }
            elif pd.api.types.is_string_dtype(dataset[col]):
                stats[col] = {
                    "unique_count": int(dataset[col].nunique()),
                    "sample_values": dataset[col].unique()[:5].tolist(),
                }

        skill.metadata.tags = list(skill.metadata.tags) + ["data_enhanced"]
        skill.config["data_statistics"] = stats
        skill.config["dataset_size"] = len(dataset)


class QualityAssessor:
    """
    质量评估器

    评估生成的数据集和技能的质量，决定是否继续迭代。
    """

    def __init__(self):
        """初始化质量评估器"""
        self.logger = get_logger(f"{__name__}.QualityAssessor")

    def assess_pair_quality(
        self,
        dataset: pd.DataFrame,
        skill: GeneratedSkill,
        schema: DatasetSchema,
    ) -> float:
        """
        评估阴阳对质量

        Args:
            dataset: 数据集
            skill: 技能
            schema: 模式

        Returns:
            质量分数 (0.0 - 1.0)
        """
        scores = []

        dataset_score = self._assess_dataset_quality(dataset, schema)
        scores.append(dataset_score)

        skill_score = self._assess_skill_quality(skill)
        scores.append(skill_score)

        consistency_score = self._assess_consistency(dataset, skill, schema)
        scores.append(consistency_score)

        overall_score = sum(scores) / len(scores) if scores else 0.0
        self.logger.info(f"质量评估: 数据集={dataset_score:.2f}, 技能={skill_score:.2f}, 一致性={consistency_score:.2f}, 综合={overall_score:.2f}")

        return overall_score

    def _assess_dataset_quality(
        self,
        dataset: pd.DataFrame,
        schema: DatasetSchema,
    ) -> float:
        """评估数据集质量"""
        if len(dataset) == 0:
            return 0.0

        score = 0.0

        size_score = min(len(dataset) / 1000.0, 1.0) * 0.3
        score += size_score

        completeness = 0.0
        if len(dataset.columns) > 0:
            completeness = 1.0 - (dataset.isnull().sum().sum() / (len(dataset) * len(dataset.columns)))
        score += completeness * 0.4

        schema_fields = [f.name for f in schema.fields]
        dataset_fields = list(dataset.columns)
        field_match = len(set(schema_fields) & set(dataset_fields)) / max(len(schema_fields), 1)
        score += field_match * 0.3

        return min(score, 1.0)

    def _assess_skill_quality(self, skill: GeneratedSkill) -> float:
        """评估技能质量"""
        score = 0.0

        if skill.code and len(skill.code) > 100:
            score += 0.3

        if skill.config:
            score += 0.2

        if skill.test_cases and len(skill.test_cases) > 0:
            score += 0.2

        if skill.documentation and len(skill.documentation) > 50:
            score += 0.2

        if skill.metadata.accuracy > 0:
            score += 0.1

        return min(score, 1.0)

    def _assess_consistency(
        self,
        dataset: pd.DataFrame,
        skill: GeneratedSkill,
        schema: DatasetSchema,
    ) -> float:
        """评估数据与技能的一致性"""
        score = 0.5

        skill_fields = skill.config.get("fields", [])
        dataset_fields = list(dataset.columns)
        if skill_fields:
            match_ratio = len(set(skill_fields) & set(dataset_fields)) / max(len(skill_fields), 1)
            score += match_ratio * 0.5

        return min(score, 1.0)


class LiangYiEngine:
    """
    两仪生成引擎

    实现 dataset（阴）与 skill（阳）的双向生成和迭代优化。
    """

    def __init__(
        self,
        config: Optional[LiangYiConfig] = None,
        skill_engine: Optional[SkillEngine] = None,
    ):
        """
        初始化两仪引擎

        Args:
            config: 两仪配置
            skill_engine: 技能引擎
        """
        self.config = config or LiangYiConfig()
        self.skill_engine = skill_engine or SkillEngine()

        self.yang_generator = YangGenerator(self.skill_engine)
        self.yin_generator = YinGenerator(self.skill_engine)
        self.quality_assessor = QualityAssessor()

        self._pairs: Dict[str, YinYangPair] = {}
        self._datasets: Dict[str, Tuple[pd.DataFrame, DatasetSchema]] = {}
        self._skills: Dict[str, GeneratedSkill] = {}

        self._status: LiangYiStatus = LiangYiStatus.IDLE
        self.logger = get_logger(f"{__name__}.LiangYiEngine")

        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def status(self) -> LiangYiStatus:
        """当前状态"""
        return self._status

    def generate_yang_from_yin(
        self,
        dataset: pd.DataFrame,
        schema: DatasetSchema,
        skill_type: str = SkillType.PROCESSOR,
        pair_name: Optional[str] = None,
    ) -> GenerationResult:
        """
        阴生阳：从数据集生成 Skill

        Args:
            dataset: 源数据集
            schema: 数据集模式
            skill_type: Skill 类型
            pair_name: 阴阳对名称

        Returns:
            生成结果
        """
        start_time = datetime.now()
        self._status = LiangYiStatus.GENERATING_YANG

        name = pair_name or f"liangyi_{schema.name}"
        self.logger.info(f"两仪-阴生阳: {name}")

        try:
            skill = self.yin_generator.generate_from_dataset(
                dataset=dataset,
                schema=schema,
                skill_type=skill_type,
            )

            if not skill:
                return GenerationResult(
                    success=False,
                    mode=LiangYiMode.YIN_TO_YANG,
                    error_message="Failed to generate skill from dataset",
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                )

            pair = YinYangPair(
                name=name,
                dataset_id=schema.name,
                skill_id=skill.metadata.id,
                dataset_version=schema.version,
                skill_version=skill.metadata.version,
                iteration=1,
            )

            self._pairs[pair.pair_id] = pair
            self._datasets[schema.name] = (dataset, schema)
            self._skills[skill.metadata.id] = skill

            quality_score = 0.0
            if self.config.validate_after_generation:
                self._status = LiangYiStatus.VALIDATING
                quality_score = self.quality_assessor.assess_pair_quality(
                    dataset, skill, schema
                )
                pair.quality_score = quality_score

            self._status = LiangYiStatus.COMPLETED

            result = GenerationResult(
                success=True,
                mode=LiangYiMode.YIN_TO_YANG,
                pair=pair,
                dataset_result=dataset,
                skill_result=skill,
                iterations=1,
                quality_score=quality_score,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

            self.logger.info(f"两仪-阴生阳完成: {pair.pair_id}, 质量={quality_score:.2f}")
            return result

        except Exception as e:
            self._status = LiangYiStatus.FAILED
            self.logger.error(f"两仪-阴生阳失败: {e}", exc_info=True)
            return GenerationResult(
                success=False,
                mode=LiangYiMode.YIN_TO_YANG,
                error_message=str(e),
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def generate_yin_from_yang(
        self,
        skill: GeneratedSkill,
        dataset_size: int = 100,
        pair_name: Optional[str] = None,
    ) -> GenerationResult:
        """
        阳生阴：从 Skill 生成数据集

        Args:
            skill: 源 Skill
            dataset_size: 数据集大小
            pair_name: 阴阳对名称

        Returns:
            生成结果
        """
        start_time = datetime.now()
        self._status = LiangYiStatus.GENERATING_YIN

        name = pair_name or f"liangyi_{skill.metadata.name}"
        self.logger.info(f"两仪-阳生阴: {name}")

        try:
            dataset, schema = self.yang_generator.generate_from_skill(
                skill=skill,
                dataset_size=dataset_size,
            )

            if dataset is None or schema is None:
                return GenerationResult(
                    success=False,
                    mode=LiangYiMode.YANG_TO_YIN,
                    error_message="Failed to generate dataset from skill",
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                )

            pair = YinYangPair(
                name=name,
                dataset_id=schema.name,
                skill_id=skill.metadata.id,
                dataset_version=schema.version,
                skill_version=skill.metadata.version,
                iteration=1,
            )

            self._pairs[pair.pair_id] = pair
            self._datasets[schema.name] = (dataset, schema)
            self._skills[skill.metadata.id] = skill

            quality_score = 0.0
            if self.config.validate_after_generation:
                self._status = LiangYiStatus.VALIDATING
                quality_score = self.quality_assessor.assess_pair_quality(
                    dataset, skill, schema
                )
                pair.quality_score = quality_score

            self._status = LiangYiStatus.COMPLETED

            result = GenerationResult(
                success=True,
                mode=LiangYiMode.YANG_TO_YIN,
                pair=pair,
                dataset_result=dataset,
                skill_result=skill,
                iterations=1,
                quality_score=quality_score,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

            self.logger.info(f"两仪-阳生阴完成: {pair.pair_id}, 质量={quality_score:.2f}")
            return result

        except Exception as e:
            self._status = LiangYiStatus.FAILED
            self.logger.error(f"两仪-阳生阴失败: {e}", exc_info=True)
            return GenerationResult(
                success=False,
                mode=LiangYiMode.YANG_TO_YIN,
                error_message=str(e),
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def mutual_generation(
        self,
        initial_dataset: Optional[pd.DataFrame] = None,
        initial_schema: Optional[DatasetSchema] = None,
        initial_skill: Optional[GeneratedSkill] = None,
        pair_name: str = "liangyi_pair",
    ) -> GenerationResult:
        """
        两仪互生：双向迭代生成

        从初始的数据集或技能开始，进行双向迭代优化。

        Args:
            initial_dataset: 初始数据集
            initial_schema: 初始数据集模式
            initial_skill: 初始 Skill
            pair_name: 阴阳对名称

        Returns:
            生成结果
        """
        start_time = datetime.now()
        self._status = LiangYiStatus.ITERATING

        self.logger.info(f"两仪-互生: {pair_name}, 最大迭代={self.config.max_iterations}")

        current_dataset = initial_dataset
        current_schema = initial_schema
        current_skill = initial_skill
        iteration = 0
        best_quality = 0.0
        best_pair = None

        try:
            if current_dataset is None and current_skill is None:
                return GenerationResult(
                    success=False,
                    mode=LiangYiMode.MUTUAL_GENERATION,
                    error_message="Either initial_dataset or initial_skill must be provided",
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                )

            for i in range(self.config.max_iterations):
                iteration = i + 1
                self.logger.info(f"两仪迭代第 {iteration} 轮")

                if current_dataset is not None and current_schema is not None:
                    current_skill = self.yin_generator.generate_from_dataset(
                        dataset=current_dataset,
                        schema=current_schema,
                    )
                    if current_skill is None:
                        break

                if current_skill is not None:
                    new_size = int(self.config.min_dataset_size * (self.config.dataset_growth_rate ** i))
                    current_dataset, current_schema = self.yang_generator.generate_from_skill(
                        skill=current_skill,
                        dataset_size=new_size,
                        dataset_name=f"{pair_name}_dataset_v{iteration}",
                    )
                    if current_dataset is None or current_schema is None:
                        break

                if self.config.validate_after_generation and current_dataset and current_schema and current_skill:
                    quality = self.quality_assessor.assess_pair_quality(
                        current_dataset, current_skill, current_schema
                    )

                    if quality > best_quality:
                        best_quality = quality
                        best_pair = YinYangPair(
                            name=pair_name,
                            dataset_id=current_schema.name,
                            skill_id=current_skill.metadata.id,
                            dataset_version=current_schema.version,
                            skill_version=current_skill.metadata.version,
                            iteration=iteration,
                            quality_score=quality,
                        )

                    self.logger.info(f"迭代 {iteration}: 质量={quality:.2f}, 最佳={best_quality:.2f}")

                    if quality >= self.config.quality_threshold and self.config.auto_iterate:
                        self.logger.info(f"达到质量阈值 {self.config.quality_threshold}，提前结束")
                        break

            if best_pair:
                self._pairs[best_pair.pair_id] = best_pair
                if current_schema:
                    self._datasets[current_schema.name] = (current_dataset, current_schema)
                if current_skill:
                    self._skills[current_skill.metadata.id] = current_skill

            self._status = LiangYiStatus.COMPLETED

            result = GenerationResult(
                success=best_pair is not None,
                mode=LiangYiMode.MUTUAL_GENERATION,
                pair=best_pair,
                dataset_result=current_dataset,
                skill_result=current_skill,
                iterations=iteration,
                quality_score=best_quality,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

            self.logger.info(f"两仪-互生完成: {iteration} 轮迭代, 最佳质量={best_quality:.2f}")
            return result

        except Exception as e:
            self._status = LiangYiStatus.FAILED
            self.logger.error(f"两仪-互生失败: {e}", exc_info=True)
            return GenerationResult(
                success=False,
                mode=LiangYiMode.MUTUAL_GENERATION,
                error_message=str(e),
                iterations=iteration,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def get_pair(self, pair_id: str) -> Optional[YinYangPair]:
        """获取阴阳对"""
        return self._pairs.get(pair_id)

    def list_pairs(self) -> List[YinYangPair]:
        """列出所有阴阳对"""
        return list(self._pairs.values())

    def get_dataset(self, dataset_id: str) -> Optional[Tuple[pd.DataFrame, DatasetSchema]]:
        """获取数据集"""
        return self._datasets.get(dataset_id)

    def get_skill(self, skill_id: str) -> Optional[GeneratedSkill]:
        """获取技能"""
        return self._skills.get(skill_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取两仪引擎统计"""
        return {
            "status": self._status.value,
            "total_pairs": len(self._pairs),
            "total_datasets": len(self._datasets),
            "total_skills": len(self._skills),
            "config": {
                "max_iterations": self.config.max_iterations,
                "quality_threshold": self.config.quality_threshold,
                "mode": self.config.mode,
            },
        }

    def export_pair(self, pair_id: str, output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        导出阴阳对到文件

        Args:
            pair_id: 阴阳对 ID
            output_dir: 输出目录

        Returns:
            输出目录路径
        """
        pair = self._pairs.get(pair_id)
        if not pair:
            return None

        output_dir = output_dir or self.config.output_dir / pair_id
        output_dir.mkdir(parents=True, exist_ok=True)

        if pair.dataset_id in self._datasets:
            dataset, schema = self._datasets[pair.dataset_id]
            dataset_path = output_dir / f"{pair.dataset_id}.parquet"
            dataset.to_parquet(dataset_path)
            self.logger.info(f"数据集已导出: {dataset_path}")

        if pair.skill_id in self._skills:
            skill = self._skills[pair.skill_id]
            self.skill_engine.export_skill(skill.metadata.id, output_dir / "skill")
            self.logger.info(f"技能已导出: {output_dir / 'skill'}")

        pair_file = output_dir / "pair_info.json"
        with open(pair_file, "w", encoding="utf-8") as f:
            json.dump(pair.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

        return output_dir
