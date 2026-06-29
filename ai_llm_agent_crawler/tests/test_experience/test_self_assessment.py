"""
自我评估模块单元测试

测试自我评估器的各维度评分、综合评估、总结生成等功能。
"""

import json
from datetime import datetime, timedelta

import pytest

from ai_llm_agent_crawler.experience import (
    AssessmentDimension,
    DimensionScore,
    ExperienceDataPool,
    ExperienceRecord,
    SelfAssessment,
    SelfAssessmentConfig,
    SelfAssessmentResult,
    TaskStatus,
    TaskType,
)


class TestAssessmentDimension:
    """评估维度枚举测试"""

    def test_dimension_values(self):
        """测试评估维度枚举值"""
        assert AssessmentDimension.ACCURACY == "accuracy"
        assert AssessmentDimension.EFFICIENCY == "efficiency"
        assert AssessmentDimension.COMPLETENESS == "completeness"
        assert AssessmentDimension.RESOURCE_USAGE == "resource_usage"
        assert AssessmentDimension.INNOVATIVENESS == "innovativeness"

    def test_dimension_count(self):
        """测试评估维度数量"""
        assert len(AssessmentDimension) == 5


class TestDimensionScore:
    """维度评分模型测试"""

    def test_create_dimension_score(self):
        """测试创建维度评分"""
        score = DimensionScore(
            dimension=AssessmentDimension.ACCURACY,
            score=0.85,
            weight=0.3,
            evidence=["测试依据1", "测试依据2"],
            confidence=0.9,
        )

        assert score.dimension == AssessmentDimension.ACCURACY
        assert score.score == 0.85
        assert score.weight == 0.3
        assert len(score.evidence) == 2
        assert score.confidence == 0.9

    def test_dimension_score_defaults(self):
        """测试维度评分默认值"""
        score = DimensionScore(
            dimension=AssessmentDimension.EFFICIENCY,
            score=0.7,
            weight=0.25,
        )

        assert score.evidence == []
        assert score.confidence == 0.0

    def test_dimension_score_validation(self):
        """测试维度评分验证"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DimensionScore(
                dimension=AssessmentDimension.ACCURACY,
                score=1.5,
                weight=0.3,
            )

        with pytest.raises(ValidationError):
            DimensionScore(
                dimension=AssessmentDimension.ACCURACY,
                score=0.8,
                weight=-0.1,
            )


class TestSelfAssessmentResult:
    """自我评估结果模型测试"""

    def test_create_result(self):
        """测试创建评估结果"""
        result = SelfAssessmentResult(
            overall_score=0.75,
            experience_count=10,
            summary="测试总结",
            strengths=["优势1"],
            weaknesses=["不足1"],
            recommendations=["建议1"],
        )

        assert result.overall_score == 0.75
        assert result.experience_count == 10
        assert result.summary == "测试总结"
        assert len(result.strengths) == 1
        assert len(result.weaknesses) == 1
        assert len(result.recommendations) == 1
        assert isinstance(result.assessment_time, datetime)

    def test_result_defaults(self):
        """测试评估结果默认值"""
        result = SelfAssessmentResult(overall_score=0.5)

        assert result.dimensions == {}
        assert result.experience_count == 0
        assert result.summary == ""
        assert result.strengths == []
        assert result.weaknesses == []
        assert result.recommendations == []


class TestSelfAssessmentConfig:
    """评估配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SelfAssessmentConfig()

        assert config.weights["accuracy"] == 0.3
        assert config.weights["efficiency"] == 0.25
        assert config.weights["completeness"] == 0.2
        assert config.weights["resource_usage"] == 0.15
        assert config.weights["innovativeness"] == 0.1
        assert config.min_experience_count == 1
        assert config.lookback_days is None
        assert config.success_threshold == 0.7

    def test_custom_config(self):
        """测试自定义配置"""
        config = SelfAssessmentConfig(
            weights={"accuracy": 0.5, "efficiency": 0.5},
            min_experience_count=5,
            lookback_days=30,
            success_threshold=0.8,
        )

        assert config.weights["accuracy"] == 0.5
        assert config.min_experience_count == 5
        assert config.lookback_days == 30
        assert config.success_threshold == 0.8


class TestSelfAssessment:
    """自我评估器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def assessor(self, pool):
        """创建自我评估器"""
        return SelfAssessment(pool)

    @pytest.fixture
    def sample_records(self):
        """创建示例记录列表"""
        records = []
        for i in range(20):
            if i < 12:
                status = TaskStatus.SUCCESS
            elif i < 16:
                status = TaskStatus.PARTIAL
            elif i < 18:
                status = TaskStatus.FAILED
            else:
                status = TaskStatus.SKIPPED

            task_types = [
                TaskType.CRAWLER,
                TaskType.PROCESSOR,
                TaskType.ANALYZER,
                TaskType.ANNOTATOR,
                TaskType.VALIDATOR,
            ]
            task_type = task_types[i % len(task_types)]

            errors = [f"error_{i}"] if i % 4 == 0 else []
            warnings = [f"warning_{i}"] if i % 3 == 0 else []

            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=task_type,
                task_name=f"task_name_{i}",
                status=status,
                duration_ms=500.0 + i * 100.0,
                performance_metrics={
                    "accuracy": 0.6 + i * 0.02,
                    "efficiency": 0.5 + i * 0.025,
                },
                input_summary=f"input_{i}",
                output_summary=f"output_{i}_result",
                errors=errors,
                warnings=warnings,
                metadata={"index": i},
            )
            records.append(record)
        return records

    @pytest.fixture
    def pool_with_records(self, pool, sample_records):
        """创建包含示例记录的数据池"""
        for record in sample_records:
            pool.add_record(record)
        return pool

    def test_assess_empty_pool(self, assessor):
        """测试空数据池评估"""
        result = assessor.assess()

        assert isinstance(result, SelfAssessmentResult)
        assert result.experience_count == 0
        assert result.overall_score == 0.0
        assert "无法进行有效评估" in result.summary
        assert len(result.weaknesses) > 0
        assert len(result.recommendations) > 0

    def test_assess_with_records(self, assessor, pool_with_records):
        """测试有数据的评估"""
        result = assessor.assess()

        assert isinstance(result, SelfAssessmentResult)
        assert result.experience_count == 20
        assert 0.0 <= result.overall_score <= 1.0
        assert len(result.dimensions) == 5
        assert result.summary != ""
        assert len(result.strengths) > 0
        assert len(result.weaknesses) > 0
        assert len(result.recommendations) > 0

    def test_assess_accuracy_dimension(self, assessor, pool_with_records):
        """测试准确性维度评分"""
        experiences = pool_with_records.query({}, limit=100)
        score = assessor.assess_dimension(AssessmentDimension.ACCURACY, experiences)

        assert isinstance(score, DimensionScore)
        assert score.dimension == AssessmentDimension.ACCURACY
        assert 0.0 <= score.score <= 1.0
        assert len(score.evidence) > 0
        assert any("成功" in e for e in score.evidence)
        assert any("成功率" in e for e in score.evidence)
        assert 0.0 <= score.confidence <= 1.0

    def test_assess_efficiency_dimension(self, assessor, pool_with_records):
        """测试效率维度评分"""
        experiences = pool_with_records.query({}, limit=100)
        score = assessor.assess_dimension(AssessmentDimension.EFFICIENCY, experiences)

        assert isinstance(score, DimensionScore)
        assert score.dimension == AssessmentDimension.EFFICIENCY
        assert 0.0 <= score.score <= 1.0
        assert len(score.evidence) > 0
        assert any("耗时" in e for e in score.evidence)
        assert 0.0 <= score.confidence <= 1.0

    def test_assess_completeness_dimension(self, assessor, pool_with_records):
        """测试完整性维度评分"""
        experiences = pool_with_records.query({}, limit=100)
        score = assessor.assess_dimension(AssessmentDimension.COMPLETENESS, experiences)

        assert isinstance(score, DimensionScore)
        assert score.dimension == AssessmentDimension.COMPLETENESS
        assert 0.0 <= score.score <= 1.0
        assert len(score.evidence) > 0
        assert any("完成率" in e for e in score.evidence)
        assert 0.0 <= score.confidence <= 1.0

    def test_assess_resource_usage_dimension(self, assessor, pool_with_records):
        """测试资源使用率维度评分"""
        experiences = pool_with_records.query({}, limit=100)
        score = assessor.assess_dimension(AssessmentDimension.RESOURCE_USAGE, experiences)

        assert isinstance(score, DimensionScore)
        assert score.dimension == AssessmentDimension.RESOURCE_USAGE
        assert 0.0 <= score.score <= 1.0
        assert len(score.evidence) > 0
        assert any("资源" in e for e in score.evidence)
        assert 0.0 <= score.confidence <= 1.0

    def test_assess_innovativeness_dimension(self, assessor, pool_with_records):
        """测试创新性维度评分"""
        experiences = pool_with_records.query({}, limit=100)
        score = assessor.assess_dimension(AssessmentDimension.INNOVATIVENESS, experiences)

        assert isinstance(score, DimensionScore)
        assert score.dimension == AssessmentDimension.INNOVATIVENESS
        assert 0.0 <= score.score <= 1.0
        assert len(score.evidence) > 0
        assert any("任务类型" in e for e in score.evidence)
        assert 0.0 <= score.confidence <= 1.0

    def test_overall_score_weighted_correctly(self, assessor, pool_with_records):
        """测试综合评分加权计算正确"""
        result = assessor.assess()

        expected_sum = 0.0
        total_weight = 0.0
        for dim_name, dim_score in result.dimensions.items():
            expected_sum += dim_score.score * dim_score.weight
            total_weight += dim_score.weight

        expected_overall = expected_sum / total_weight if total_weight > 0 else 0.0
        assert abs(result.overall_score - expected_overall) < 0.001

    def test_evidence_not_empty(self, assessor, pool_with_records):
        """测试评分依据不为空"""
        result = assessor.assess()

        for dim_name, dim_score in result.dimensions.items():
            assert len(dim_score.evidence) > 0, f"{dim_name} 的评分依据为空"
            for ev in dim_score.evidence:
                assert isinstance(ev, str)
                assert len(ev) > 0

    def test_custom_weights_change_overall_score(self, pool, pool_with_records):
        """测试修改权重后综合评分按预期变化"""
        config1 = SelfAssessmentConfig(
            weights={"accuracy": 1.0, "efficiency": 0.0, "completeness": 0.0, "resource_usage": 0.0, "innovativeness": 0.0}
        )
        assessor1 = SelfAssessment(pool, config1)
        result1 = assessor1.assess()

        config2 = SelfAssessmentConfig(
            weights={"accuracy": 0.0, "efficiency": 0.0, "completeness": 0.0, "resource_usage": 0.0, "innovativeness": 1.0}
        )
        assessor2 = SelfAssessment(pool, config2)
        result2 = assessor2.assess()

        accuracy_score = result1.dimensions["accuracy"].score
        innovativeness_score = result2.dimensions["innovativeness"].score

        assert abs(result1.overall_score - accuracy_score) < 0.001
        assert abs(result2.overall_score - innovativeness_score) < 0.001

    def test_min_experience_count_config(self, pool):
        """测试最少经验数量配置"""
        config = SelfAssessmentConfig(min_experience_count=5)
        assessor = SelfAssessment(pool, config)

        for i in range(3):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=TaskStatus.SUCCESS,
            )
            pool.add_record(record)

        result = assessor.assess()
        assert result.overall_score == 0.0
        assert "无法进行有效评估" in result.summary

    def test_assess_with_filters(self, assessor, pool_with_records):
        """测试不同过滤条件下的评估"""
        result_all = assessor.assess()
        result_crawler = assessor.assess({"task_type": "crawler"})
        result_success = assessor.assess({"status": "success"})

        assert result_all.experience_count == 20
        assert result_crawler.experience_count == 4
        assert result_success.experience_count == 12

        assert result_crawler.overall_score != result_all.overall_score or result_crawler.experience_count != result_all.experience_count

    def test_strengths_and_weaknesses_generation(self, assessor, pool_with_records):
        """测试优势和不足列表生成正确"""
        result = assessor.assess()

        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
        assert len(result.strengths) >= 1
        assert len(result.weaknesses) >= 1

        for s in result.strengths:
            assert isinstance(s, str)
            assert len(s) > 0

        for w in result.weaknesses:
            assert isinstance(w, str)
            assert len(w) > 0

    def test_recommendations_generation(self, assessor, pool_with_records):
        """测试改进建议列表生成正确"""
        result = assessor.assess()

        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) >= 1

        for r in result.recommendations:
            assert isinstance(r, str)
            assert len(r) > 0

    def test_assess_dimension_empty_list(self, assessor):
        """测试空经验列表的维度评分"""
        score = assessor.assess_dimension(AssessmentDimension.ACCURACY, [])

        assert score.score == 0.0
        assert len(score.evidence) > 0
        assert "无经验数据" in score.evidence[0]

    def test_historical_assessment_empty(self, assessor):
        """测试空历史评估"""
        history = assessor.get_historical_assessment()
        assert isinstance(history, list)
        assert len(history) == 0

    def test_historical_assessment_with_data(self, assessor, pool_with_records):
        """测试有数据的历史评估"""
        assessor.assess()
        assessor.assess({"task_type": "crawler"})

        history = assessor.get_historical_assessment(days=30)
        assert isinstance(history, list)
        assert len(history) >= 1

        for entry in history:
            assert "date" in entry
            assert "overall_score" in entry
            assert "experience_count" in entry
            assert "assessment_count" in entry
            assert 0.0 <= entry["overall_score"] <= 1.0

    def test_result_json_serializable(self, assessor, pool_with_records):
        """测试评估结果可序列化为 JSON"""
        result = assessor.assess()

        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        data = json.loads(json_str)
        assert "overall_score" in data
        assert "dimensions" in data
        assert "experience_count" in data
        assert "summary" in data
        assert "strengths" in data
        assert "weaknesses" in data
        assert "recommendations" in data

    def test_lookback_days_config(self, pool):
        """测试回顾天数配置"""
        now = datetime.now()

        old_record = ExperienceRecord(
            task_id="old_task",
            task_type=TaskType.CRAWLER,
            task_name="old",
            status=TaskStatus.SUCCESS,
            timestamp=now - timedelta(days=60),
        )
        new_record = ExperienceRecord(
            task_id="new_task",
            task_type=TaskType.PROCESSOR,
            task_name="new",
            status=TaskStatus.SUCCESS,
            timestamp=now - timedelta(days=1),
        )

        pool.add_record(old_record)
        pool.add_record(new_record)

        config = SelfAssessmentConfig(lookback_days=7)
        assessor = SelfAssessment(pool, config)

        result = assessor.assess()
        assert result.experience_count == 1

    def test_all_five_dimensions_present(self, assessor, pool_with_records):
        """测试所有5个维度都在结果中"""
        result = assessor.assess()

        expected_dims = {
            "accuracy",
            "efficiency",
            "completeness",
            "resource_usage",
            "innovativeness",
        }
        assert set(result.dimensions.keys()) == expected_dims

    def test_high_performance_records(self, pool):
        """测试高表现记录的评估"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"high_perf_{i}",
                status=TaskStatus.SUCCESS,
                duration_ms=100.0,
                performance_metrics={"accuracy": 0.95, "efficiency": 0.9},
                output_summary=f"complete_output_{i}",
                errors=[],
                warnings=[],
            )
            pool.add_record(record)

        assessor = SelfAssessment(pool)
        result = assessor.assess()

        assert result.overall_score > 0.6
        assert result.dimensions["accuracy"].score > 0.7

    def test_low_performance_records(self, pool):
        """测试低表现记录的评估"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"low_perf_{i}",
                status=TaskStatus.FAILED,
                duration_ms=20000.0,
                performance_metrics={"accuracy": 0.2, "efficiency": 0.1},
                output_summary="",
                errors=[f"err1_{i}", f"err2_{i}", f"err3_{i}"],
                warnings=[f"warn1_{i}", f"warn2_{i}"],
            )
            pool.add_record(record)

        assessor = SelfAssessment(pool)
        result = assessor.assess()

        assert result.overall_score < 0.5
        assert result.dimensions["accuracy"].score < 0.4

    def test_summary_contains_level_description(self, assessor, pool_with_records):
        """测试总结包含等级描述"""
        result = assessor.assess()

        level_words = ["优秀", "良好", "中等", "一般", "较差"]
        assert any(word in result.summary for word in level_words)
        assert str(result.experience_count) in result.summary
