"""
质量验证模块

提供数据集质量检查和验证功能：
- 数据完整性验证
- 数据一致性验证
- 数据有效性验证
- 数据分布分析
- 异常检测
"""

import hashlib
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.schema import (
    DataQuality,
    DatasetSchema,
    DatasetRecord,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationLevel(str):
    """验证级别"""

    ERROR = "error"  # 错误 - 必须修复
    WARNING = "warning"  # 警告 - 建议修复
    INFO = "info"  # 信息 - 仅提示


class ValidationError(BaseModel):
    """验证错误"""

    level: str = Field(..., description="错误级别")
    field: str = Field(..., description="字段名")
    message: str = Field(..., description="错误消息")
    value: Optional[Any] = Field(default=None, description="错误值")
    record_id: Optional[str] = Field(default=None, description="记录ID")
    rule_name: str = Field(default="", description="规则名称")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ValidationReport(BaseModel):
    """验证报告"""

    dataset_name: str = Field(..., description="数据集名称")
    total_records: int = Field(default=0, description="总记录数")
    valid_records: int = Field(default=0, description="有效记录数")
    invalid_records: int = Field(default=0, description="无效记录数")
    error_count: int = Field(default=0, description="错误数")
    warning_count: int = Field(default=0, description="警告数")
    info_count: int = Field(default=0, description="信息数")
    errors: List[ValidationError] = Field(default_factory=list, description="错误列表")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="统计信息")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="质量评分")
    quality_level: DataQuality = Field(default=DataQuality.RAW, description="质量等级")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class BaseValidator(ABC):
    """验证器基类"""

    def __init__(self, name: str, level: str = ValidationLevel.ERROR):
        """
        初始化验证器

        Args:
            name: 验证器名称
            level: 验证级别
        """
        self.name = name
        self.level = level

    @abstractmethod
    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """
        验证数据

        Args:
            data: 要验证的数据

        Returns:
            验证错误列表
        """
        pass


class SchemaValidator(BaseValidator):
    """模式验证器"""

    def __init__(self, schema: DatasetSchema, name: str = "schema_validator"):
        """
        初始化模式验证器

        Args:
            schema: 数据集模式
            name: 验证器名称
        """
        super().__init__(name, ValidationLevel.ERROR)
        self.schema = schema

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """验证数据是否符合模式"""
        errors = []

        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, pd.DataFrame):
            records = data.to_dict("records")
        else:
            records = data

        for i, record in enumerate(records):
            record_id = record.get("id", f"record_{i}")
            is_valid, field_errors = self.schema.validate_record(record)

            for error_msg in field_errors:
                errors.append(ValidationError(
                    level=self.level,
                    field=error_msg.split("'")[1] if "'" in error_msg else "unknown",
                    message=error_msg,
                    value=record.get(error_msg.split("'")[1] if "'" in error_msg else "unknown"),
                    record_id=record_id,
                    rule_name=self.name,
                ))

        return errors


class CompletenessValidator(BaseValidator):
    """完整性验证器"""

    def __init__(
        self,
        required_fields: List[str],
        name: str = "completeness_validator",
        allow_partial: bool = False,
        min_completion_rate: float = 0.9,
    ):
        """
        初始化完整性验证器

        Args:
            required_fields: 必需字段列表
            name: 验证器名称
            allow_partial: 是否允许部分缺失
            min_completion_rate: 最小完成率
        """
        super().__init__(name, ValidationLevel.ERROR)
        self.required_fields = required_fields
        self.allow_partial = allow_partial
        self.min_completion_rate = min_completion_rate

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """验证数据完整性"""
        errors = []

        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, pd.DataFrame):
            records = data.to_dict("records")
        else:
            records = data

        for i, record in enumerate(records):
            record_id = record.get("id", f"record_{i}")
            missing_fields = []

            for field in self.required_fields:
                if field not in record or record[field] is None or record[field] == "":
                    missing_fields.append(field)

            if missing_fields and not self.allow_partial:
                errors.append(ValidationError(
                    level=self.level,
                    field="all",
                    message=f"缺失必需字段: {missing_fields}",
                    value=None,
                    record_id=record_id,
                    rule_name=self.name,
                ))

        # 检查整体完成率
        if isinstance(data, pd.DataFrame):
            completion_rates = {}
            for field in self.required_fields:
                if field in data.columns:
                    completion_rate = data[field].notna().sum() / len(data)
                    completion_rates[field] = completion_rate

                    if completion_rate < self.min_completion_rate:
                        errors.append(ValidationError(
                            level=ValidationLevel.WARNING,
                            field=field,
                            message=f"字段 '{field}' 完成率 {completion_rate:.2%} 低于阈值 {self.min_completion_rate:.2%}",
                            value=completion_rate,
                            rule_name=self.name,
                        ))

        return errors


class ConsistencyValidator(BaseValidator):
    """一致性验证器"""

    def __init__(
        self,
        consistency_rules: Optional[Dict[str, Callable]] = None,
        name: str = "consistency_validator",
    ):
        """
        初始化一致性验证器

        Args:
            consistency_rules: 一致性规则字典
            name: 验证器名称
        """
        super().__init__(name, ValidationLevel.WARNING)
        self.consistency_rules = consistency_rules or {}

    def add_rule(self, rule_name: str, rule_func: Callable[[Dict], bool]) -> None:
        """
        添加一致性规则

        Args:
            rule_name: 规则名称
            rule_func: 规则函数，返回True表示一致
        """
        self.consistency_rules[rule_name] = rule_func

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """验证数据一致性"""
        errors = []

        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, pd.DataFrame):
            records = data.to_dict("records")
        else:
            records = data

        for i, record in enumerate(records):
            record_id = record.get("id", f"record_{i}")

            for rule_name, rule_func in self.consistency_rules.items():
                try:
                    if not rule_func(record):
                        errors.append(ValidationError(
                            level=self.level,
                            field="consistency",
                            message=f"违反一致性规则 '{rule_name}'",
                            record_id=record_id,
                            rule_name=rule_name,
                        ))
                except Exception as e:
                    errors.append(ValidationError(
                        level=ValidationLevel.ERROR,
                        field="consistency",
                        message=f"一致性规则 '{rule_name}' 执行失败: {e}",
                        record_id=record_id,
                        rule_name=rule_name,
                    ))

        return errors


class RangeValidator(BaseValidator):
    """范围验证器"""

    def __init__(
        self,
        field_ranges: Dict[str, Tuple[Optional[float], Optional[float]]],
        name: str = "range_validator",
    ):
        """
        初始化范围验证器

        Args:
            field_ranges: 字段范围字典，键为字段名，值为(min, max)
            name: 验证器名称
        """
        super().__init__(name, ValidationLevel.ERROR)
        self.field_ranges = field_ranges

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """验证数值范围"""
        errors = []

        if isinstance(data, pd.DataFrame):
            for field, (min_val, max_val) in self.field_ranges.items():
                if field in data.columns:
                    if min_val is not None:
                        out_of_range = data[field] < min_val
                        for idx in data[out_of_range].index:
                            errors.append(ValidationError(
                                level=self.level,
                                field=field,
                                message=f"值 {data.loc[idx, field]} 小于最小值 {min_val}",
                                value=data.loc[idx, field],
                                record_id=str(idx),
                                rule_name=self.name,
                            ))

                    if max_val is not None:
                        out_of_range = data[field] > max_val
                        for idx in data[out_of_range].index:
                            errors.append(ValidationError(
                                level=self.level,
                                field=field,
                                message=f"值 {data.loc[idx, field]} 大于最大值 {max_val}",
                                value=data.loc[idx, field],
                                record_id=str(idx),
                                rule_name=self.name,
                            ))
        else:
            if isinstance(data, dict):
                records = [data]
            else:
                records = data

            for i, record in enumerate(records):
                record_id = record.get("id", f"record_{i}")

                for field, (min_val, max_val) in self.field_ranges.items():
                    value = record.get(field)
                    if value is not None and isinstance(value, (int, float)):
                        if min_val is not None and value < min_val:
                            errors.append(ValidationError(
                                level=self.level,
                                field=field,
                                message=f"值 {value} 小于最小值 {min_val}",
                                value=value,
                                record_id=record_id,
                                rule_name=self.name,
                            ))
                        if max_val is not None and value > max_val:
                            errors.append(ValidationError(
                                level=self.level,
                                field=field,
                                message=f"值 {value} 大于最大值 {max_val}",
                                value=value,
                                record_id=record_id,
                                rule_name=self.name,
                            ))

        return errors


class PatternValidator(BaseValidator):
    """模式验证器"""

    def __init__(
        self,
        field_patterns: Dict[str, str],
        name: str = "pattern_validator",
    ):
        """
        初始化模式验证器

        Args:
            field_patterns: 字段模式字典，键为字段名，值为正则表达式
            name: 验证器名称
        """
        super().__init__(name, ValidationLevel.WARNING)
        self.field_patterns = field_patterns

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """验证字符串模式"""
        errors = []

        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, pd.DataFrame):
            records = data.to_dict("records")
        else:
            records = data

        for i, record in enumerate(records):
            record_id = record.get("id", f"record_{i}")

            for field, pattern in self.field_patterns.items():
                value = record.get(field)
                if value is not None and isinstance(value, str):
                    if not re.match(pattern, value):
                        errors.append(ValidationError(
                            level=self.level,
                            field=field,
                            message=f"值 '{value}' 不匹配模式 '{pattern}'",
                            value=value,
                            record_id=record_id,
                            rule_name=self.name,
                        ))

        return errors


class UniquenessValidator(BaseValidator):
    """唯一性验证器"""

    def __init__(
        self,
        unique_fields: List[str],
        name: str = "uniqueness_validator",
    ):
        """
        初始化唯一性验证器

        Args:
            unique_fields: 应该唯一的字段列表
            name: 验证器名称
        """
        super().__init__(name, ValidationLevel.ERROR)
        self.unique_fields = unique_fields

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """验证数据唯一性"""
        errors = []

        if isinstance(data, pd.DataFrame):
            for field in self.unique_fields:
                if field in data.columns:
                    duplicates = data[field].value_counts()
                    duplicates = duplicates[duplicates > 1]

                    for value, count in duplicates.items():
                        errors.append(ValidationError(
                            level=self.level,
                            field=field,
                            message=f"值 '{value}' 重复出现 {count} 次",
                            value=value,
                            rule_name=self.name,
                        ))
        else:
            if isinstance(data, dict):
                records = [data]
            else:
                records = data

            for field in self.unique_fields:
                seen_values = {}
                for i, record in enumerate(records):
                    record_id = record.get("id", f"record_{i}")
                    value = record.get(field)

                    if value is not None:
                        if value in seen_values:
                            errors.append(ValidationError(
                                level=self.level,
                                field=field,
                                message=f"值 '{value}' 与记录 '{seen_values[value]}' 重复",
                                value=value,
                                record_id=record_id,
                                rule_name=self.name,
                            ))
                        seen_values[value] = record_id

        return errors


class OutlierValidator(BaseValidator):
    """异常值验证器"""

    def __init__(
        self,
        outlier_fields: List[str],
        name: str = "outlier_validator",
        method: str = "iqr",
        threshold: float = 3.0,
    ):
        """
        初始化异常值验证器

        Args:
            outlier_fields: 要检查的字段列表
            name: 验证器名称
            method: 检测方法 ('iqr', 'zscore', 'mad')
            threshold: 阈值
        """
        super().__init__(name, ValidationLevel.WARNING)
        self.outlier_fields = outlier_fields
        self.method = method
        self.threshold = threshold

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """检测异常值"""
        errors = []

        if isinstance(data, pd.DataFrame):
            for field in self.outlier_fields:
                if field in data.columns:
                    outliers = self._detect_outliers(data[field])

                    for idx in outliers.index:
                        errors.append(ValidationError(
                            level=self.level,
                            field=field,
                            message=f"检测到异常值: {data.loc[idx, field]}",
                            value=data.loc[idx, field],
                            record_id=str(idx),
                            rule_name=self.name,
                        ))
        else:
            if isinstance(data, dict):
                records = [data]
            else:
                records = data

            # 转换为DataFrame进行检测
            df = pd.DataFrame(records)
            for field in self.outlier_fields:
                if field in df.columns:
                    outliers = self._detect_outliers(df[field])

                    for idx in outliers.index:
                        errors.append(ValidationError(
                            level=self.level,
                            field=field,
                            message=f"检测到异常值: {df.loc[idx, field]}",
                            value=df.loc[idx, field],
                            record_id=str(idx),
                            rule_name=self.name,
                        ))

        return errors

    def _detect_outliers(self, series: pd.Series) -> pd.Series:
        """检测异常值"""
        if self.method == "iqr":
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - self.threshold * IQR
            upper_bound = Q3 + self.threshold * IQR
            return series[(series < lower_bound) | (series > upper_bound)]

        elif self.method == "zscore":
            mean = series.mean()
            std = series.std()
            if std == 0:
                return pd.Series([], dtype=series.dtype)
            z_scores = (series - mean) / std
            return series[abs(z_scores) > self.threshold]

        elif self.method == "mad":
            median = series.median()
            mad = np.median(np.abs(series - median))
            if mad == 0:
                return pd.Series([], dtype=series.dtype)
            modified_z_scores = 0.6745 * (series - median) / mad
            return series[abs(modified_z_scores) > self.threshold]

        return pd.Series([], dtype=series.dtype)


class DistributionValidator(BaseValidator):
    """分布验证器"""

    def __init__(
        self,
        distribution_rules: Optional[Dict[str, Dict[str, Any]]] = None,
        name: str = "distribution_validator",
    ):
        """
        初始化分布验证器

        Args:
            distribution_rules: 分布规则字典
            name: 验证器名称
        """
        super().__init__(name, ValidationLevel.INFO)
        self.distribution_rules = distribution_rules or {}

    def validate(self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]) -> List[ValidationError]:
        """验证数据分布"""
        errors = []

        if isinstance(data, pd.DataFrame):
            df = data
        else:
            if isinstance(data, dict):
                records = [data]
            else:
                records = data
            df = pd.DataFrame(records)

        for field, rule in self.distribution_rules.items():
            if field in df.columns:
                distribution_errors = self._check_distribution(df[field], rule)
                errors.extend(distribution_errors)

        return errors

    def _check_distribution(self, series: pd.Series, rule: Dict[str, Any]) -> List[ValidationError]:
        """检查分布"""
        errors = []

        # 检查类别分布
        if "expected_classes" in rule:
            actual_classes = set(series.dropna().unique())
            expected_classes = set(rule["expected_classes"])

            missing = expected_classes - actual_classes
            if missing:
                errors.append(ValidationError(
                    level=self.level,
                    field=series.name,
                    message=f"缺少预期类别: {missing}",
                    rule_name="expected_classes",
                ))

            extra = actual_classes - expected_classes
            if extra:
                errors.append(ValidationError(
                    level=self.level,
                    field=series.name,
                    message=f"存在额外类别: {extra}",
                    rule_name="expected_classes",
                ))

        # 检查类别比例
        if "min_class_ratio" in rule:
            value_counts = series.value_counts(normalize=True)
            min_ratio = rule["min_class_ratio"]

            for value, ratio in value_counts.items():
                if ratio < min_ratio:
                    errors.append(ValidationError(
                        level=ValidationLevel.WARNING,
                        field=series.name,
                        message=f"类别 '{value}' 比例 {ratio:.2%} 低于最小阈值 {min_ratio:.2%}",
                        value=value,
                        rule_name="min_class_ratio",
                    ))

        # 检查分布类型
        if "distribution_type" in rule:
            expected_type = rule["distribution_type"]
            # 这里可以添加分布类型检测逻辑
            # 例如使用统计检验来验证是否为正态分布等

        return errors


class QualityValidator:
    """质量验证系统"""

    def __init__(self, schema: Optional[DatasetSchema] = None):
        """
        初始化质量验证系统

        Args:
            schema: 数据集模式
        """
        self.schema = schema
        self.validators: Dict[str, BaseValidator] = {}
        self._setup_default_validators()

    def _setup_default_validators(self) -> None:
        """设置默认验证器"""
        if self.schema:
            # 添加模式验证器
            self.register_validator(SchemaValidator(self.schema))

            # 添加完整性验证器
            required_fields = [f.name for f in self.schema.fields if not f.nullable]
            if required_fields:
                self.register_validator(CompletenessValidator(required_fields))

            # 添加范围验证器
            field_ranges = {}
            for field in self.schema.fields:
                if field.min_value is not None or field.max_value is not None:
                    field_ranges[field.name] = (field.min_value, field.max_value)
            if field_ranges:
                self.register_validator(RangeValidator(field_ranges))

            # 添加模式验证器
            field_patterns = {}
            for field in self.schema.fields:
                if field.pattern is not None:
                    field_patterns[field.name] = field.pattern
            if field_patterns:
                self.register_validator(PatternValidator(field_patterns))

    def register_validator(self, validator: BaseValidator) -> None:
        """
        注册验证器

        Args:
            validator: 验证器实例
        """
        self.validators[validator.name] = validator
        logger.info(f"注册验证器: {validator.name}")

    def get_validator(self, name: str) -> Optional[BaseValidator]:
        """
        获取验证器

        Args:
            name: 验证器名称

        Returns:
            验证器实例
        """
        return self.validators.get(name)

    def validate(
        self,
        data: Union[Dict[str, Any], pd.DataFrame, List[Dict], List[DatasetRecord]],
        validators: Optional[List[str]] = None,
    ) -> ValidationReport:
        """
        执行验证

        Args:
            data: 要验证的数据
            validators: 要使用的验证器列表

        Returns:
            验证报告
        """
        # 转换数据格式
        if isinstance(data, list) and data and isinstance(data[0], DatasetRecord):
            records = [r.model_dump() for r in data]
            data = pd.DataFrame(records)

        dataset_name = self.schema.name if self.schema else "unknown"

        # 确定要使用的验证器
        validator_list = validators or list(self.validators.keys())

        # 执行所有验证
        all_errors = []
        for validator_name in validator_list:
            validator = self.validators.get(validator_name)
            if validator:
                try:
                    errors = validator.validate(data)
                    all_errors.extend(errors)
                except Exception as e:
                    logger.error(f"验证器 '{validator_name}' 执行失败: {e}")
                    all_errors.append(ValidationError(
                        level=ValidationLevel.ERROR,
                        field="validator",
                        message=f"验证器 '{validator_name}' 执行失败: {e}",
                        rule_name=validator_name,
                    ))

        # 统计结果
        if isinstance(data, pd.DataFrame):
            total_records = len(data)
        elif isinstance(data, list):
            total_records = len(data)
        else:
            total_records = 1

        error_count = len([e for e in all_errors if e.level == ValidationLevel.ERROR])
        warning_count = len([e for e in all_errors if e.level == ValidationLevel.WARNING])
        info_count = len([e for e in all_errors if e.level == ValidationLevel.INFO])

        invalid_records = len(set(e.record_id for e in all_errors if e.record_id))
        valid_records = total_records - invalid_records

        # 计算质量评分
        quality_score = self._calculate_quality_score(
            total_records, valid_records, error_count, warning_count
        )

        # 确定质量等级
        quality_level = self._determine_quality_level(quality_score)

        # 收集统计信息
        statistics = self._collect_statistics(data)

        return ValidationReport(
            dataset_name=dataset_name,
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=invalid_records,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            errors=all_errors,
            statistics=statistics,
            quality_score=quality_score,
            quality_level=quality_level,
        )

    def _calculate_quality_score(
        self,
        total_records: int,
        valid_records: int,
        error_count: int,
        warning_count: int,
    ) -> float:
        """计算质量评分"""
        if total_records == 0:
            return 0.0

        # 基础评分：有效记录比例
        base_score = valid_records / total_records

        # 错误扣分
        error_penalty = min(error_count / total_records * 0.5, 0.3)

        # 警告扣分
        warning_penalty = min(warning_count / total_records * 0.2, 0.1)

        quality_score = base_score - error_penalty - warning_penalty
        return max(0.0, min(1.0, quality_score))

    def _determine_quality_level(self, quality_score: float) -> DataQuality:
        """确定质量等级"""
        if quality_score >= 0.9:
            return DataQuality.HIGH
        elif quality_score >= 0.7:
            return DataQuality.MEDIUM
        elif quality_score >= 0.5:
            return DataQuality.LOW
        else:
            return DataQuality.RAW

    def _collect_statistics(
        self, data: Union[Dict[str, Any], pd.DataFrame, List[Dict]]
    ) -> Dict[str, Any]:
        """收集统计信息"""
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])

        stats = {
            "record_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "missing_values": {},
            "data_types": {},
        }

        # 缺失值统计
        for col in df.columns:
            missing = df[col].isna().sum()
            stats["missing_values"][col] = {
                "count": missing,
                "ratio": missing / len(df) if len(df) > 0 else 0,
            }

        # 数据类型统计
        for col in df.columns:
            stats["data_types"][col] = str(df[col].dtype)

        return stats

    def generate_report(
        self,
        data: Union[Dict[str, Any], pd.DataFrame, List[Dict]],
        output_path: Union[str, Path],
        format: str = "json",
    ) -> None:
        """
        生成验证报告

        Args:
            data: 要验证的数据
            output_path: 输出路径
            format: 报告格式
        """
        report = self.validate(data)
        output_path = Path(output_path)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        elif format == "csv":
            error_records = []
            for error in report.errors:
                error_records.append({
                    "level": error.level,
                    "field": error.field,
                    "message": error.message,
                    "value": error.value,
                    "record_id": error.record_id,
                    "rule_name": error.rule_name,
                    "timestamp": error.timestamp,
                })
            df = pd.DataFrame(error_records)
            df.to_csv(output_path, index=False, encoding="utf-8")
        elif format == "html":
            html_content = self._generate_html_report(report)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        logger.info(f"验证报告已保存到: {output_path}")

    def _generate_html_report(self, report: ValidationReport) -> str:
        """生成HTML报告"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>数据质量验证报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .error {{ color: red; }}
        .warning {{ color: orange; }}
        .info {{ color: blue; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>数据质量验证报告</h1>
    <div class="summary">
        <p><strong>数据集名称:</strong> {report.dataset_name}</p>
        <p><strong>总记录数:</strong> {report.total_records}</p>
        <p><strong>有效记录数:</strong> {report.valid_records}</p>
        <p><strong>无效记录数:</strong> {report.invalid_records}</p>
        <p><strong>质量评分:</strong> {report.quality_score:.2%}</p>
        <p><strong>质量等级:</strong> {report.quality_level}</p>
        <p><strong>错误数:</strong> {report.error_count}</p>
        <p><strong>警告数:</strong> {report.warning_count}</p>
        <p><strong>信息数:</strong> {report.info_count}</p>
    </div>
    <h2>验证错误列表</h2>
    <table>
        <tr>
            <th>级别</th>
            <th>字段</th>
            <th>消息</th>
            <th>值</th>
            <th>记录ID</th>
            <th>规则</th>
        </tr>
"""
        for error in report.errors:
            level_class = error.level
            html += f"""
        <tr class="{level_class}">
            <td>{error.level}</td>
            <td>{error.field}</td>
            <td>{error.message}</td>
            <td>{error.value}</td>
            <td>{error.record_id}</td>
            <td>{error.rule_name}</td>
        </tr>
"""
        html += """
    </table>
</body>
</html>
"""
        return html

    def filter_valid_records(
        self,
        data: Union[pd.DataFrame, List[Dict], List[DatasetRecord]],
        min_quality: DataQuality = DataQuality.MEDIUM,
    ) -> Union[pd.DataFrame, List[Dict], List[DatasetRecord]]:
        """
        过滤有效记录

        Args:
            data: 数据
            min_quality: 最小质量等级

        Returns:
            过滤后的数据
        """
        report = self.validate(data)

        if isinstance(data, pd.DataFrame):
            # 找出有错误的记录ID
            invalid_ids = set(e.record_id for e in report.errors if e.level == ValidationLevel.ERROR)

            if invalid_ids:
                # 根据索引过滤
                valid_indices = [i for i in range(len(data)) if str(i) not in invalid_ids]
                return data.iloc[valid_indices]
            return data

        elif isinstance(data, list):
            if data and isinstance(data[0], DatasetRecord):
                invalid_ids = set(e.record_id for e in report.errors if e.level == ValidationLevel.ERROR)
                return [r for r in data if r.id not in invalid_ids]
            else:
                invalid_ids = set(e.record_id for e in report.errors if e.level == ValidationLevel.ERROR)
                return [r for i, r in enumerate(data) if f"record_{i}" not in invalid_ids]

        return data


class DataCleaner:
    """数据清洗器"""

    def __init__(self, validator: Optional[QualityValidator] = None):
        """
        初始化数据清洗器

        Args:
            validator: 质量验证器
        """
        self.validator = validator

    def clean(
        self,
        data: pd.DataFrame,
        strategies: Optional[Dict[str, str]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        清洗数据

        Args:
            data: 数据框
            strategies: 清洗策略字典，键为字段名，值为策略名称

        Returns:
            (清洗后的数据框, 清洗统计)
        """
        if strategies is None:
            strategies = {}

        stats = {
            "original_count": len(data),
            "cleaned_count": 0,
            "removed_count": 0,
            "filled_count": 0,
            "transformed_count": 0,
            "operations": [],
        }

        cleaned_data = data.copy()

        # 应用清洗策略
        for field, strategy in strategies.items():
            if field not in cleaned_data.columns:
                continue

            if strategy == "drop_na":
                before = len(cleaned_data)
                cleaned_data = cleaned_data.dropna(subset=[field])
                stats["removed_count"] += before - len(cleaned_data)
                stats["operations"].append(f"字段 '{field}': 删除了 {before - len(cleaned_data)} 条缺失值记录")

            elif strategy == "fill_mean":
                if cleaned_data[field].dtype in [np.float64, np.int64]:
                    mean_value = cleaned_data[field].mean()
                    filled = cleaned_data[field].isna().sum()
                    cleaned_data[field] = cleaned_data[field].fillna(mean_value)
                    stats["filled_count"] += filled
                    stats["operations"].append(f"字段 '{field}': 用均值 {mean_value} 填充了 {filled} 个缺失值")

            elif strategy == "fill_median":
                if cleaned_data[field].dtype in [np.float64, np.int64]:
                    median_value = cleaned_data[field].median()
                    filled = cleaned_data[field].isna().sum()
                    cleaned_data[field] = cleaned_data[field].fillna(median_value)
                    stats["filled_count"] += filled
                    stats["operations"].append(f"字段 '{field}': 用中位数 {median_value} 填充了 {filled} 个缺失值")

            elif strategy == "fill_mode":
                mode_value = cleaned_data[field].mode().iloc[0] if len(cleaned_data[field].mode()) > 0 else None
                if mode_value is not None:
                    filled = cleaned_data[field].isna().sum()
                    cleaned_data[field] = cleaned_data[field].fillna(mode_value)
                    stats["filled_count"] += filled
                    stats["operations"].append(f"字段 '{field}': 用众数 '{mode_value}' 填充了 {filled} 个缺失值")

            elif strategy == "fill_constant":
                constant = strategies.get(f"{field}_constant", "")
                filled = cleaned_data[field].isna().sum()
                cleaned_data[field] = cleaned_data[field].fillna(constant)
                stats["filled_count"] += filled
                stats["operations"].append(f"字段 '{field}': 用常量 '{constant}' 填充了 {filled} 个缺失值")

            elif strategy == "remove_duplicates":
                before = len(cleaned_data)
                cleaned_data = cleaned_data.drop_duplicates(subset=[field])
                stats["removed_count"] += before - len(cleaned_data)
                stats["operations"].append(f"字段 '{field}': 删除了 {before - len(cleaned_data)} 条重复记录")

            elif strategy == "trim":
                if cleaned_data[field].dtype == object:
                    cleaned_data[field] = cleaned_data[field].str.strip()
                    stats["transformed_count"] += cleaned_data[field].notna().sum()
                    stats["operations"].append(f"字段 '{field}': 去除了前后空格")

        stats["cleaned_count"] = len(cleaned_data)

        logger.info(f"数据清洗完成: {stats['original_count']} -> {stats['cleaned_count']}")

        return cleaned_data, stats

    def remove_outliers(
        self,
        data: pd.DataFrame,
        fields: Optional[List[str]] = None,
        method: str = "iqr",
        threshold: float = 1.5,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        移除异常值

        Args:
            data: 数据框
            fields: 要处理的字段列表
            method: 检测方法
            threshold: 阈值

        Returns:
            (处理后的数据框, 处理统计)
        """
        if fields is None:
            fields = data.select_dtypes(include=[np.number]).columns.tolist()

        stats = {
            "original_count": len(data),
            "removed_count": 0,
            "fields_processed": {},
        }

        cleaned_data = data.copy()

        for field in fields:
            if field not in cleaned_data.columns:
                continue

            # 检测异常值
            series = cleaned_data[field]

            if method == "iqr":
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outliers_mask = (series < lower_bound) | (series > upper_bound)
            elif method == "zscore":
                mean = series.mean()
                std = series.std()
                if std == 0:
                    continue
                z_scores = (series - mean) / std
                outliers_mask = abs(z_scores) > threshold
            else:
                continue

            outliers_count = outliers_mask.sum()
            stats["fields_processed"][field] = outliers_count

            # 移除异常值记录
            cleaned_data = cleaned_data[~outliers_mask]

        stats["removed_count"] = stats["original_count"] - len(cleaned_data)

        return cleaned_data, stats