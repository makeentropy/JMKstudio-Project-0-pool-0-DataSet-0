"""
路径探测与空间分析测试

测试路径探测、临界点识别、异常区域识别、空间拓扑分析等功能。
"""

import pytest
import pandas as pd
import numpy as np

from ai_llm_agent_crawler.dimension import (
    DimensionSpaceProbe,
    PathProbePoint,
    PathProbeResult,
    DimensionTopology,
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
    })


@pytest.fixture
def outlier_dataframe():
    """包含离群点的测试DataFrame"""
    np.random.seed(123)
    n_normal = 90
    n_outlier = 10
    normal_values = np.random.randn(n_normal) * 10 + 50
    outlier_values = np.array([500, 600, 700, 800, 900, -300, -400, -500, -600, -700])
    all_values = np.concatenate([normal_values, outlier_values])
    np.random.shuffle(all_values)
    return pd.DataFrame({
        "value": all_values,
        "other": np.random.randn(len(all_values)) * 5 + 20,
    })


@pytest.fixture
def empty_dataframe():
    """创建空DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def single_value_dataframe():
    """单值DataFrame"""
    return pd.DataFrame({"x": [5.0] * 50})


@pytest.fixture
def categorical_dataframe():
    """分类数据DataFrame"""
    return pd.DataFrame({
        "category": ["A"] * 50 + ["B"] * 30 + ["C"] * 15 + ["D"] * 5,
        "value": range(100),
    })


class TestPathProbeModels:
    """测试路径探测数据模型"""

    def test_path_probe_point_model(self):
        """测试路径探测点模型"""
        point = PathProbePoint(
            position=0.5,
            density=0.1,
            value=100.0,
            is_critical=False,
            anomaly_score=1.5,
            description="测试点",
        )
        assert point.position == 0.5
        assert point.density == 0.1
        assert point.value == 100.0
        assert not point.is_critical
        assert point.anomaly_score == 1.5
        assert point.description == "测试点"

    def test_path_probe_point_defaults(self):
        """测试路径探测点默认值"""
        point = PathProbePoint()
        assert point.position == 0.0
        assert point.density == 0.0
        assert point.value == 0.0
        assert not point.is_critical
        assert point.anomaly_score == 0.0
        assert point.description == ""

    def test_path_probe_result_model(self):
        """测试路径探测结果模型"""
        points = [PathProbePoint(position=0.5, density=0.1)]
        result = PathProbeResult(
            dimension="test_field",
            path_points=points,
            distribution={"mean": 100.0, "std": 10.0},
            critical_points=[],
            anomaly_regions=[],
            step_size=0.05,
            total_depth=2,
            execution_time_ms=10.0,
        )
        assert result.dimension == "test_field"
        assert len(result.path_points) == 1
        assert result.distribution["mean"] == 100.0
        assert result.step_size == 0.05

    def test_dimension_topology_model(self):
        """测试维度空间拓扑模型"""
        topology = DimensionTopology(
            num_dimensions=3,
            distance_matrix=[[0, 0.5, 0.8], [0.5, 0, 0.3], [0.8, 0.3, 0]],
            density_distribution={"a": 1.0, "b": 2.0},
            centroid={"a": 50.0, "b": 100.0},
            boundary_points=[{"field": "a", "min": 0, "max": 100}],
            cluster_count=2,
            cluster_info=[{"cluster_id": 0, "size": 50}],
        )
        assert topology.num_dimensions == 3
        assert topology.distance_matrix is not None
        assert len(topology.density_distribution) == 2
        assert topology.cluster_count == 2


class TestProbePath:
    """测试单字段路径探测"""

    def test_probe_path_returns_correct_structure(self, probe, sample_dataframe):
        """测试单字段路径探测返回正确结构"""
        result = probe.probe_path(sample_dataframe, "value")
        assert isinstance(result, PathProbeResult)
        assert result.dimension == "value"
        assert isinstance(result.path_points, list)
        assert isinstance(result.distribution, dict)
        assert isinstance(result.critical_points, list)
        assert isinstance(result.anomaly_regions, list)
        assert result.execution_time_ms >= 0

    def test_probe_path_has_distribution_stats(self, probe, sample_dataframe):
        """测试路径探测包含分布统计信息"""
        result = probe.probe_path(sample_dataframe, "value")
        dist = result.distribution
        assert "min" in dist
        assert "max" in dist
        assert "mean" in dist
        assert "median" in dist
        assert "std" in dist
        assert "skew" in dist
        assert "kurtosis" in dist

    def test_probe_path_point_count(self, probe, sample_dataframe):
        """测试路径探测点数量与步长对应"""
        step_size = 0.05
        result = probe.probe_path(sample_dataframe, "value", step_size=step_size)
        expected_points = int(1.0 / step_size)
        assert len(result.path_points) == expected_points

    def test_probe_path_positions_in_range(self, probe, sample_dataframe):
        """测试路径探测点位置在0-1范围内"""
        result = probe.probe_path(sample_dataframe, "value")
        for point in result.path_points:
            assert 0.0 <= point.position <= 1.0
            assert point.density >= 0.0

    def test_probe_path_with_outliers(self, probe, outlier_dataframe):
        """测试路径探测能识别离群点区域"""
        result = probe.probe_path(outlier_dataframe, "value")
        assert len(result.critical_points) > 0
        has_outlier_critical = any(
            "异常值" in p.description for p in result.critical_points
        )
        assert has_outlier_critical

    def test_probe_path_different_step_sizes(self, probe, sample_dataframe):
        """测试修改步长后探测结果粒度变化"""
        result_fine = probe.probe_path(sample_dataframe, "value", step_size=0.02)
        result_coarse = probe.probe_path(sample_dataframe, "value", step_size=0.1)
        assert len(result_fine.path_points) > len(result_coarse.path_points)

    def test_probe_path_nonexistent_field(self, probe, sample_dataframe):
        """测试不存在的字段路径探测"""
        result = probe.probe_path(sample_dataframe, "nonexistent_field")
        assert isinstance(result, PathProbeResult)
        assert result.dimension == "nonexistent_field"
        assert len(result.path_points) == 0

    def test_probe_path_empty_dataframe(self, probe, empty_dataframe):
        """测试空数据集不会崩溃"""
        result = probe.probe_path(empty_dataframe, "value")
        assert isinstance(result, PathProbeResult)
        assert len(result.path_points) == 0

    def test_probe_path_single_value(self, probe, single_value_dataframe):
        """测试单值数据集不会崩溃"""
        result = probe.probe_path(single_value_dataframe, "x")
        assert isinstance(result, PathProbeResult)

    def test_probe_path_categorical_field(self, probe, categorical_dataframe):
        """测试非数值字段有合理的降级处理"""
        result = probe.probe_path(categorical_dataframe, "category")
        assert isinstance(result, PathProbeResult)
        assert len(result.path_points) > 0
        assert "unique_count" in result.distribution


class TestProbePathMulti:
    """测试多字段路径探测"""

    def test_probe_path_multi_returns_mapping(self, probe, sample_dataframe):
        """测试多字段路径探测返回正确映射"""
        fields = ["value", "quantity", "price"]
        results = probe.probe_path_multi(sample_dataframe, fields)
        assert isinstance(results, dict)
        assert len(results) == 3
        for field in fields:
            assert field in results
            assert isinstance(results[field], PathProbeResult)

    def test_probe_path_multi_empty_list(self, probe, sample_dataframe):
        """测试空字段列表"""
        results = probe.probe_path_multi(sample_dataframe, [])
        assert isinstance(results, dict)
        assert len(results) == 0

    def test_probe_path_multi_with_nonexistent(self, probe, sample_dataframe):
        """测试包含不存在字段的多字段探测"""
        fields = ["value", "nonexistent"]
        results = probe.probe_path_multi(sample_dataframe, fields)
        assert len(results) == 2
        assert "value" in results
        assert "nonexistent" in results


class TestCriticalPoints:
    """测试临界点检测"""

    def test_find_critical_points_returns_list(self, probe, sample_dataframe):
        """测试查找临界点返回列表"""
        points = probe.find_critical_points(sample_dataframe["value"])
        assert isinstance(points, list)

    def test_find_critical_points_structure(self, probe, outlier_dataframe):
        """测试临界点结构"""
        points = probe.find_critical_points(outlier_dataframe["value"])
        if points:
            point = points[0]
            assert "position" in point
            assert "value" in point
            assert "type" in point
            assert "severity" in point
            assert 0.0 <= point["position"] <= 1.0

    def test_find_critical_points_with_outliers(self, probe, outlier_dataframe):
        """测试能正确识别离群点"""
        points = probe.find_critical_points(outlier_dataframe["value"])
        outlier_points = [p for p in points if p["type"] == "outlier"]
        assert len(outlier_points) > 0

    def test_find_critical_points_empty_series(self, probe):
        """测试空序列不崩溃"""
        empty_series = pd.Series([], dtype=float)
        points = probe.find_critical_points(empty_series)
        assert isinstance(points, list)
        assert len(points) == 0

    def test_find_critical_points_threshold(self, probe, outlier_dataframe):
        """测试不同阈值下临界点数量变化"""
        points_low = probe.find_critical_points(outlier_dataframe["value"], threshold=1.0)
        points_high = probe.find_critical_points(outlier_dataframe["value"], threshold=3.0)
        assert len(points_low) >= len(points_high)


class TestAnomalyRegions:
    """测试异常区域识别"""

    def test_find_anomaly_regions_returns_list(self, probe):
        """测试查找异常区域返回列表"""
        points = [
            PathProbePoint(position=p * 0.1, anomaly_score=1.0)
            for p in range(10)
        ]
        regions = probe.find_anomaly_regions(points)
        assert isinstance(regions, list)

    def test_find_anomaly_regions_detects_consecutive(self, probe):
        """测试能正确识别连续异常区域"""
        points = []
        for i in range(20):
            score = 3.0 if 5 <= i <= 10 else 1.0
            points.append(PathProbePoint(position=i * 0.05, anomaly_score=score))

        regions = probe.find_anomaly_regions(points, min_consecutive=3)
        assert len(regions) == 1
        assert regions[0]["consecutive_count"] == 6
        assert regions[0]["severity"] == "high"

    def test_find_anomaly_regions_no_anomalies(self, probe):
        """测试无异常时返回空列表"""
        points = [PathProbePoint(position=p * 0.1, anomaly_score=1.0) for p in range(10)]
        regions = probe.find_anomaly_regions(points)
        assert len(regions) == 0

    def test_find_anomaly_regions_multiple_regions(self, probe):
        """测试识别多个不连续的异常区域"""
        points = []
        for i in range(20):
            if 2 <= i <= 5 or 12 <= i <= 16:
                score = 2.5
            else:
                score = 0.5
            points.append(PathProbePoint(position=i * 0.05, anomaly_score=score))

        regions = probe.find_anomaly_regions(points, min_consecutive=3)
        assert len(regions) == 2

    def test_find_anomaly_regions_below_min_consecutive(self, probe):
        """测试连续异常数低于阈值时不识别"""
        points = [
            PathProbePoint(position=p * 0.1, anomaly_score=2.5)
            for p in range(2)
        ]
        points += [PathProbePoint(position=0.5, anomaly_score=0.5)]
        regions = probe.find_anomaly_regions(points, min_consecutive=3)
        assert len(regions) == 0

    def test_find_anomaly_regions_region_structure(self, probe):
        """测试异常区域结构完整"""
        points = [
            PathProbePoint(position=p * 0.1, anomaly_score=2.5)
            for p in range(5)
        ]
        regions = probe.find_anomaly_regions(points, min_consecutive=3)
        assert len(regions) == 1
        region = regions[0]
        assert "start" in region
        assert "end" in region
        assert "severity" in region
        assert "description" in region
        assert "consecutive_count" in region
        assert "max_anomaly_score" in region


class TestDistanceMatrix:
    """测试距离矩阵计算"""

    def test_compute_distance_matrix_returns_matrix(self, probe, sample_dataframe):
        """测试距离矩阵返回正确结构"""
        matrix = probe.compute_distance_matrix(sample_dataframe)
        assert isinstance(matrix, list)
        assert len(matrix) > 0
        assert isinstance(matrix[0], list)

    def test_distance_matrix_is_symmetric(self, probe, sample_dataframe):
        """测试距离矩阵是对称的"""
        matrix = probe.compute_distance_matrix(sample_dataframe)
        n = len(matrix)
        for i in range(n):
            for j in range(n):
                assert abs(matrix[i][j] - matrix[j][i]) < 1e-9

    def test_distance_matrix_diagonal_zero(self, probe, sample_dataframe):
        """测试距离矩阵对角线为0"""
        matrix = probe.compute_distance_matrix(sample_dataframe)
        for i in range(len(matrix)):
            assert matrix[i][i] == 0.0

    def test_distance_matrix_values_in_range(self, probe, sample_dataframe):
        """测试距离值在0-1范围内"""
        matrix = probe.compute_distance_matrix(sample_dataframe)
        for row in matrix:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_distance_matrix_single_column(self, probe):
        """测试单列数据的距离矩阵"""
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        matrix = probe.compute_distance_matrix(df)
        assert len(matrix) == 1
        assert matrix[0][0] == 0.0

    def test_distance_matrix_no_numeric_columns(self, probe):
        """测试无数值列时返回空列表"""
        df = pd.DataFrame({"a": ["x", "y", "z"], "b": ["p", "q", "r"]})
        matrix = probe.compute_distance_matrix(df)
        assert matrix == []


class TestClusters:
    """测试聚类检测"""

    def test_detect_clusters_returns_list(self, probe, sample_dataframe):
        """测试聚类检测返回列表"""
        clusters = probe.detect_clusters(sample_dataframe)
        assert isinstance(clusters, list)

    def test_detect_clusters_reasonable_count(self, probe, sample_dataframe):
        """测试聚类检测返回合理的聚类数"""
        n_clusters = 3
        clusters = probe.detect_clusters(sample_dataframe, n_clusters=n_clusters)
        assert len(clusters) == n_clusters

    def test_detect_clusters_structure(self, probe, sample_dataframe):
        """测试聚类信息结构完整"""
        clusters = probe.detect_clusters(sample_dataframe, n_clusters=2)
        if clusters:
            cluster = clusters[0]
            assert "cluster_id" in cluster
            assert "size" in cluster
            assert "center" in cluster
            assert "feature_description" in cluster
            assert "range" in cluster
            assert cluster["size"] > 0

    def test_detect_clusters_empty_dataframe(self, probe, empty_dataframe):
        """测试空数据集聚类"""
        clusters = probe.detect_clusters(empty_dataframe)
        assert isinstance(clusters, list)
        assert len(clusters) == 0

    def test_detect_clusters_no_numeric_columns(self, probe):
        """测试无数值列时返回空列表"""
        df = pd.DataFrame({"a": ["x", "y", "z"] * 10})
        clusters = probe.detect_clusters(df)
        assert isinstance(clusters, list)
        assert len(clusters) == 0

    def test_detect_clusters_too_few_data(self, probe):
        """测试数据量不足时的处理"""
        df = pd.DataFrame({"x": [1, 2]})
        clusters = probe.detect_clusters(df, n_clusters=5)
        assert isinstance(clusters, list)
        assert len(clusters) <= len(df)


class TestDensityHistogram:
    """测试密度直方图生成"""

    def test_generate_density_histogram_structure(self, probe, sample_dataframe):
        """测试密度直方图返回正确结构"""
        result = probe.generate_density_histogram(sample_dataframe["value"])
        assert isinstance(result, dict)
        assert "bin_edges" in result
        assert "counts" in result
        assert "densities" in result
        assert "peak_position" in result
        assert "peak_value" in result
        assert "total_count" in result

    def test_density_histogram_bin_count(self, probe, sample_dataframe):
        """测试密度直方图返回正确的bin数量"""
        bins = 20
        result = probe.generate_density_histogram(sample_dataframe["value"], bins=bins)
        assert len(result["counts"]) == bins
        assert len(result["bin_edges"]) == bins + 1
        assert len(result["densities"]) == bins

    def test_density_histogram_densities_sum(self, probe, sample_dataframe):
        """测试密度和接近1"""
        result = probe.generate_density_histogram(sample_dataframe["value"], bins=20)
        total_density = sum(result["densities"])
        assert abs(total_density - 1.0) < 0.01

    def test_density_histogram_peak_valid(self, probe, sample_dataframe):
        """测试峰值位置有效"""
        result = probe.generate_density_histogram(sample_dataframe["value"])
        assert result["peak_position"] is not None
        assert result["peak_value"] > 0
        assert result["peak_value"] == max(result["counts"])

    def test_density_histogram_empty_series(self, probe):
        """测试空序列直方图"""
        empty_series = pd.Series([], dtype=float)
        result = probe.generate_density_histogram(empty_series)
        assert result["total_count"] == 0
        assert len(result["counts"]) == 0
        assert result["peak_position"] is None


class TestAnalyzeTopology:
    """测试空间拓扑分析"""

    def test_analyze_topology_returns_correct_type(self, probe, sample_dataframe):
        """测试空间拓扑分析返回正确类型"""
        topology = probe.analyze_topology(sample_dataframe)
        assert isinstance(topology, DimensionTopology)

    def test_analyze_topology_has_all_fields(self, probe, sample_dataframe):
        """测试空间拓扑分析返回所有预期字段"""
        topology = probe.analyze_topology(sample_dataframe)
        assert topology.num_dimensions > 0
        assert topology.distance_matrix is not None
        assert isinstance(topology.density_distribution, dict)
        assert isinstance(topology.centroid, dict)
        assert isinstance(topology.boundary_points, list)
        assert topology.cluster_count >= 0
        assert isinstance(topology.cluster_info, list)

    def test_analyze_topology_num_dimensions(self, probe, sample_dataframe):
        """测试维度数正确"""
        topology = probe.analyze_topology(sample_dataframe)
        numeric_cols = sample_dataframe.select_dtypes(include=[np.number]).columns
        assert topology.num_dimensions == len(numeric_cols)

    def test_analyze_topology_centroid_keys(self, probe, sample_dataframe):
        """测试质心包含所有数值字段"""
        topology = probe.analyze_topology(sample_dataframe)
        numeric_cols = sample_dataframe.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert col in topology.centroid

    def test_analyze_topology_empty_dataframe(self, probe, empty_dataframe):
        """测试空数据集拓扑分析不崩溃"""
        topology = probe.analyze_topology(empty_dataframe)
        assert isinstance(topology, DimensionTopology)
        assert topology.num_dimensions == 0

    def test_analyze_topology_boundary_points(self, probe, sample_dataframe):
        """测试边界点包含所有数值字段"""
        topology = probe.analyze_topology(sample_dataframe)
        numeric_cols = sample_dataframe.select_dtypes(include=[np.number]).columns
        assert len(topology.boundary_points) == len(numeric_cols)
        for bp in topology.boundary_points:
            assert "field" in bp
            assert "min" in bp
            assert "max" in bp
            assert "range" in bp
