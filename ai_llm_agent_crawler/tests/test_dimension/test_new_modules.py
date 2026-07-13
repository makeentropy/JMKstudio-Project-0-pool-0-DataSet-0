"""
新模块测试用例

测试维度量化器、两仪模型、熵数据审查器和HDF5预览框架的功能。
"""

import os
import pytest
import pandas as pd
import numpy as np
import tempfile
from datetime import datetime, timedelta

from ai_llm_agent_crawler.dimension import (
    DimensionType,
    DataMassEnergy,
    QualityAssessment,
    QualityMetric,
    QualityMetricType,
    DimensionQuantizer,
    MultiDimensionQuantizer,
    YinYangModel,
    YinYangEvolution,
    EntropyAuditor,
    EntropyDrivenQualityAssessor,
)

from ai_llm_agent_crawler.dataset import H5PreviewManager, H5DataExtractor, H5JSPreviewGenerator


class TestDimensionQuantizer:
    """测试维度量化器"""

    @pytest.fixture
    def quantizer(self):
        """创建量化器实例"""
        return DimensionQuantizer()

    @pytest.fixture
    def sample_dataframe(self):
        """创建测试DataFrame"""
        return pd.DataFrame({
            "id": range(100),
            "name": [f"item_{i}" for i in range(100)],
            "value": np.random.randn(100),
            "category": np.random.choice(["A", "B", "C"], 100),
            "created_at": pd.date_range("2024-01-01", periods=100, freq="D"),
            "price": np.random.uniform(10, 1000, 100),
        })

    def test_quantizer_initialization(self, quantizer):
        """测试量化器初始化"""
        assert quantizer is not None
        assert quantizer.config is not None

    def test_quantize_numeric(self, quantizer):
        """测试数值维度量化"""
        values = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = quantizer.quantize(DimensionType.STATISTICAL, values)
        assert result is not None
        assert 0 <= result.normalized_score <= 1
        assert result.entropy >= 0

    def test_quantize_text(self, quantizer):
        """测试文本维度量化"""
        values = pd.Series(["hello", "world", "test", "data", "sample"])
        result = quantizer.quantize(DimensionType.CONTENT, values)
        assert result is not None
        assert 0 <= result.normalized_score <= 1

    def test_quantize_temporal(self, quantizer):
        """测试时间维度量化"""
        dates = pd.date_range(datetime.now() - timedelta(days=30), periods=10)
        result = quantizer.quantize(DimensionType.TEMPORAL, dates)
        assert result is not None
        assert result.normalized_score > 0.5

    def test_quantize_field(self, quantizer, sample_dataframe):
        """测试字段量化"""
        result = quantizer.quantize_field("price", sample_dataframe["price"])
        assert result is not None
        assert result.metadata["field_name"] == "price"

    def test_quantize_dataframe(self, quantizer, sample_dataframe):
        """测试DataFrame量化"""
        results = quantizer.quantize_dataframe(sample_dataframe)
        assert len(results) == len(sample_dataframe.columns)
        for field_name, result in results.items():
            assert result is not None
            assert 0 <= result.normalized_score <= 1

    def test_quantize_with_mass_energy(self, quantizer):
        """测试结合质能模型量化"""
        values = pd.Series([1, 2, 3, 4, 5])
        mass_energy = DataMassEnergy(
            data_mass=100.0,
            data_energy=50.0,
            quality_factor=0.8,
            density=60.0,
            entropy=3.0,
        )
        result = quantizer.quantize_with_mass_energy(
            DimensionType.STATISTICAL, values, mass_energy
        )
        assert result.quality_factor == 0.8
        assert "data_mass" in result.metadata

    def test_generate_quantization_report(self, quantizer, sample_dataframe):
        """测试生成量化报告"""
        results = quantizer.quantize_dataframe(sample_dataframe)
        report = quantizer.generate_quantization_report(results)
        assert "summary" in report
        assert "dimension_distribution" in report
        assert "fields" in report
        assert "recommendations" in report

    def test_infer_dimension_type(self, quantizer):
        """测试维度类型推断"""
        dim_type = quantizer._infer_dimension_type("created_at", pd.Series(["2024-01-01"]))
        assert dim_type == DimensionType.TEMPORAL

        dim_type = quantizer._infer_dimension_type("location", pd.Series(["39.9, 116.4"]))
        assert dim_type == DimensionType.SPATIAL

        dim_type = quantizer._infer_dimension_type("value", pd.Series([1, 2, 3]))
        assert dim_type == DimensionType.STATISTICAL


class TestMultiDimensionQuantizer:
    """测试多维量化器"""

    @pytest.fixture
    def multi_quantizer(self):
        """创建多维量化器实例"""
        return MultiDimensionQuantizer()

    @pytest.fixture
    def sample_dataframe(self):
        """创建测试DataFrame"""
        return pd.DataFrame({
            "id": range(50),
            "name": [f"product_{i}" for i in range(50)],
            "price": np.random.uniform(10, 500, 50),
            "created_date": pd.date_range("2024-01-01", periods=50, freq="D"),
            "category": np.random.choice(["electronics", "clothing", "food"], 50),
            "rating": np.random.uniform(1, 5, 50),
        })

    def test_multi_quantizer_initialization(self, multi_quantizer):
        """测试多维量化器初始化"""
        assert multi_quantizer is not None
        assert multi_quantizer.quantizer is not None

    def test_quantize_all_dimensions(self, multi_quantizer, sample_dataframe):
        """测试量化所有维度"""
        results = multi_quantizer.quantize_all_dimensions(sample_dataframe)
        assert isinstance(results, dict)
        assert len(results) > 0

    def test_calculate_dimension_importance(self, multi_quantizer, sample_dataframe):
        """测试计算维度重要性"""
        importance = multi_quantizer.calculate_dimension_importance(sample_dataframe)
        assert isinstance(importance, dict)
        total_weight = sum(importance.values())
        assert abs(total_weight - 1.0) < 0.01 or total_weight == 0

    def test_create_quantization_vector(self, multi_quantizer, sample_dataframe):
        """测试创建量化向量"""
        vector = multi_quantizer.create_quantization_vector(sample_dataframe)
        assert isinstance(vector, np.ndarray)
        assert len(vector) == len(DimensionType)

    def test_compare_dimensions(self, multi_quantizer):
        """测试比较两个数据集"""
        df1 = pd.DataFrame({
            "value": np.random.randn(100),
            "text": [f"text_{i}" for i in range(100)],
        })
        df2 = pd.DataFrame({
            "value": np.random.randn(100) * 2,
            "text": [f"text_{i}" for i in range(100)],
        })
        diff = multi_quantizer.compare_dimensions(df1, df2)
        assert isinstance(diff, dict)


class TestYinYangModel:
    """测试两仪模型"""

    @pytest.fixture
    def model(self):
        """创建两仪模型实例"""
        return YinYangModel()

    @pytest.fixture
    def sample_dataframe(self):
        """创建测试DataFrame"""
        return pd.DataFrame({
            "id": range(100),
            "name": [f"item_{i}" for i in range(100)],
            "value": np.random.randn(100),
            "category": np.random.choice(["A", "B", "C", "D"], 100),
            "price": np.random.uniform(10, 1000, 100),
            "rating": np.random.uniform(1, 5, 100),
            "created_at": pd.date_range("2024-01-01", periods=100, freq="D"),
        })

    def test_model_initialization(self, model):
        """测试模型初始化"""
        assert model is not None
        assert model.config is not None

    def test_generate_yin_yang(self, model, sample_dataframe):
        """测试生成两仪状态"""
        state = model.generate_yin_yang(sample_dataframe)
        assert state is not None
        assert 0 <= state.yin_score <= 1
        assert 0 <= state.yang_score <= 1
        assert -1 <= state.balance <= 1

    def test_generate_from_quantization(self, model, sample_dataframe):
        """测试从量化结果生成两仪状态"""
        quantizer = DimensionQuantizer()
        results = quantizer.quantize_dataframe(sample_dataframe)
        quant_dict = {k: v.to_dict() for k, v in results.items()}
        state = model.generate_from_quantization(quant_dict)
        assert state is not None

    def test_generate_yin_yang_with_mass_energy(self, model, sample_dataframe):
        """测试带质能模型的两仪生成"""
        mass_energy = DataMassEnergy(
            data_mass=100.0,
            data_energy=50.0,
            quality_factor=0.8,
            density=60.0,
            entropy=3.0,
        )
        state = model.generate_yin_yang(sample_dataframe, mass_energy=mass_energy)
        assert state.mass_energy_ratio == 0.5
        assert state.singularity_risk > 0

    def test_generate_yin_yang_with_assessment(self, model, sample_dataframe):
        """测试带质量评估的两仪生成"""
        metrics = [
            QualityMetric(
                metric_type=QualityMetricType.COMPLETENESS,
                score=0.9,
            ),
            QualityMetric(
                metric_type=QualityMetricType.CONSISTENCY,
                score=0.85,
            ),
        ]
        assessment = QualityAssessment(metrics=metrics, record_count=100)
        state = model.generate_yin_yang(sample_dataframe, assessment=assessment)
        assert state is not None

    def test_predict_transition(self, model, sample_dataframe):
        """测试预测阴阳转换"""
        state = model.generate_yin_yang(sample_dataframe)
        transition = model.predict_transition(state, entropy_change=0.5)
        assert transition is not None
        assert transition.from_state == state.state_label

    def test_generate_yin_yang_report(self, model, sample_dataframe):
        """测试生成两仪分析报告"""
        state = model.generate_yin_yang(sample_dataframe)
        report = model.generate_yin_yang_report(state, sample_dataframe)
        assert "state" in report
        assert "interpretation" in report
        assert "dimensions" in report
        assert "recommendations" in report

    def test_state_dominance(self, model):
        """测试状态主导性"""
        state = model.generate_yin_yang(
            pd.DataFrame({
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
            })
        )
        assert state.dominance in ["yin", "yang", "balanced"]


class TestYinYangEvolution:
    """测试两仪演化分析器"""

    @pytest.fixture
    def evolution(self):
        """创建演化分析器实例"""
        return YinYangEvolution()

    def test_evolution_initialization(self, evolution):
        """测试演化分析器初始化"""
        assert evolution is not None
        assert evolution.model is not None

    def test_analyze_evolution(self, evolution):
        """测试分析演化轨迹"""
        df_sequence = [
            pd.DataFrame({
                "value": np.random.randn(50),
                "category": np.random.choice(["A", "B", "C"], 50),
            })
            for _ in range(3)
        ]
        result = evolution.analyze_evolution(df_sequence)
        assert "states" in result
        assert "transitions" in result
        assert "trend" in result


class TestEntropyAuditor:
    """测试熵数据审查器"""

    @pytest.fixture
    def auditor(self):
        """创建审查器实例"""
        return EntropyAuditor()

    @pytest.fixture
    def sample_dataframe(self):
        """创建测试DataFrame"""
        return pd.DataFrame({
            "id": range(100),
            "name": [f"item_{i}" for i in range(100)],
            "value": np.random.randn(100),
            "category": np.random.choice(["A", "B", "C", "D"], 100),
            "price": np.random.uniform(10, 1000, 100),
            "text": ["This is a sample text"] * 100,
        })

    def test_auditor_initialization(self, auditor):
        """测试审查器初始化"""
        assert auditor is not None
        assert auditor.config is not None

    def test_audit(self, auditor, sample_dataframe):
        """测试执行熵审查"""
        result = auditor.audit(sample_dataframe)
        assert result is not None
        assert result.overall_entropy >= 0
        assert 0 <= result.quality_score <= 1
        assert result.risk_level in ["low", "medium", "high"]

    def test_audit_empty_dataframe(self, auditor):
        """测试空数据集审查"""
        result = auditor.audit(pd.DataFrame())
        assert result is not None
        assert "空数据集" in result.recommendations[0]

    def test_generate_audit_report(self, auditor, sample_dataframe):
        """测试生成审查报告"""
        result = auditor.audit(sample_dataframe)
        report = auditor.generate_audit_report(result, sample_dataframe)
        assert "audit_result" in report
        assert "entropy_analysis" in report
        assert "field_analysis" in report
        assert "risk_analysis" in report

    def test_analyze_entropy_evolution(self, auditor):
        """测试分析熵演变轨迹"""
        df_sequence = [
            pd.DataFrame({
                "value": np.random.randn(50),
                "category": np.random.choice(["A", "B", "C"], 50),
            })
            for _ in range(3)
        ]
        result = auditor.analyze_entropy_evolution(df_sequence)
        assert "evolution_points" in result
        assert "trend" in result
        assert "summary" in result

    def test_field_entropies(self, auditor, sample_dataframe):
        """测试字段熵计算"""
        entropies = auditor._calculate_field_entropies(sample_dataframe)
        assert isinstance(entropies, dict)
        assert len(entropies) == len(sample_dataframe.columns)

    def test_record_entropies(self, auditor, sample_dataframe):
        """测试记录熵计算"""
        record_entropies = auditor._calculate_record_entropies(sample_dataframe)
        assert isinstance(record_entropies, dict)


class TestEntropyDrivenQualityAssessor:
    """测试熵驱动的质量评估器"""

    @pytest.fixture
    def assessor(self):
        """创建评估器实例"""
        return EntropyDrivenQualityAssessor()

    @pytest.fixture
    def sample_dataframe(self):
        """创建测试DataFrame"""
        return pd.DataFrame({
            "id": range(50),
            "value": np.random.randn(50),
            "name": [f"name_{i}" for i in range(50)],
        })

    def test_assessor_initialization(self, assessor):
        """测试评估器初始化"""
        assert assessor is not None
        assert assessor.auditor is not None

    def test_assess(self, assessor, sample_dataframe):
        """测试执行评估"""
        result = assessor.assess(sample_dataframe)
        assert "combined_score" in result
        assert "entropy_score" in result
        assert "traditional_score" in result
        assert "quality_level" in result

    def test_assess_with_traditional(self, assessor, sample_dataframe):
        """测试结合传统评估的评估"""
        metrics = [
            QualityMetric(
                metric_type=QualityMetricType.COMPLETENESS,
                score=0.9,
            ),
        ]
        assessment = QualityAssessment(metrics=metrics, record_count=50)
        result = assessor.assess(sample_dataframe, assessment=assessment)
        assert result["traditional_score"] == 0.9


class TestH5DataExtractor:
    """测试HDF5数据提取器"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return H5DataExtractor()

    @pytest.fixture
    def temp_h5_file(self):
        """创建临时HDF5文件"""
        import h5py

        fd, path = tempfile.mkstemp(suffix=".h5")
        os.close(fd)

        with h5py.File(path, "w") as f:
            f.create_dataset("dataset1", data=np.random.randn(100))
            f.create_dataset("dataset2", data=np.random.randn(50, 10))
            f.create_dataset("string_dataset", data=[f"text_{i}" for i in range(20)])
            f.create_group("group1")
            f["group1"].create_dataset("nested_dataset", data=np.arange(30))

        yield path

        if os.path.exists(path):
            os.remove(path)

    def test_extractor_initialization(self, extractor):
        """测试提取器初始化"""
        assert extractor is not None

    def test_extract_h5_structure(self, extractor, temp_h5_file):
        """测试提取HDF5结构"""
        structure = extractor.extract_h5_structure(temp_h5_file)
        assert "file_name" in structure
        assert "datasets" in structure
        assert "groups" in structure
        assert len(structure["datasets"]) >= 3

    def test_extract_dataset_data(self, extractor, temp_h5_file):
        """测试提取数据集内容"""
        data = extractor.extract_dataset_data(temp_h5_file, "/dataset1")
        assert data is not None
        assert "path" in data
        assert "shape" in data
        assert "preview" in data

    def test_extract_all_preview_data(self, extractor, temp_h5_file):
        """测试提取所有预览数据"""
        data = extractor.extract_all_preview_data(temp_h5_file)
        assert "structure" in data
        assert "datasets" in data


class TestH5JSPreviewGenerator:
    """测试HDF5 JS预览生成器"""

    @pytest.fixture
    def generator(self):
        """创建生成器实例"""
        return H5JSPreviewGenerator()

    @pytest.fixture
    def temp_h5_file(self):
        """创建临时HDF5文件"""
        import h5py

        fd, path = tempfile.mkstemp(suffix=".h5")
        os.close(fd)

        with h5py.File(path, "w") as f:
            f.create_dataset("simple_data", data=np.random.randn(50))
            f.create_dataset("matrix_data", data=np.random.randn(20, 5))

        yield path

        if os.path.exists(path):
            os.remove(path)

    def test_generator_initialization(self, generator):
        """测试生成器初始化"""
        assert generator is not None

    def test_generate_preview(self, generator, temp_h5_file):
        """测试生成预览"""
        result = generator.generate_preview(temp_h5_file)
        assert result is not None
        assert len(result.html_content) > 0
        assert "<!DOCTYPE html>" in result.html_content
        assert "HDF5" in result.html_content

    def test_generate_preview_for_data(self, generator):
        """测试为已有数据生成预览"""
        data = {
            "structure": {
                "file_name": "test.h5",
                "file_size": 1000,
                "datasets": [],
                "groups": [],
            },
            "datasets": {},
        }
        result = generator.generate_preview_for_data(data)
        assert result is not None
        assert len(result.html_content) > 0


class TestH5PreviewManager:
    """测试HDF5预览管理器"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return H5PreviewManager()

    @pytest.fixture
    def temp_h5_file(self):
        """创建临时HDF5文件"""
        import h5py

        fd, path = tempfile.mkstemp(suffix=".h5")
        os.close(fd)

        with h5py.File(path, "w") as f:
            f.create_dataset("data", data=np.arange(100))
            f.create_group("test_group")
            f["test_group"].create_dataset("nested", data=[1, 2, 3])

        yield path

        if os.path.exists(path):
            os.remove(path)

    def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        assert manager is not None

    def test_create_preview(self, manager, temp_h5_file, test_output_dir):
        """测试创建预览"""
        output_path = str(test_output_dir / "test_preview.html")
        result = manager.create_preview(temp_h5_file, output_path)
        assert result is not None
        assert os.path.exists(output_path)

    def test_get_h5_summary(self, manager, temp_h5_file):
        """测试获取HDF5摘要"""
        summary = manager.get_h5_summary(temp_h5_file)
        assert "file_name" in summary
        assert "dataset_count" in summary
        assert "group_count" in summary

    def test_extract_and_preview(self, manager, temp_h5_file):
        """测试提取并生成预览"""
        data, result = manager.extract_and_preview(temp_h5_file)
        assert data is not None
        assert result is not None


class TestIntegrationNewModules:
    """新模块集成测试"""

    def test_full_dimension_workflow(self):
        """测试完整维度工作流"""
        df = pd.DataFrame({
            "id": range(100),
            "name": [f"product_{i}" for i in range(100)],
            "price": np.random.uniform(10, 1000, 100),
            "category": np.random.choice(["A", "B", "C"], 100),
            "created_at": pd.date_range("2024-01-01", periods=100, freq="D"),
            "rating": np.random.uniform(1, 5, 100),
            "description": ["Product description"] * 100,
        })

        quantizer = DimensionQuantizer()
        quantization_results = quantizer.quantize_dataframe(df)
        assert len(quantization_results) > 0

        yin_yang_model = YinYangModel()
        yin_yang_state = yin_yang_model.generate_yin_yang(df)
        assert yin_yang_state is not None

        auditor = EntropyAuditor()
        audit_result = auditor.audit(df)
        assert audit_result is not None

        assessor = EntropyDrivenQualityAssessor()
        quality_result = assessor.assess(df)
        assert quality_result is not None

    def test_h5_preview_workflow(self):
        """测试HDF5预览工作流"""
        import h5py

        fd, path = tempfile.mkstemp(suffix=".h5")
        os.close(fd)

        try:
            with h5py.File(path, "w") as f:
                f.create_dataset("timeseries", data=np.random.randn(100))
                f.create_dataset("matrix", data=np.random.randn(50, 10))
                f.create_dataset("labels", data=[f"label_{i}" for i in range(50)])

            manager = H5PreviewManager()
            summary = manager.get_h5_summary(path)
            assert summary["dataset_count"] >= 3

            data, preview = manager.extract_and_preview(path)
            assert data is not None
            assert preview is not None
            assert len(preview.html_content) > 0

        finally:
            if os.path.exists(path):
                os.remove(path)