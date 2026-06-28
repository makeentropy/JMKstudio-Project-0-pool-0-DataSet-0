"""
自动标注模块

提供多种标注方法：
- 规则标注：基于预定义规则进行标注
- 模型标注：使用预训练模型进行标注
- 半自动标注：结合人工和自动标注
- 启发式标注：基于特征进行标注
"""

import hashlib
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.schema import (
    AnnotationMethod,
    DataQuality,
    DatasetRecord,
    DatasetSchema,
    LabelSchema,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AnnotationResult(BaseModel):
    """标注结果"""

    label_name: str = Field(..., description="标签名称")
    value: Any = Field(..., description="标签值")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    method: AnnotationMethod = Field(default=AnnotationMethod.MANUAL, description="标注方法")
    annotator: str = Field(default="system", description="标注者")
    timestamp: datetime = Field(default_factory=datetime.now, description="标注时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AnnotationBatch(BaseModel):
    """标注批次"""

    batch_id: str = Field(..., description="批次ID")
    records: List[DatasetRecord] = Field(default_factory=list, description="记录列表")
    results: Dict[str, List[AnnotationResult]] = Field(
        default_factory=dict, description="标注结果"
    )
    status: str = Field(default="pending", description="状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")


class BaseAnnotator(ABC):
    """标注器基类"""

    def __init__(self, name: str, method: AnnotationMethod):
        """
        初始化标注器

        Args:
            name: 标注器名称
            method: 标注方法
        """
        self.name = name
        self.method = method
        self._initialized = False

    @abstractmethod
    def annotate(self, record: DatasetRecord, label_schema: LabelSchema) -> AnnotationResult:
        """
        标注单条记录

        Args:
            record: 要标注的记录
            label_schema: 标签模式

        Returns:
            标注结果
        """
        pass

    @abstractmethod
    def batch_annotate(
        self, records: List[DatasetRecord], label_schema: LabelSchema
    ) -> List[AnnotationResult]:
        """
        批量标注记录

        Args:
            records: 要标注的记录列表
            label_schema: 标签模式

        Returns:
            标注结果列表
        """
        pass

    def initialize(self) -> None:
        """初始化标注器（加载模型、配置等）"""
        self._initialized = True
        logger.info(f"标注器 '{self.name}' 已初始化")

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


class RuleBasedAnnotator(BaseAnnotator):
    """规则标注器"""

    def __init__(
        self,
        name: str = "rule_based",
        rules: Optional[Dict[str, Callable]] = None,
    ):
        """
        初始化规则标注器

        Args:
            name: 标注器名称
            rules: 规则字典，键为标签名，值为规则函数
        """
        super().__init__(name, AnnotationMethod.RULE_BASED)
        self.rules = rules or {}

    def add_rule(self, label_name: str, rule_func: Callable) -> None:
        """
        添加标注规则

        Args:
            label_name: 标签名称
            rule_func: 规则函数，接收记录数据，返回标签值和置信度
        """
        self.rules[label_name] = rule_func
        logger.info(f"为标签 '{label_name}' 添加了规则")

    def annotate(self, record: DatasetRecord, label_schema: LabelSchema) -> AnnotationResult:
        """标注单条记录"""
        rule_func = self.rules.get(label_schema.name)

        if rule_func is None:
            logger.warning(f"未找到标签 '{label_schema.name}' 的规则")
            return AnnotationResult(
                label_name=label_schema.name,
                value=None,
                confidence=0.0,
                method=self.method,
                annotator=self.name,
            )

        try:
            result = rule_func(record.data)
            if isinstance(result, tuple):
                value, confidence = result
            else:
                value = result
                confidence = 1.0

            return AnnotationResult(
                label_name=label_schema.name,
                value=value,
                confidence=confidence,
                method=self.method,
                annotator=self.name,
            )
        except Exception as e:
            logger.error(f"规则标注失败: {e}")
            return AnnotationResult(
                label_name=label_schema.name,
                value=None,
                confidence=0.0,
                method=self.method,
                annotator=self.name,
                metadata={"error": str(e)},
            )

    def batch_annotate(
        self, records: List[DatasetRecord], label_schema: LabelSchema
    ) -> List[AnnotationResult]:
        """批量标注记录"""
        return [self.annotate(record, label_schema) for record in records]


class PatternRuleAnnotator(RuleBasedAnnotator):
    """模式规则标注器"""

    def __init__(
        self,
        name: str = "pattern_rule",
        patterns: Optional[Dict[str, List[Tuple[str, Any, float]]]] = None,
    ):
        """
        初始化模式规则标注器

        Args:
            name: 标注器名称
            patterns: 模式字典，键为标签名，值为(模式,标签值,置信度)列表
        """
        super().__init__(name)
        self.patterns = patterns or {}
        self._build_rules()

    def _build_rules(self) -> None:
        """构建规则函数"""
        for label_name, pattern_list in self.patterns.items():
            self.add_rule(label_name, self._create_pattern_rule(pattern_list))

    def _create_pattern_rule(
        self, pattern_list: List[Tuple[str, Any, float]]
    ) -> Callable[[Dict], Tuple[Any, float]]:
        """
        创建模式规则函数

        Args:
            pattern_list: 模式列表，每个元素为(正则模式,标签值,置信度)

        Returns:
            规则函数
        """

        def rule_func(data: Dict) -> Tuple[Any, float]:
            # 搜索所有字段中的文本
            for field_name, field_value in data.items():
                if isinstance(field_value, str):
                    for pattern, label_value, confidence in pattern_list:
                        if re.search(pattern, field_value):
                            return label_value, confidence
            return None, 0.0

        return rule_func

    def add_pattern(
        self, label_name: str, pattern: str, label_value: Any, confidence: float = 1.0
    ) -> None:
        """
        添加标注模式

        Args:
            label_name: 标签名称
            pattern: 正则表达式模式
            label_value: 匹配后的标签值
            confidence: 置信度
        """
        if label_name not in self.patterns:
            self.patterns[label_name] = []
        self.patterns[label_name].append((pattern, label_value, confidence))
        self._build_rules()


class KeywordRuleAnnotator(RuleBasedAnnotator):
    """关键词规则标注器"""

    def __init__(
        self,
        name: str = "keyword_rule",
        keywords: Optional[Dict[str, Dict[str, Tuple[Any, float]]]] = None,
    ):
        """
        初始化关键词规则标注器

        Args:
            name: 标注器名称
            keywords: 关键词字典，键为标签名，值为{关键词:(标签值,置信度)}字典
        """
        super().__init__(name)
        self.keywords = keywords or {}
        self._build_rules()

    def _build_rules(self) -> None:
        """构建规则函数"""
        for label_name, keyword_map in self.keywords.items():
            self.add_rule(label_name, self._create_keyword_rule(keyword_map))

    def _create_keyword_rule(
        self, keyword_map: Dict[str, Tuple[Any, float]]
    ) -> Callable[[Dict], Tuple[Any, float]]:
        """
        创建关键词规则函数

        Args:
            keyword_map: 关键词映射，键为关键词，值为(标签值,置信度)

        Returns:
            规则函数
        """

        def rule_func(data: Dict) -> Tuple[Any, float]:
            best_match = None
            best_confidence = 0.0

            for field_name, field_value in data.items():
                if isinstance(field_value, str):
                    for keyword, (label_value, confidence) in keyword_map.items():
                        if keyword.lower() in field_value.lower():
                            if confidence > best_confidence:
                                best_match = label_value
                                best_confidence = confidence

            return best_match, best_confidence

        return rule_func

    def add_keyword(
        self, label_name: str, keyword: str, label_value: Any, confidence: float = 1.0
    ) -> None:
        """
        添加标注关键词

        Args:
            label_name: 标签名称
            keyword: 关键词
            label_value: 匹配后的标签值
            confidence: 置信度
        """
        if label_name not in self.keywords:
            self.keywords[label_name] = {}
        self.keywords[label_name][keyword] = (label_value, confidence)
        self._build_rules()


class ModelBasedAnnotator(BaseAnnotator):
    """模型标注器"""

    def __init__(
        self,
        name: str = "model_based",
        model_path: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化模型标注器

        Args:
            name: 标注器名称
            model_path: 模型路径
            model_config: 模型配置
        """
        super().__init__(name, AnnotationMethod.MODEL_BASED)
        self.model_path = model_path
        self.model_config = model_config or {}
        self.model = None

    def initialize(self) -> None:
        """初始化模型"""
        # 这里可以加载预训练模型
        # 实际实现取决于具体使用的模型框架
        if self.model_path:
            logger.info(f"正在加载模型: {self.model_path}")
            # 示例：加载模型的逻辑
            # self.model = load_model(self.model_path, **self.model_config)
        self._initialized = True

    def annotate(self, record: DatasetRecord, label_schema: LabelSchema) -> AnnotationResult:
        """标注单条记录"""
        if not self.is_initialized():
            self.initialize()

        # 如果有实际模型，使用模型进行预测
        if self.model is not None:
            try:
                # 示例预测逻辑
                # prediction, confidence = self.model.predict(record.data)
                prediction = None
                confidence = 0.0
            except Exception as e:
                logger.error(f"模型标注失败: {e}")
                prediction = None
                confidence = 0.0
        else:
            # 模拟标注（用于测试）
            prediction = self._mock_predict(record.data, label_schema)
            confidence = 0.7

        return AnnotationResult(
            label_name=label_schema.name,
            value=prediction,
            confidence=confidence,
            method=self.method,
            annotator=self.name,
        )

    def _mock_predict(self, data: Dict, label_schema: LabelSchema) -> Any:
        """模拟预测（测试用）"""
        if label_schema.classes and len(label_schema.classes) > 0:
            # 返回第一个类别作为模拟预测
            return label_schema.classes[0]
        return "mock_label"

    def batch_annotate(
        self, records: List[DatasetRecord], label_schema: LabelSchema
    ) -> List[AnnotationResult]:
        """批量标注记录"""
        if not self.is_initialized():
            self.initialize()

        # 模型批量预测
        results = []
        for record in records:
            results.append(self.annotate(record, label_schema))
        return results


class HeuristicAnnotator(BaseAnnotator):
    """启发式标注器"""

    def __init__(
        self,
        name: str = "heuristic",
        heuristics: Optional[Dict[str, List[Callable]]] = None,
    ):
        """
        初始化启发式标注器

        Args:
            name: 标注器名称
            heuristics: 启发式规则字典，键为标签名，值为规则函数列表
        """
        super().__init__(name, AnnotationMethod.SEMI_AUTO)
        self.heuristics = heuristics or {}

    def add_heuristic(
        self, label_name: str, heuristic_func: Callable[[Dict], Tuple[Any, float]]
    ) -> None:
        """
        添加启发式规则

        Args:
            label_name: 标签名称
            heuristic_func: 启发式规则函数
        """
        if label_name not in self.heuristics:
            self.heuristics[label_name] = []
        self.heuristics[label_name].append(heuristic_func)

    def annotate(self, record: DatasetRecord, label_schema: LabelSchema) -> AnnotationResult:
        """标注单条记录"""
        heuristic_funcs = self.heuristics.get(label_schema.name, [])

        if not heuristic_funcs:
            return AnnotationResult(
                label_name=label_schema.name,
                value=None,
                confidence=0.0,
                method=self.method,
                annotator=self.name,
            )

        # 使用投票机制
        votes: Dict[Any, List[float]] = {}
        for func in heuristic_funcs:
            try:
                value, confidence = func(record.data)
                if value is not None:
                    if value not in votes:
                        votes[value] = []
                    votes[value].append(confidence)
            except Exception as e:
                logger.warning(f"启发式规则执行失败: {e}")

        if not votes:
            return AnnotationResult(
                label_name=label_schema.name,
                value=None,
                confidence=0.0,
                method=self.method,
                annotator=self.name,
            )

        # 计算加权投票结果
        best_value = None
        best_score = 0.0
        for value, confidences in votes.items():
            avg_confidence = sum(confidences) / len(confidences)
            weighted_score = avg_confidence * len(confidences)
            if weighted_score > best_score:
                best_value = value
                best_score = weighted_score

        final_confidence = best_score / len(heuristic_funcs) if heuristic_funcs else 0.0

        return AnnotationResult(
            label_name=label_schema.name,
            value=best_value,
            confidence=final_confidence,
            method=self.method,
            annotator=self.name,
        )

    def batch_annotate(
        self, records: List[DatasetRecord], label_schema: LabelSchema
    ) -> List[AnnotationResult]:
        """批量标注记录"""
        return [self.annotate(record, label_schema) for record in records]


class AutoAnnotator:
    """自动标注系统"""

    def __init__(self, schema: Optional[DatasetSchema] = None):
        """
        初始化自动标注系统

        Args:
            schema: 数据集模式
        """
        self.schema = schema
        self.annotators: Dict[str, BaseAnnotator] = {}
        self.annotation_history: List[AnnotationBatch] = []

    def register_annotator(self, annotator: BaseAnnotator) -> None:
        """
        注册标注器

        Args:
            annotator: 标注器实例
        """
        self.annotators[annotator.name] = annotator
        logger.info(f"注册标注器: {annotator.name}")

    def get_annotator(self, name: str) -> Optional[BaseAnnotator]:
        """
        获取标注器

        Args:
            name: 标注器名称

        Returns:
            标注器实例
        """
        return self.annotators.get(name)

    def select_annotator(self, label_schema: LabelSchema) -> BaseAnnotator:
        """
        根据标签模式选择合适的标注器

        Args:
            label_schema: 标签模式

        Returns:
            选择的标注器
        """
        method = label_schema.annotation_method

        # 根据标注方法选择标注器
        for annotator in self.annotators.values():
            if annotator.method == method:
                return annotator

        # 默认使用第一个可用的标注器
        if self.annotators:
            return next(iter(self.annotators.values()))

        # 如果没有注册标注器，返回规则标注器
        return RuleBasedAnnotator()

    def annotate_record(
        self,
        record: DatasetRecord,
        label_schemas: Optional[List[LabelSchema]] = None,
    ) -> Dict[str, AnnotationResult]:
        """
        标注单条记录

        Args:
            record: 要标注的记录
            label_schemas: 标签模式列表

        Returns:
            标注结果字典
        """
        if label_schemas is None:
            label_schemas = self.schema.labels if self.schema else []

        results = {}
        for label_schema in label_schemas:
            annotator = self.select_annotator(label_schema)
            result = annotator.annotate(record, label_schema)
            results[label_schema.name] = result

        return results

    def annotate_batch(
        self,
        records: List[DatasetRecord],
        label_schemas: Optional[List[LabelSchema]] = None,
        batch_id: Optional[str] = None,
    ) -> AnnotationBatch:
        """
        批量标注记录

        Args:
            records: 要标注的记录列表
            label_schemas: 标签模式列表
            batch_id: 批次ID

        Returns:
            标注批次
        """
        if batch_id is None:
            batch_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]

        batch = AnnotationBatch(batch_id=batch_id, records=records, status="processing")

        if label_schemas is None:
            label_schemas = self.schema.labels if self.schema else []

        all_results: Dict[str, List[AnnotationResult]] = {}
        for label_schema in label_schemas:
            annotator = self.select_annotator(label_schema)
            results = annotator.batch_annotate(records, label_schema)
            all_results[label_schema.name] = results

        batch.results = all_results
        batch.status = "completed"
        batch.completed_at = datetime.now()

        self.annotation_history.append(batch)
        logger.info(f"批次 {batch_id} 标注完成")

        return batch

    def apply_annotations(
        self,
        records: List[DatasetRecord],
        threshold: float = 0.8,
    ) -> List[DatasetRecord]:
        """
        将标注结果应用到记录

        Args:
            records: 要标注的记录列表
            threshold: 置信度阈值

        Returns:
            标注后的记录列表
        """
        annotated_records = []

        for record in records:
            annotation_results = self.annotate_record(record)

            # 应用高置信度标注
            new_labels = {}
            for label_name, result in annotation_results.items():
                if result.confidence >= threshold:
                    new_labels[label_name] = result.value

            record.labels = new_labels
            record.updated_at = datetime.now()

            # 更新质量等级
            if len(new_labels) == len(annotation_results):
                record.quality = DataQuality.HIGH
            elif len(new_labels) > 0:
                record.quality = DataQuality.MEDIUM
            else:
                record.quality = DataQuality.LOW

            annotated_records.append(record)

        return annotated_records

    def export_annotations(
        self,
        output_path: Union[str, Path],
        format: str = "json",
    ) -> None:
        """
        导出标注历史

        Args:
            output_path: 输出路径
            format: 导出格式
        """
        output_path = Path(output_path)

        if format == "json":
            data = [batch.model_dump() for batch in self.annotation_history]
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        elif format == "csv":
            records = []
            for batch in self.annotation_history:
                for label_name, results in batch.results.items():
                    for i, result in enumerate(results):
                        records.append({
                            "batch_id": batch.batch_id,
                            "record_id": batch.records[i].id if i < len(batch.records) else None,
                            "label_name": label_name,
                            "value": result.value,
                            "confidence": result.confidence,
                            "method": result.method,
                            "annotator": result.annotator,
                            "timestamp": result.timestamp,
                        })
            df = pd.DataFrame(records)
            df.to_csv(output_path, index=False, encoding="utf-8")

        logger.info(f"标注历史已导出到: {output_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取标注统计信息

        Returns:
            统计信息字典
        """
        total_batches = len(self.annotation_history)
        total_records = sum(len(batch.records) for batch in self.annotation_history)
        total_annotations = sum(
            sum(len(results) for results in batch.results.values())
            for batch in self.annotation_history
        )

        # 计算平均置信度
        confidences = []
        for batch in self.annotation_history:
            for results in batch.results.values():
                for result in results:
                    confidences.append(result.confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_batches": total_batches,
            "total_records": total_records,
            "total_annotations": total_annotations,
            "avg_confidence": avg_confidence,
            "annotators": list(self.annotators.keys()),
        }


class AnnotationRuleBuilder:
    """标注规则构建器"""

    def __init__(self):
        """初始化规则构建器"""
        self.rules: Dict[str, Callable] = {}

    def build_classification_rule(
        self,
        field_name: str,
        class_mapping: Dict[str, str],
        default_class: Optional[str] = None,
    ) -> Callable[[Dict], Tuple[str, float]]:
        """
        构建分类规则

        Args:
            field_name: 字段名
            class_mapping: 类别映射，键为字段值，值为标签类别
            default_class: 默认类别

        Returns:
            规则函数
        """

        def rule(data: Dict) -> Tuple[str, float]:
            value = data.get(field_name)
            if value in class_mapping:
                return class_mapping[value], 1.0
            if default_class:
                return default_class, 0.5
            return None, 0.0

        return rule

    def build_range_rule(
        self,
        field_name: str,
        ranges: List[Tuple[float, float, Any, float]],
        default_value: Optional[Any] = None,
    ) -> Callable[[Dict], Tuple[Any, float]]:
        """
        构建范围规则

        Args:
            field_name: 字段名
            ranges: 范围列表，每个元素为(最小值,最大值,标签值,置信度)
            default_value: 默认值

        Returns:
            规则函数
        """

        def rule(data: Dict) -> Tuple[Any, float]:
            value = data.get(field_name)
            if isinstance(value, (int, float)):
                for min_val, max_val, label_val, confidence in ranges:
                    if min_val <= value <= max_val:
                        return label_val, confidence
            if default_value:
                return default_value, 0.5
            return None, 0.0

        return rule

    def build_regex_rule(
        self,
        field_name: str,
        regex_patterns: List[Tuple[str, Any, float]],
        default_value: Optional[Any] = None,
    ) -> Callable[[Dict], Tuple[Any, float]]:
        """
        构建正则表达式规则

        Args:
            field_name: 字段名
            regex_patterns: 正则模式列表，每个元素为(模式,标签值,置信度)
            default_value: 默认值

        Returns:
            规则函数
        """

        def rule(data: Dict) -> Tuple[Any, float]:
            value = data.get(field_name)
            if isinstance(value, str):
                for pattern, label_val, confidence in regex_patterns:
                    if re.search(pattern, value):
                        return label_val, confidence
            if default_value:
                return default_value, 0.5
            return None, 0.0

        return rule

    def build_combined_rule(
        self,
        rules: List[Callable[[Dict], Tuple[Any, float]]],
        aggregation: str = "vote",
    ) -> Callable[[Dict], Tuple[Any, float]]:
        """
        构建组合规则

        Args:
            rules: 规则列表
            aggregation: 聚合方式 ('vote', 'max', 'avg')

        Returns:
            组合规则函数
        """

        def rule(data: Dict) -> Tuple[Any, float]:
            results = []
            for r in rules:
                try:
                    value, confidence = r(data)
                    if value is not None:
                        results.append((value, confidence))
                except Exception:
                    pass

            if not results:
                return None, 0.0

            if aggregation == "vote":
                votes: Dict[Any, List[float]] = {}
                for value, confidence in results:
                    if value not in votes:
                        votes[value] = []
                    votes[value].append(confidence)

                best_value = max(votes.keys(), key=lambda k: sum(votes[k]) / len(votes[k]))
                avg_confidence = sum(votes[best_value]) / len(votes[best_value])
                return best_value, avg_confidence

            elif aggregation == "max":
                return max(results, key=lambda x: x[1])

            elif aggregation == "avg":
                total_confidence = sum(c for _, c in results)
                avg_confidence = total_confidence / len(results)
                return results[0][0], avg_confidence

            return results[0]

        return rule