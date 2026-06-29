"""
维度空间探针测试

测试维度空间探针的五大维度探测、报告生成、奇点检测等功能。
"""

import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ai_llm_agent_crawler.dimension import (
    DimensionSpaceProbe,
    ProbeDimension,
    DimensionProbeResult,
    ProbeReport,
)


@pytest.fixture
def probe():
    """创建探针实例"""
    return DimensionSpaceProbe()


@pytest.fixture
def sample_dataframe():
    """创建标准测试DataFrame"""
    np.random.seed(42)
    n = 100
    return pd.DataFrame({
        "id": range(1, n + 1),
        "name": [f"item_{i}" for i in range(1, n + 1)],
        "category": np.random.choice(["A", "B", "C", "D"], n),
        "value": np.random.randn(n) * 100 + 500,
        "quantity": np.random.randint(1, 100, n),
        "price": np.random.uniform(10, 1000, n),
        "created_at": [
            datetime.now() - timedelta(days=np.random.randint(0, 365))
            for _ in range(n)
        ],
        "description": [f"Description for item {i}" for i in range(1, n + 1)],
    })


@pytest.fixture
def low_quality_dataframe():
    """创建低质量测试DataFrame"""
    n = 50
    data = {
        "id": list(range(1, n + 1)),
        "value": [100] * 40 + [10000] * 10,
        "name": ["same_name"] * 30 + [None] * 20,
        "duplicate_col": [100] * 40 + [10000] * 10,
    }
    return pd.DataFrame(data)


@pytest.fixture
def empty_dataframe():
    """创建空DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def small_dataframe():
    """创建小型DataFrame"""
    return pd.DataFrame({
        "a": [1, 2, 3],
        "b": ["x", "y", "z"],
    })


@pytest.fixture
def large_dataframe():
    """创建大型DataFrame"""
    np.random.seed(123)
    n = 1000
    data = {}
    for i in range(10):
        if i % 2 == 0:
            data[f"num_{i}"] = np.random.randn(n) * 10 + 50
        else:
            data[f"str_{i}"] = [f"text_{j}" for j in range(n)]
    return pd.DataFrame(data)


class TestProbeModels:
    """测试探针数据模型"""

    def test_probe_dimension_enum(self):
        """测试探针维度枚举"""
        assert ProbeDimension.QUALITY == "quality"
        assert ProbeDimension.STRUCTURAL == "structural"
        assert ProbeDimension.STATISTICAL == "statistical"
        assert ProbeDimension.CONTENT == "content"
        assert ProbeDimension.RELATIONAL == "relational"
        assert len(list(ProbeDimension)) == 5

    def test_dimension_probe_result(self):
        """测试单维度探测结果模型"""
        result = DimensionProbeResult(
            dimension=ProbeDimension.QUALITY,
            quantitative_metrics={"completeness": 0.9, "accuracy": 0.85},
            qualitative_description="测试描述",
            anomalies_found=1,
            singularities=[{"type": "test"}],
            health_score=0.85,
            probe_depth=2,
            execution_time_ms=100.0,
        )
        assert result.dimension == ProbeDimension.QUALITY
        assert len(result.quantitative_metrics) == 2
        assert result.health_score == 0.85
        assert result.anomalies_found == 1

    def test_probe_report(self):
        """测试完整探测报告模型"""
        report = ProbeReport(
            report_id="probe_123_abcdefgh",
            dataset_name="test_dataset",
            record_count=100,
            field_count=5,
            overall_health_score=0.75,
        )
        assert report.report_id == "probe_123_abcdefgh"
        assert report.dataset_name == "test_dataset"
        assert report.record_count == 100
        assert 0 <= report.overall_health_score <= 1


class TestDimensionSpaceProbe:
    """测试维度空间探针类"""

    def test_probe_initialization(self, probe):
        """测试探针初始化"""
        assert probe is not None
        assert probe.quality_assessor is not None
        assert probe.singularity_detector is not None
        assert probe.probe_depth >= 1

    def test_probe_with_config(self):
        """测试带配置的初始化"""
        config = {
            "probe_depth": 3,
            "sensitivity": 0.9,
        }
        probe = DimensionSpaceProbe(config=config)
        assert probe.probe_depth == 3
        assert probe.singularity_detector.sensitivity == 0.9

    def test_full_probe_returns_5_dimensions(self, probe, sample_dataframe):
        """测试全维度探测返回5个维度的结果"""
        report = probe.probe(sample_dataframe, dataset_name="test")
        assert isinstance(report, ProbeReport)
        assert len(report.dimension_results) == 5
        assert "quality" in report.dimension_results
        assert "structural" in report.dimension_results
        assert "statistical" in report.dimension_results
        assert "content" in report.dimension_results
        assert "relational" in report.dimension_results

    def test_each_dimension_has_metrics_and_description(self, probe, sample_dataframe):
        """测试每个维度都有量化指标和定性描述"""
        report = probe.probe(sample_dataframe)
        for dim_key, result in report.dimension_results.items():
            assert isinstance(result, DimensionProbeResult)
            assert len(result.quantitative_metrics) > 0, f"{dim_key} 没有量化指标"
            assert len(result.qualitative_description) > 0, f"{dim_key} 没有定性描述"

    def test_probe_report_has_singularities(self, probe, low_quality_dataframe):
        """测试探测报告标记了奇点和异常"""
        report = probe.probe(low_quality_dataframe)
        total_anomalies = sum(
            r.anomalies_found for r in report.dimension_results.values()
        )
        assert total_anomalies > 0, "低质量数据应该检测到异常"

        total_singularities = sum(
            len(r.singularities) for r in report.dimension_results.values()
        )
        assert total_singularities > 0, "低质量数据应该检测到奇点"

    def test_empty_dataset_does_not_crash(self, probe, empty_dataframe):
        """测试空数据集不会导致崩溃"""
        report = probe.probe(empty_dataframe, dataset_name="empty")
        assert isinstance(report, ProbeReport)
        assert report.record_count == 0
        assert report.field_count == 0
        assert 0 <= report.overall_health_score <= 1

    def test_small_dataset_probe(self, probe, small_dataframe):
        """测试小型数据集能正常探测"""
        report = probe.probe(small_dataframe, dataset_name="small")
        assert isinstance(report, ProbeReport)
        assert report.record_count == 3
        assert report.field_count == 2
        assert len(report.dimension_results) == 5

    def test_large_dataset_probe(self, probe, large_dataframe):
        """测试大型数据集能正常探测"""
        report = probe.probe(large_dataframe, dataset_name="large")
        assert isinstance(report, ProbeReport)
        assert report.record_count == 1000
        assert report.field_count == 10
        assert len(report.dimension_results) == 5
        assert report.total_duration_ms >= 0

    def test_overall_health_in_range(self, probe, sample_dataframe):
        """测试整体健康度在0-1范围内"""
        report = probe.probe(sample_dataframe)
        assert 0 <= report.overall_health_score <= 1

    def test_critical_issues_and_warnings(self, probe, low_quality_dataframe):
        """测试严重问题和警告列表正确生成"""
        report = probe.probe(low_quality_dataframe)
        assert isinstance(report.critical_issues, list)
        assert isinstance(report.warnings, list)

        for issue in report.critical_issues:
            assert "severity" in issue
            assert issue["severity"] in ("high", "critical")

        for warning in report.warnings:
            assert "severity" in warning

    def test_recommendations_not_empty_when_issues(self, probe, low_quality_dataframe):
        """测试有问题时优化建议列表不为空"""
        report = probe.probe(low_quality_dataframe)
        assert len(report.recommendations) > 0, "有问题时应该有优化建议"

    def test_probe_summary_function(self, probe, sample_dataframe):
        """测试探测摘要功能正常"""
        report = probe.probe(sample_dataframe)
        summary = probe.get_probe_summary(report)

        assert "overall_health_score" in summary
        assert "total_issues" in summary
        assert "top_issues" in summary
        assert "key_recommendations" in summary
        assert "report_id" in summary
        assert "dataset_name" in summary
        assert len(summary["top_issues"]) <= 3
        assert len(summary["key_recommendations"]) <= 3

    def test_report_serializable_to_json(self, probe, sample_dataframe):
        """测试报告可序列化为JSON"""
        report = probe.probe(sample_dataframe)
        report_dict = report.model_dump()
        json_str = json.dumps(report_dict, default=str, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        parsed = json.loads(json_str)
        assert "report_id" in parsed
        assert "overall_health_score" in parsed
        assert "dimension_results" in parsed


class TestQualityProbe:
    """测试质量维度探测"""

    def test_probe_quality_returns_result(self, probe, sample_dataframe):
        """测试质量维度探测返回结果"""
        result = probe.probe_quality(sample_dataframe)
        assert isinstance(result, DimensionProbeResult)
        assert result.dimension == ProbeDimension.QUALITY
        assert len(result.quantitative_metrics) > 0
        assert 0 <= result.health_score <= 1

    def test_quality_metrics_include_standard_metrics(self, probe, sample_dataframe):
        """测试质量指标包含标准指标"""
        result = probe.probe_quality(sample_dataframe)
        metrics = result.quantitative_metrics
        assert "completeness" in metrics
        assert "accuracy" in metrics
        assert "consistency" in metrics
        assert "validity" in metrics


class TestStructuralProbe:
    """测试结构维度探测"""

    def test_probe_structural_returns_result(self, probe, sample_dataframe):
        """测试结构维度探测返回结果"""
        result = probe.probe_structural(sample_dataframe)
        assert isinstance(result, DimensionProbeResult)
        assert result.dimension == ProbeDimension.STRUCTURAL

    def test_structural_metrics(self, probe, sample_dataframe):
        """测试结构维度量化指标"""
        result = probe.probe_structural(sample_dataframe)
        metrics = result.quantitative_metrics
        assert "field_count" in metrics
        assert "record_count" in metrics
        assert "type_count" in metrics
        assert "sparsity" in metrics
        assert metrics["field_count"] == len(sample_dataframe.columns)
        assert metrics["record_count"] == len(sample_dataframe)


class TestStatisticalProbe:
    """测试统计维度探测"""

    def test_probe_statistical_returns_result(self, probe, sample_dataframe):
        """测试统计维度探测返回结果"""
        result = probe.probe_statistical(sample_dataframe)
        assert isinstance(result, DimensionProbeResult)
        assert result.dimension == ProbeDimension.STATISTICAL

    def test_statistical_metrics(self, probe, sample_dataframe):
        """测试统计维度量化指标"""
        result = probe.probe_statistical(sample_dataframe)
        metrics = result.quantitative_metrics
        assert "numeric_field_count" in metrics
        assert "avg_mean" in metrics
        assert "avg_std" in metrics
        assert "avg_skewness" in metrics
        assert "avg_kurtosis" in metrics
        assert "avg_outlier_ratio" in metrics


class TestContentProbe:
    """测试内容维度探测"""

    def test_probe_content_returns_result(self, probe, sample_dataframe):
        """测试内容维度探测返回结果"""
        result = probe.probe_content(sample_dataframe)
        assert isinstance(result, DimensionProbeResult)
        assert result.dimension == ProbeDimension.CONTENT

    def test_content_metrics(self, probe, sample_dataframe):
        """测试内容维度量化指标"""
        result = probe.probe_content(sample_dataframe)
        metrics = result.quantitative_metrics
        assert "text_field_count" in metrics
        assert "avg_text_length" in metrics
        assert "avg_null_ratio" in metrics
        assert "avg_duplicate_ratio" in metrics
        assert "avg_unique_ratio" in metrics


class TestRelationalProbe:
    """测试关系维度探测"""

    def test_probe_relational_returns_result(self, probe, sample_dataframe):
        """测试关系维度探测返回结果"""
        result = probe.probe_relational(sample_dataframe)
        assert isinstance(result, DimensionProbeResult)
        assert result.dimension == ProbeDimension.RELATIONAL

    def test_relational_metrics(self, probe, sample_dataframe):
        """测试关系维度量化指标"""
        result = probe.probe_relational(sample_dataframe)
        metrics = result.quantitative_metrics
        assert "numeric_field_count" in metrics
        assert "total_field_pairs" in metrics
        assert "high_correlation_pairs" in metrics
        assert "independence_score" in metrics
        assert 0 <= metrics["independence_score"] <= 1


class TestSingularityDetection:
    """测试奇点检测"""

    def test_detect_singularities_returns_list(self, probe, sample_dataframe):
        """测试奇点检测返回列表"""
        singularities = probe.detect_singularities(sample_dataframe)
        assert isinstance(singularities, list)

    def test_singularity_structure(self, probe, low_quality_dataframe):
        """测试奇点结构"""
        singularities = probe.detect_singularities(low_quality_dataframe)
        if singularities:
            sing = singularities[0]
            assert "type" in sing
            assert "severity" in sing
            assert "dimension" in sing
            assert "description" in sing
            assert "affected_records" in sing


class TestOverallHealthCalculation:
    """测试整体健康度计算"""

    def test_calculate_overall_health_weighted(self, probe):
        """测试整体健康度加权计算"""
        results = {}
        dims = [
            ProbeDimension.QUALITY,
            ProbeDimension.STRUCTURAL,
            ProbeDimension.STATISTICAL,
            ProbeDimension.CONTENT,
            ProbeDimension.RELATIONAL,
        ]
        for dim in dims:
            results[dim.value] = DimensionProbeResult(
                dimension=dim,
                health_score=0.8,
            )

        overall = probe._calculate_overall_health(results)
        assert abs(overall - 0.8) < 0.001

    def test_quality_has_higher_weight(self, probe):
        """测试质量维度权重更高"""
        quality_score = 0.5
        other_score = 0.9

        results = {}
        dims = [
            (ProbeDimension.QUALITY, quality_score),
            (ProbeDimension.STRUCTURAL, other_score),
            (ProbeDimension.STATISTICAL, other_score),
            (ProbeDimension.CONTENT, other_score),
            (ProbeDimension.RELATIONAL, other_score),
        ]
        for dim, score in dims:
            results[dim.value] = DimensionProbeResult(
                dimension=dim,
                health_score=score,
            )

        overall = probe._calculate_overall_health(results)
        expected = 0.3 * quality_score + 0.175 * other_score * 4
        assert abs(overall - expected) < 0.001


class TestReportGeneration:
    """测试报告生成"""

    def test_report_id_format(self, probe, sample_dataframe):
        """测试报告ID格式"""
        report = probe.probe(sample_dataframe)
        assert report.report_id.startswith("probe_")
        parts = report.report_id.split("_")
        assert len(parts) >= 3

    def test_probe_time_is_datetime(self, probe, sample_dataframe):
        """测试探测时间是datetime类型"""
        report = probe.probe(sample_dataframe)
        assert isinstance(report.probe_time, datetime)

    def test_total_duration_positive(self, probe, sample_dataframe):
        """测试总耗时为正"""
        report = probe.probe(sample_dataframe)
        assert report.total_duration_ms >= 0

    def test_dataset_name_preserved(self, probe, sample_dataframe):
        """测试数据集名称正确保存"""
        name = "my_test_dataset"
        report = probe.probe(sample_dataframe, dataset_name=name)
        assert report.dataset_name == name
