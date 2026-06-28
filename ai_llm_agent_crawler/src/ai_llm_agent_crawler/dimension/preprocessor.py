"""
数据预处理和标准化模块

提供数据清洗、转换、标准化等多种预处理操作，支持大规模数据处理。
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ai_llm_agent_crawler.dimension.models import (
    PreprocessingConfig,
    PreprocessingResult,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FieldTransformRule:
    """字段转换规则"""
    field_name: str
    transform_type: str  # clean, normalize, convert, encode, custom
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 执行优先级


@dataclass
class CleaningRule:
    """清洗规则"""
    rule_name: str
    condition: Callable[[Any], bool]  # 判断是否需要清洗的条件
    action: Callable[[Any], Any]  # 清洗动作
    description: str = ""
    affected_fields: List[str] = field(default_factory=list)


class DataPreprocessor:
    """
    数据预处理器

    提供数据清洗、转换、标准化等多种预处理操作：
    - 数据清洗：缺失值处理、重复值删除、异常值处理
    - 数据转换：类型转换、格式转换、编码转换
    - 数据标准化：归一化、标准化、离散化
    - 自定义处理：支持自定义处理规则
    """

    def __init__(
        self,
        config: Optional[PreprocessingConfig] = None,
        custom_rules: Optional[List[CleaningRule]] = None,
        enable_parallel: bool = True,
        batch_size: int = 10000,
        max_workers: int = 4,
    ):
        """
        初始化数据预处理器

        Args:
            config: 预处理配置
            custom_rules: 自定义清洗规则列表
            enable_parallel: 是否启用并行处理
            batch_size: 批处理大小
            max_workers: 最大并行工作线程数
        """
        self.config = config or PreprocessingConfig()
        self.custom_rules = custom_rules or []
        self.enable_parallel = enable_parallel
        self.batch_size = batch_size
        self.max_workers = max_workers

        # 内置清洗规则
        self._builtin_rules = self._init_builtin_rules()

        logger.info(f"数据预处理器初始化完成，批大小: {batch_size}")

    def process(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        output_format: str = "_dataframe",  # dataframe, list, dict
    ) -> PreprocessingResult:
        """
        执行数据预处理

        Args:
            data: 输入数据（DataFrame或记录列表）
            output_format: 输出格式

        Returns:
            预处理结果
        """
        start_time = time.time()

        # 转换输入为DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        result = PreprocessingResult(
            original_record_count=len(df),
            processed_record_count=len(df),
        )

        try:
            # 执行预处理流程
            df = self._execute_preprocessing(df, result)

            # 设置输出数据
            if output_format == "list":
                result.output_data = df.to_dict('records')
            elif output_format == "dict":
                result.output_data = df.to_dict()
            else:
                result.output_data = df

            result.processed_record_count = len(df)

        except Exception as e:
            result.errors.append(f"预处理失败: {str(e)}")
            logger.error(f"预处理失败: {e}")

        end_time = time.time()
        result.processing_time_ms = (end_time - start_time) * 1000

        logger.info(
            f"数据预处理完成，处理 {result.original_record_count} 条记录，"
            f"耗时 {result.processing_time_ms:.2f}ms"
        )

        return result

    def _execute_preprocessing(
        self,
        df: pd.DataFrame,
        result: PreprocessingResult,
    ) -> pd.DataFrame:
        """执行预处理流程"""

        # 1. 删除重复值
        if self.config.remove_duplicates:
            before = len(df)
            df = self._remove_duplicates(df)
            result.removed_duplicates = before - len(df)
            logger.debug(f"删除了 {result.removed_duplicates} 条重复记录")

        # 2. 处理缺失值
        if self.config.handle_missing_values:
            before = len(df)
            df = self._handle_missing_values(df)
            if self.config.missing_value_strategy == "drop":
                result.handled_missing = before - len(df)
            else:
                result.handled_missing = df.isna().sum().sum()
            logger.debug(f"处理了缺失值")

        # 3. 处理异常值
        if self.config.remove_outliers:
            before = len(df)
            df = self._remove_outliers(df)
            result.removed_outliers = before - len(df)
            logger.debug(f"删除了 {result.removed_outliers} 条异常值记录")

        # 4. 标准化数值
        if self.config.normalize_values:
            df, normalized_fields = self._normalize_values(df)
            result.normalized_fields = normalized_fields
            logger.debug(f"标准化了 {len(normalized_fields)} 个字段")

        # 5. 标准化格式
        if self.config.standardize_formats:
            df = self._standardize_formats(df)
            logger.debug(f"标准化了数据格式")

        # 6. 应用自定义规则
        for rule in self.custom_rules:
            df = self._apply_custom_rule(df, rule)
            logger.debug(f"应用自定义规则: {rule.rule_name}")

        # 7. 应用自定义处理规则
        if self.config.custom_rules:
            df = self._apply_custom_rules(df, self.config.custom_rules)

        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """删除重复值"""
        return df.drop_duplicates()

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        strategy = self.config.missing_value_strategy

        if strategy == "drop":
            return df.dropna()

        elif strategy == "mean":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                df[col] = df[col].fillna(df[col].mean())

        elif strategy == "median":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                df[col] = df[col].fillna(df[col].median())

        elif strategy == "mode":
            for col in df.columns:
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col] = df[col].fillna(mode_val.iloc[0])

        elif strategy == "fill":
            fill_value = self.config.missing_value_fill
            df = df.fillna(fill_value)

        elif strategy == "ffill":
            df = df.fillna(method='ffill')

        elif strategy == "bfill":
            df = df.fillna(method='bfill')

        elif strategy == "interpolate":
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                df[col] = df[col].interpolate()

        return df

    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """删除异常值"""
        method = self.config.outlier_method
        threshold = self.config.outlier_threshold

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if method == "iqr":
            for col in numeric_cols:
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - threshold * iqr
                upper_bound = q3 + threshold * iqr
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]

        elif method == "zscore":
            for col in numeric_cols:
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    z_scores = np.abs((df[col] - mean) / std)
                    df = df[z_scores <= threshold]

        elif method == "isolation":
            # 简化的孤立森林方法
            for col in numeric_cols:
                mean = df[col].mean()
                std = df[col].std()
                median = df[col].median()
                mad = np.median(np.abs(df[col] - median))
                if mad > 0:
                    modified_z_scores = 0.6745 * (df[col] - median) / mad
                    df = df[np.abs(modified_z_scores) <= threshold]

        return df

    def _normalize_values(
        self,
        df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """标准化数值"""
        method = self.config.normalization_method
        normalized_fields = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            non_null_values = df[col].dropna()
            if len(non_null_values) == 0:
                continue

            if method == "minmax":
                min_val = non_null_values.min()
                max_val = non_null_values.max()
                if max_val - min_val > 0:
                    df[col] = (df[col] - min_val) / (max_val - min_val)
                    normalized_fields.append(col)

            elif method == "zscore":
                mean = non_null_values.mean()
                std = non_null_values.std()
                if std > 0:
                    df[col] = (df[col] - mean) / std
                    normalized_fields.append(col)

            elif method == "robust":
                median = non_null_values.median()
                iqr = non_null_values.quantile(0.75) - non_null_values.quantile(0.25)
                if iqr > 0:
                    df[col] = (df[col] - median) / iqr
                    normalized_fields.append(col)

        return df, normalized_fields

    def _standardize_formats(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化格式"""
        encoding = self.config.encoding

        # 标准化字符串格式
        text_cols = df.select_dtypes(include=['object']).columns

        for col in text_cols:
            df[col] = df[col].apply(lambda x: self._standardize_string(x, encoding) if pd.notna(x) else x)

        # 标准化日期格式
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        for col in datetime_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    def _standardize_string(self, value: Any, encoding: str) -> str:
        """标准化字符串"""
        if not isinstance(value, str):
            return str(value)

        try:
            # 去除首尾空白
            value = value.strip()

            # 统一空白字符
            value = re.sub(r'\s+', ' ', value)

            # 统一编码
            if encoding == "utf-8":
                value = value.encode('utf-8', errors='ignore').decode('utf-8')

            # 去除不可见字符
            value = re.sub(r'[^\x20-\x7E\u4e00-\u9fff]', '', value)

            return value

        except Exception:
            return str(value)

    def _apply_custom_rule(
        self,
        df: pd.DataFrame,
        rule: CleaningRule,
    ) -> pd.DataFrame:
        """应用自定义清洗规则"""
        fields = rule.affected_fields or list(df.columns)

        for field in fields:
            if field not in df.columns:
                continue

            df[field] = df[field].apply(
                lambda x: rule.action(x) if rule.condition(x) and pd.notna(x) else x
            )

        return df

    def _apply_custom_rules(
        self,
        df: pd.DataFrame,
        custom_rules: Dict[str, Any],
    ) -> pd.DataFrame:
        """应用配置中的自定义规则"""
        for field_name, rules in custom_rules.items():
            if field_name not in df.columns:
                continue

            for rule_name, rule_params in rules.items():
                if rule_name == "replace":
                    df[field_name] = df[field_name].replace(
                        rule_params.get("pattern", ""),
                        rule_params.get("replacement", "")
                    )
                elif rule_name == "map":
                    mapping = rule_params.get("mapping", {})
                    df[field_name] = df[field_name].map(mapping).fillna(df[field_name])
                elif rule_name == "regex_replace":
                    pattern = rule_params.get("pattern", "")
                    replacement = rule_params.get("replacement", "")
                    df[field_name] = df[field_name].apply(
                        lambda x: re.sub(pattern, replacement, str(x)) if pd.notna(x) else x
                    )
                elif rule_name == "convert_type":
                    target_type = rule_params.get("type", "string")
                    df[field_name] = self._convert_type(df[field_name], target_type)

        return df

    def _convert_type(self, values: pd.Series, target_type: str) -> pd.Series:
        """转换数据类型"""
        try:
            if target_type == "int":
                return pd.to_numeric(values, errors='coerce').astype('Int64')
            elif target_type == "float":
                return pd.to_numeric(values, errors='coerce')
            elif target_type == "string":
                return values.astype(str)
            elif target_type == "datetime":
                return pd.to_datetime(values, errors='coerce')
            elif target_type == "bool":
                return values.astype(bool)
        except Exception:
            return values

        return values

    def _init_builtin_rules(self) -> List[CleaningRule]:
        """初始化内置清洗规则"""
        return [
            CleaningRule(
                rule_name="remove_empty_strings",
                condition=lambda x: isinstance(x, str) and x.strip() == "",
                action=lambda x: None,
                description="移除空字符串",
            ),
            CleaningRule(
                rule_name="trim_whitespace",
                condition=lambda x: isinstance(x, str) and (x.startswith(' ') or x.endswith(' ')),
                action=lambda x: x.strip(),
                description="去除首尾空白",
            ),
            CleaningRule(
                rule_name="normalize_numbers",
                condition=lambda x: isinstance(x, str) and re.match(r'^[\d,\.]+$', x),
                action=lambda x: float(x.replace(',', '')),
                description="标准化数字格式",
            ),
        ]

    def process_batch(
        self,
        data_batches: List[pd.DataFrame],
    ) -> List[PreprocessingResult]:
        """
        批量处理数据

        Args:
            data_batches: 数据批次列表

        Returns:
            预处理结果列表
        """
        if not self.enable_parallel or len(data_batches) < self.max_workers:
            return [self.process(batch) for batch in data_batches]

        results = [None] * len(data_batches)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.process, batch): idx
                for idx, batch in enumerate(data_batches)
            }

            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()

        return results

    def add_cleaning_rule(self, rule: CleaningRule) -> None:
        """
        添加清洗规则

        Args:
            rule: 清洗规则
        """
        self.custom_rules.append(rule)
        logger.info(f"添加清洗规则: {rule.rule_name}")

    def get_processing_stats(self, result: PreprocessingResult) -> Dict[str, Any]:
        """
        获取处理统计信息

        Args:
            result: 预处理结果

        Returns:
            统计信息字典
        """
        stats = {
            "original_count": result.original_record_count,
            "processed_count": result.processed_record_count,
            "reduction_ratio": (
                result.original_record_count - result.processed_record_count
            ) / result.original_record_count if result.original_record_count > 0 else 0,
            "removed_duplicates": result.removed_duplicates,
            "handled_missing": result.handled_missing,
            "removed_outliers": result.removed_outliers,
            "normalized_fields": len(result.normalized_fields),
            "processing_time_ms": result.processing_time_ms,
            "throughput": (
                result.processed_record_count / (result.processing_time_ms / 1000)
                if result.processing_time_ms > 0 else 0
            ),
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
        }

        return stats


class FieldTransformer:
    """
    字段转换器

    提供单个字段的转换和处理功能。
    """

    @staticmethod
    def clean_text(value: Any) -> Any:
        """清洗文本"""
        if pd.isna(value) or not isinstance(value, str):
            return value

        # 去除HTML标签
        value = re.sub(r'<[^>]+>', '', value)

        # 去除特殊字符
        value = re.sub(r'[^\w\s\u4e00-\u9fff\-\.]', '', value)

        # 去除多余空白
        value = re.sub(r'\s+', ' ', value).strip()

        return value

    @staticmethod
    def normalize_url(value: Any) -> Any:
        """标准化URL"""
        if pd.isna(value) or not isinstance(value, str):
            return value

        value = value.strip()

        # 添加协议
        if not value.startswith(('http://', 'https://')):
            value = 'https://' + value

        # 移除尾部斜杠（可选）
        # value = value.rstrip('/')

        return value

    @staticmethod
    def normalize_email(value: Any) -> Any:
        """标准化邮箱"""
        if pd.isna(value) or not isinstance(value, str):
            return value

        value = value.strip().lower()

        # 验证邮箱格式
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
            return None

        return value

    @staticmethod
    def normalize_phone(value: Any) -> Any:
        """标准化电话号码"""
        if pd.isna(value):
            return value

        value = str(value)

        # 提取数字
        digits = re.sub(r'[^\d]', '', value)

        # 中国手机号码
        if len(digits) == 11 and digits.startswith('1'):
            return digits

        # 其他格式保持原样
        return digits if digits else value

    @staticmethod
    def normalize_date(value: Any) -> Any:
        """标准化日期"""
        if pd.isna(value):
            return value

        if isinstance(value, datetime):
            return value

        try:
            return pd.to_datetime(value)
        except Exception:
            return value

    @staticmethod
    def extract_numbers(value: Any) -> List[float]:
        """从文本中提取数字"""
        if pd.isna(value):
            return []

        value = str(value)

        numbers = re.findall(r'[\d,\.]+', value)

        result = []
        for num in numbers:
            try:
                result.append(float(num.replace(',', '')))
            except ValueError:
                continue

        return result

    @staticmethod
    def categorize_value(
        value: Any,
        categories: Dict[str, List[Any]],
        default_category: str = "unknown",
    ) -> str:
        """
        分类值

        Args:
            value: 要分类的值
            categories: 分类映射（类别名称 -> 值列表）
            default_category: 默认类别

        Returns:
            类别名称
        """
        if pd.isna(value):
            return default_category

        for category, values in categories.items():
            if value in values:
                return category

        return default_category

    @staticmethod
    def discretize_numeric(
        value: Any,
        bins: List[float],
        labels: Optional[List[str]] = None,
    ) -> Union[str, float]:
        """
        离散化数值

        Args:
            value: 数值
            bins: 分箱边界
            labels: 分箱标签

        Returns:
            分箱标签或索引
        """
        if pd.isna(value) or not isinstance(value, (int, float)):
            return value

        for i, (lower, upper) in enumerate(zip(bins[:-1], bins[1:])):
            if lower <= value < upper:
                if labels and i < len(labels):
                    return labels[i]
                return i

        if value >= bins[-1]:
            if labels:
                return labels[-1]
            return len(bins) - 1

        return value


class DataValidator:
    """
    数据验证器

    在预处理过程中验证数据有效性。
    """

    @staticmethod
    def validate_field(
        values: pd.Series,
        rules: Dict[str, Any],
    ) -> Tuple[pd.Series, List[str]]:
        """
        验证字段

        Args:
            values: 字段值
            rules: 验证规则

        Returns:
            验证后的值和错误列表
        """
        errors = []

        # 类型验证
        expected_type = rules.get("type")
        if expected_type:
            invalid_mask = ~values.apply(lambda x: DataValidator._check_type(x, expected_type))
            invalid_count = invalid_mask.sum()
            if invalid_count > 0:
                errors.append(f"类型验证失败: {invalid_count} 条记录")

        # 范围验证
        min_val = rules.get("min")
        max_val = rules.get("max")
        if min_val is not None and max_val is not None:
            numeric_values = pd.to_numeric(values, errors='coerce')
            out_of_range = (numeric_values < min_val) | (numeric_values > max_val)
            out_count = out_of_range.sum()
            if out_count > 0:
                errors.append(f"范围验证失败: {out_count} 条记录超出范围 [{min_val}, {max_val}]")

        # 格式验证
        pattern = rules.get("pattern")
        if pattern:
            invalid_mask = ~values.apply(
                lambda x: bool(re.match(pattern, str(x))) if pd.notna(x) else True
            )
            invalid_count = invalid_mask.sum()
            if invalid_count > 0:
                errors.append(f"格式验证失败: {invalid_count} 条记录不符合模式")

        # 必填验证
        if rules.get("required"):
            null_count = values.isna().sum()
            if null_count > 0:
                errors.append(f"必填验证失败: {null_count} 条记录为空")

        # 唯一性验证
        if rules.get("unique"):
            duplicate_count = len(values) - values.nunique()
            if duplicate_count > 0:
                errors.append(f"唯一性验证失败: {duplicate_count} 条重复记录")

        return values, errors

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """检查类型"""
        if pd.isna(value):
            return True

        type_mapping = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "number": (int, float),
            "boolean": bool,
            "list": list,
            "dict": dict,
        }

        expected = type_mapping.get(expected_type.lower())
        if expected is None:
            return True

        return isinstance(value, expected)


class DataPipeline:
    """
    数据处理管道

    组合多个处理步骤，形成完整的处理流程。
    """

    def __init__(
        self,
        steps: Optional[List[Callable[[pd.DataFrame], pd.DataFrame]]] = None,
        preprocessor: Optional[DataPreprocessor] = None,
    ):
        """
        初始化数据管道

        Args:
            steps: 处理步骤列表
            preprocessor: 预处理器实例
        """
        self.steps = steps or []
        self.preprocessor = preprocessor or DataPreprocessor()

        logger.info(f"数据处理管道初始化完成，包含 {len(self.steps)} 个步骤")

    def add_step(
        self,
        step: Callable[[pd.DataFrame], pd.DataFrame],
        position: Optional[int] = None,
    ) -> None:
        """
        添加处理步骤

        Args:
            step: 处理函数
            position: 插入位置（可选）
        """
        if position is None:
            self.steps.append(step)
        else:
            self.steps.insert(position, step)

        logger.info(f"添加处理步骤，当前共 {len(self.steps)} 个步骤")

    def run(
        self,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> PreprocessingResult:
        """
        运行处理管道

        Args:
            data: 输入数据

        Returns:
            处理结果
        """
        start_time = time.time()

        # 执行预处理器
        result = self.preprocessor.process(data)

        if result.errors:
            return result

        df = result.output_data

        # 执行自定义步骤
        step_errors = []
        for i, step in enumerate(self.steps):
            try:
                df = step(df)
                logger.debug(f"执行步骤 {i+1}")
            except Exception as e:
                step_errors.append(f"步骤 {i+1} 执行失败: {str(e)}")
                logger.warning(f"步骤 {i+1} 执行失败: {e}")

        result.errors.extend(step_errors)
        result.output_data = df
        result.processed_record_count = len(df)

        end_time = time.time()
        result.processing_time_ms += (end_time - start_time) * 1000

        return result

    def create_standard_pipeline(
        self,
        config: Optional[PreprocessingConfig] = None,
    ) -> "DataPipeline":
        """
        创建标准处理管道

        Args:
            config: 预处理配置

        Returns:
            标准管道实例
        """
        config = config or PreprocessingConfig()

        pipeline = DataPipeline()

        # 添加标准步骤
        if config.remove_duplicates:
            pipeline.add_step(lambda df: df.drop_duplicates())

        if config.handle_missing_values:
            if config.missing_value_strategy == "drop":
                pipeline.add_step(lambda df: df.dropna())
            elif config.missing_value_strategy == "mean":
                pipeline.add_step(lambda df: df.fillna(df.mean()))
            elif config.missing_value_strategy == "median":
                pipeline.add_step(lambda df: df.fillna(df.median()))

        if config.standardize_formats:
            pipeline.add_step(lambda df: df.applymap(
                lambda x: FieldTransformer.clean_text(x) if isinstance(x, str) else x
            ))

        return pipeline