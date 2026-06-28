"""
维度空间分类器模块

提供多维数据分类和分析功能，支持内容、时间、空间、语义等维度的识别和分类。
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ai_llm_agent_crawler.dimension.models import (
    DimensionClassificationResult,
    DimensionFeature,
    DimensionType,
    DimensionVector,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DimensionRule:
    """维度识别规则"""
    dimension_type: DimensionType
    patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    data_types: List[str] = field(default_factory=list)
    value_ranges: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)
    priority: int = 0  # 规则优先级，数字越大优先级越高


class DimensionClassifier:
    """
    数据维度分类器

    支持多维数据分析，包括内容、时间、空间、语义等维度。
    使用规则引擎和启发式方法识别数据所属维度。
    """

    # 默认维度识别规则
    DEFAULT_RULES: Dict[DimensionType, DimensionRule] = {
        DimensionType.TEMPORAL: DimensionRule(
            dimension_type=DimensionType.TEMPORAL,
            patterns=[
                r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'^\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                r'^\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
                r'\d{4}年\d{1,2}月\d{1,2}日',  # 中文日期
                r'^\d{1,2}:\d{2}:\d{2}',  # 时间格式
                r'^\d{1,2}:\d{2}',  # 小时:分钟
            ],
            keywords=['time', 'date', 'timestamp', 'created', 'updated', '时间', '日期', '创建', '更新'],
            data_types=['datetime64', 'datetime', 'date', 'time'],
            priority=10,
        ),
        DimensionType.SPATIAL: DimensionRule(
            dimension_type=DimensionType.SPATIAL,
            patterns=[
                r'^-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+$',  # 经纬度
                r'^(latitude|longitude|lat|lon)[:：]?\s*-?\d',
                r'省|市|区|县|镇|乡|街道|路|号',
                r'(province|city|district|county|street|address)',
            ],
            keywords=['location', 'geo', 'address', 'city', 'country', 'latitude', 'longitude',
                     '位置', '地址', '城市', '国家', '经纬度'],
            data_types=['geopoint', 'geometry'],
            priority=9,
        ),
        DimensionType.CONTENT: DimensionRule(
            dimension_type=DimensionType.CONTENT,
            patterns=[
                r'^[a-zA-Z\u4e00-\u9fff\s\.,!?;:\"\'\-\(\)]{10,}$',  # 文本内容
                r'<[a-zA-Z][^>]*>',  # HTML标签
                r'^https?://',  # URL
            ],
            keywords=['text', 'content', 'description', 'body', 'html', 'url', 'title',
                     '内容', '文本', '描述', '标题'],
            data_types=['string', 'text', 'varchar', 'nvarchar'],
            priority=5,
        ),
        DimensionType.SEMANTIC: DimensionRule(
            dimension_type=DimensionType.SEMANTIC,
            patterns=[
                r'^(positive|negative|neutral)$',  # 情感标签
                r'^(happy|sad|angry|fear|surprise)$',  # 情绪标签
                r'(topic|subject|theme|category)[:：]?\s*\w+',
            ],
            keywords=['sentiment', 'emotion', 'topic', 'category', 'intent', 'meaning',
                     '情感', '主题', '分类', '意图', '语义'],
            priority=6,
        ),
        DimensionType.STATISTICAL: DimensionRule(
            dimension_type=DimensionType.STATISTICAL,
            patterns=[
                r'^(count|sum|avg|mean|min|max|std|var)_\w+',  # 统计字段名
                r'.*(score|rate|ratio|percentage|percent).*',
            ],
            keywords=['statistics', 'metric', 'value', 'count', 'average', 'sum',
                     '统计', '指标', '数值', '平均', '总计'],
            data_types=['int', 'float', 'decimal', 'numeric'],
            priority=7,
        ),
        DimensionType.STRUCTURAL: DimensionRule(
            dimension_type=DimensionType.STRUCTURAL,
            patterns=[
                r'^\{.*\}$',  # JSON
                r'^\[.*\]$',  # 数组
                r'^<[^>]+>.*</[^>]+>$',  # XML
            ],
            keywords=['json', 'xml', 'structure', 'schema', 'format', '结构', '格式', '模式'],
            priority=4,
        ),
        DimensionType.RELATIONAL: DimensionRule(
            dimension_type=DimensionType.RELATIONAL,
            patterns=[
                r'.*_id$',  # 外键
                r'^(parent|child|reference|link|relation)\w*',
                r'^\w+_to_\w+$',  # 关系命名
            ],
            keywords=['relation', 'reference', 'foreign_key', 'parent', 'child', 'link',
                     '关系', '引用', '关联', '外键'],
            priority=8,
        ),
        DimensionType.QUALITY: DimensionRule(
            dimension_type=DimensionType.QUALITY,
            patterns=[
                r'^(quality|score|grade|level|rank)\w*',
                r'.*(completeness|accuracy|consistency|validity).*',
            ],
            keywords=['quality', 'score', 'grade', 'completeness', 'accuracy',
                     '质量', '评分', '等级', '完整性', '准确性'],
            priority=3,
        ),
    }

    def __init__(
        self,
        custom_rules: Optional[Dict[DimensionType, DimensionRule]] = None,
        enable_parallel: bool = True,
        max_workers: int = 4,
    ):
        """
        初始化维度分类器

        Args:
            custom_rules: 自定义规则字典，会与默认规则合并
            enable_parallel: 是否启用并行处理
            max_workers: 最大并行工作线程数
        """
        self.rules = dict(self.DEFAULT_RULES)
        if custom_rules:
            self.rules.update(custom_rules)

        self.enable_parallel = enable_parallel
        self.max_workers = max_workers

        # 缓存已识别的维度
        self._dimension_cache: Dict[str, DimensionClassificationResult] = {}

        logger.info(f"维度分类器初始化完成，加载 {len(self.rules)} 条规则")

    def classify_field(
        self,
        field_name: str,
        field_value: Any,
        field_type: Optional[str] = None,
    ) -> DimensionClassificationResult:
        """
        对单个字段进行维度分类

        Args:
            field_name: 字段名称
            field_value: 字段值
            field_type: 字段数据类型（可选）

        Returns:
            维度分类结果
        """
        # 检查缓存
        cache_key = f"{field_name}_{field_type}"
        if cache_key in self._dimension_cache:
            return self._dimension_cache[cache_key]

        candidates: List[Tuple[DimensionType, float, List[DimensionFeature]]] = []

        for dim_type, rule in self.rules.items():
            score = 0.0
            features: List[DimensionFeature] = []

            # 匹配模式
            pattern_score = self._match_patterns(str(field_value) if field_value is not None else "", rule.patterns)
            if pattern_score > 0:
                score += pattern_score * 0.4
                features.append(DimensionFeature(
                    dimension_type=dim_type,
                    feature_name="pattern_match",
                    feature_value=pattern_score,
                    weight=0.4,
                ))

            # 匹配关键字
            keyword_score = self._match_keywords(field_name, rule.keywords)
            if keyword_score > 0:
                score += keyword_score * 0.3
                features.append(DimensionFeature(
                    dimension_type=dim_type,
                    feature_name="keyword_match",
                    feature_value=keyword_score,
                    weight=0.3,
                ))

            # 匹配数据类型
            if field_type:
                type_score = self._match_data_type(field_type, rule.data_types)
                if type_score > 0:
                    score += type_score * 0.2
                    features.append(DimensionFeature(
                        dimension_type=dim_type,
                        feature_name="type_match",
                        feature_value=type_score,
                        weight=0.2,
                    ))

            # 检查值范围
            if rule.value_ranges:
                range_score = self._check_value_ranges(field_value, rule.value_ranges)
                if range_score > 0:
                    score += range_score * 0.1
                    features.append(DimensionFeature(
                        dimension_type=dim_type,
                        feature_name="range_match",
                        feature_value=range_score,
                        weight=0.1,
                    ))

            if score > 0:
                # 添加优先级加权
                final_score = score * (1 + rule.priority * 0.1)
                candidates.append((dim_type, final_score, features))

        # 选择最佳匹配
        if not candidates:
            result = DimensionClassificationResult(
                dimension_type=DimensionType.CONTENT,  # 默认归类为内容维度
                confidence=0.0,
                features=[],
                metadata={"field_name": field_name, "fallback": True},
            )
        else:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_dim, best_score, best_features = candidates[0]

            result = DimensionClassificationResult(
                dimension_type=best_dim,
                confidence=min(best_score, 1.0),
                features=best_features,
                sub_dimensions=[c[0].value for c in candidates[1:3]] if len(candidates) > 1 else [],
                metadata={"field_name": field_name, "candidates_count": len(candidates)},
            )

        # 缓存结果
        self._dimension_cache[cache_key] = result
        return result

    def classify_record(
        self,
        record: Dict[str, Any],
        field_types: Optional[Dict[str, str]] = None,
    ) -> Dict[str, DimensionClassificationResult]:
        """
        对整条记录进行维度分类

        Args:
            record: 数据记录
            field_types: 字段类型映射（可选）

        Returns:
            字段名到分类结果的映射
        """
        results = {}
        field_types = field_types or {}

        for field_name, field_value in record.items():
            field_type = field_types.get(field_name)
            results[field_name] = self.classify_field(field_name, field_value, field_type)

        return results

    def classify_dataframe(
        self,
        df: pd.DataFrame,
        sample_size: int = 100,
    ) -> Dict[str, DimensionClassificationResult]:
        """
        对DataFrame进行维度分类

        Args:
            df: 要分类的DataFrame
            sample_size: 采样大小（用于分析字段值）

        Returns:
            字段名到分类结果的映射
        """
        results = {}

        # 获取数据类型映射
        field_types = {col: str(df[col].dtype) for col in df.columns}

        # 对每个字段进行分类
        for col in df.columns:
            # 采样分析
            sample_values = df[col].dropna().head(sample_size).tolist()
            sample_value = sample_values[0] if sample_values else None

            result = self.classify_field(col, sample_value, field_types.get(col))

            # 基于采样值修正置信度
            if sample_values:
                consistent_count = 0
                for val in sample_values[:10]:
                    temp_result = self.classify_field(col, val, field_types.get(col))
                    if temp_result.dimension_type == result.dimension_type:
                        consistent_count += 1
                result.confidence = consistent_count / min(10, len(sample_values))

            results[col] = result

        return results

    def create_dimension_vector(
        self,
        record: Dict[str, Any],
        classification_results: Optional[Dict[str, DimensionClassificationResult]] = None,
    ) -> DimensionVector:
        """
        创建维度向量

        Args:
            record: 数据记录
            classification_results: 预计算的分类结果（可选）

        Returns:
            维度向量
        """
        if classification_results is None:
            classification_results = self.classify_record(record)

        features: List[DimensionFeature] = []
        for field_name, result in classification_results.items():
            feature = DimensionFeature(
                dimension_type=result.dimension_type,
                feature_name=field_name,
                feature_value=str(record.get(field_name, "")),
                weight=result.confidence,
                confidence=result.confidence,
                metadata={"sub_dimensions": result.sub_dimensions},
            )
            features.append(feature)

        return DimensionVector(features=features)

    def get_dimension_distribution(
        self,
        classification_results: Dict[str, DimensionClassificationResult],
    ) -> Dict[DimensionType, int]:
        """
        获取维度分布统计

        Args:
            classification_results: 分类结果

        Returns:
            各维度的字段数量统计
        """
        distribution: Dict[DimensionType, int] = {}
        for result in classification_results.values():
            dim = result.dimension_type
            distribution[dim] = distribution.get(dim, 0) + 1

        return distribution

    def analyze_dimension_coverage(
        self,
        classification_results: Dict[str, DimensionClassificationResult],
    ) -> Dict[str, Any]:
        """
        分析维度覆盖度

        Args:
            classification_results: 分类结果

        Returns:
            维度覆盖度分析报告
        """
        total_fields = len(classification_results)
        if total_fields == 0:
            return {"coverage": {}, "missing_dimensions": list(DimensionType)}

        distribution = self.get_dimension_distribution(classification_results)

        # 计算每个维度的覆盖度
        coverage = {}
        for dim_type in DimensionType:
            count = distribution.get(dim_type, 0)
            coverage[dim_type.value] = {
                "count": count,
                "percentage": count / total_fields * 100,
            }

        # 识别缺失的维度
        missing = [dim.value for dim in DimensionType if dim not in distribution]

        # 计算维度多样性指数
        diversity_index = len(distribution) / len(DimensionType)

        # 计算平均置信度
        avg_confidence = sum(r.confidence for r in classification_results.values()) / total_fields

        return {
            "coverage": coverage,
            "missing_dimensions": missing,
            "diversity_index": diversity_index,
            "average_confidence": avg_confidence,
            "total_fields": total_fields,
        }

    def batch_classify(
        self,
        records: List[Dict[str, Any]],
        field_types: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, DimensionClassificationResult]]:
        """
        批量分类记录

        Args:
            records: 数据记录列表
            field_types: 字段类型映射（可选）

        Returns:
            分类结果列表
        """
        if not self.enable_parallel or len(records) < 100:
            return [self.classify_record(record, field_types) for record in records]

        results = [None] * len(records)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.classify_record, record, field_types): idx
                for idx, record in enumerate(records)
            }

            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()

        return results

    def clear_cache(self) -> None:
        """清除分类缓存"""
        self._dimension_cache.clear()
        logger.info("维度分类缓存已清除")

    def add_custom_rule(self, rule: DimensionRule) -> None:
        """
        添加自定义规则

        Args:
            rule: 维度规则
        """
        self.rules[rule.dimension_type] = rule
        self._dimension_cache.clear()
        logger.info(f"已添加自定义维度规则: {rule.dimension_type.value}")

    def _match_patterns(self, value: str, patterns: List[str]) -> float:
        """匹配模式，返回匹配得分"""
        if not value or not patterns:
            return 0.0

        match_count = 0
        for pattern in patterns:
            try:
                if re.search(pattern, value, re.IGNORECASE):
                    match_count += 1
            except re.error:
                continue

        return min(match_count / len(patterns), 1.0) if patterns else 0.0

    def _match_keywords(self, field_name: str, keywords: List[str]) -> float:
        """匹配关键字，返回匹配得分"""
        if not field_name or not keywords:
            return 0.0

        field_name_lower = field_name.lower()
        match_count = sum(1 for kw in keywords if kw.lower() in field_name_lower)

        return min(match_count / len(keywords), 1.0) if keywords else 0.0

    def _match_data_type(self, field_type: str, data_types: List[str]) -> float:
        """匹配数据类型，返回匹配得分"""
        if not field_type or not data_types:
            return 0.0

        field_type_lower = field_type.lower()
        for dt in data_types:
            if dt.lower() in field_type_lower:
                return 1.0

        return 0.0

    def _check_value_ranges(self, value: Any, value_ranges: Dict[str, Tuple[Any, Any]]) -> float:
        """检查值范围"""
        if value is None or not value_ranges:
            return 0.0

        try:
            if isinstance(value, (int, float)):
                for range_name, (min_val, max_val) in value_ranges.items():
                    if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                        if min_val <= value <= max_val:
                            return 1.0
        except (TypeError, ValueError):
            pass

        return 0.0


class TemporalDimensionAnalyzer:
    """时间维度分析器"""

    @staticmethod
    def analyze_timestamp_field(values: pd.Series) -> Dict[str, Any]:
        """
        分析时间戳字段

        Args:
            values: 时间戳序列

        Returns:
            时间维度分析结果
        """
        results = {}

        # 转换为datetime
        try:
            dt_values = pd.to_datetime(values, errors='coerce')
            valid_dt = dt_values.dropna()

            if len(valid_dt) > 0:
                results.update({
                    "min_time": valid_dt.min().isoformat(),
                    "max_time": valid_dt.max().isoformat(),
                    "time_range_days": (valid_dt.max() - valid_dt.min()).days,
                    "valid_count": len(valid_dt),
                    "invalid_count": len(values) - len(valid_dt),
                })

                # 分析时间分布
                results["time_distribution"] = {
                    "hour": valid_dt.dt.hour.value_counts().to_dict(),
                    "day_of_week": valid_dt.dt.dayofweek.value_counts().to_dict(),
                    "month": valid_dt.dt.month.value_counts().to_dict(),
                }
        except Exception as e:
            results["error"] = str(e)

        return results

    @staticmethod
    def detect_time_series_pattern(values: pd.Series) -> Dict[str, Any]:
        """
        检测时间序列模式

        Args:
            values: 数值序列

        Returns:
            时间序列模式检测结果
        """
        if len(values) < 3:
            return {"pattern": "insufficient_data"}

        results = {}

        # 检测趋势
        diff = values.diff().dropna()
        if len(diff) > 0:
            positive_count = (diff > 0).sum()
            negative_count = (diff < 0).sum()

            if positive_count > negative_count * 1.5:
                results["trend"] = "increasing"
            elif negative_count > positive_count * 1.5:
                results["trend"] = "decreasing"
            else:
                results["trend"] = "stable"

        # 检测周期性（简化版）
        results["has_pattern"] = len(values) > 10

        return results


class SpatialDimensionAnalyzer:
    """空间维度分析器"""

    @staticmethod
    def analyze_geo_field(values: pd.Series) -> Dict[str, Any]:
        """
        分析地理字段

        Args:
            values: 地理数据序列

        Returns:
            空间维度分析结果
        """
        results = {}

        # 尝试解析经纬度
        coords = []
        for val in values.dropna():
            try:
                if isinstance(val, str):
                    # 尝试解析 "lat,lon" 格式
                    parts = val.split(',')
                    if len(parts) == 2:
                        lat, lon = float(parts[0]), float(parts[1])
                        coords.append((lat, lon))
            except (ValueError, AttributeError):
                continue

        if coords:
            lats, lons = zip(*coords)
            results.update({
                "count": len(coords),
                "lat_range": [min(lats), max(lats)],
                "lon_range": [min(lons), max(lons)],
                "center": [np.mean(lats), np.mean(lons)],
            })

        return results


class SemanticDimensionAnalyzer:
    """语义维度分析器"""

    # 情感关键词
    POSITIVE_KEYWORDS = {'good', 'great', 'excellent', 'happy', 'positive', 'love', '好', '优秀', '满意', '喜欢'}
    NEGATIVE_KEYWORDS = {'bad', 'poor', 'terrible', 'sad', 'negative', 'hate', '坏', '差', '不满', '讨厌'}

    @staticmethod
    def analyze_text_field(values: pd.Series) -> Dict[str, Any]:
        """
        分析文本字段

        Args:
            values: 文本序列

        Returns:
            语义维度分析结果
        """
        results = {}

        valid_texts = values.dropna().astype(str)
        if len(valid_texts) == 0:
            return results

        # 基本统计
        results.update({
            "count": len(valid_texts),
            "avg_length": valid_texts.str.len().mean(),
            "max_length": valid_texts.str.len().max(),
            "min_length": valid_texts.str.len().min(),
        })

        # 情感分析（简化版）
        positive_count = sum(1 for text in valid_texts
                           if any(kw in text.lower() for kw in SemanticDimensionAnalyzer.POSITIVE_KEYWORDS))
        negative_count = sum(1 for text in valid_texts
                           if any(kw in text.lower() for kw in SemanticDimensionAnalyzer.NEGATIVE_KEYWORDS))

        results["sentiment"] = {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": len(valid_texts) - positive_count - negative_count,
        }

        return results