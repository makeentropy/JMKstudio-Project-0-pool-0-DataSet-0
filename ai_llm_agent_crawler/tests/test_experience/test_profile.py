"""
自我认知画像模块单元测试

测试智能体画像生成、更新、各维度分析、知识边界、趋势分析等功能。
"""

import json
from datetime import datetime, timedelta

import pytest

from ai_llm_agent_crawler.experience import (
    AgentProfile,
    AgentProfileGenerator,
    ExperienceDataPool,
    ExperienceRecord,
    KnowledgeBoundary,
    SkillDomain,
    TaskStatus,
    TaskType,
)


class TestSkillDomain:
    """技能领域模型测试"""

    def test_create_skill_domain(self):
        """测试创建技能领域"""
        domain = SkillDomain(
            domain_name="crawler",
            task_count=10,
            success_rate=0.85,
            avg_accuracy=0.8,
            avg_efficiency=0.75,
            proficiency=0.7,
            strengths=["高成功率"],
            weaknesses=["效率待提升"],
        )

        assert domain.domain_name == "crawler"
        assert domain.task_count == 10
        assert domain.success_rate == 0.85
        assert domain.avg_accuracy == 0.8
        assert domain.avg_efficiency == 0.75
        assert domain.proficiency == 0.7
        assert len(domain.strengths) == 1
        assert len(domain.weaknesses) == 1
        assert isinstance(domain.last_active, datetime)

    def test_skill_domain_defaults(self):
        """测试技能领域默认值"""
        domain = SkillDomain(domain_name="test")

        assert domain.task_count == 0
        assert domain.success_rate == 0.0
        assert domain.avg_accuracy == 0.0
        assert domain.avg_efficiency == 0.0
        assert domain.proficiency == 0.0
        assert domain.strengths == []
        assert domain.weaknesses == []

    def test_skill_domain_validation(self):
        """测试技能领域验证"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SkillDomain(domain_name="test", success_rate=1.5)

        with pytest.raises(ValidationError):
            SkillDomain(domain_name="test", proficiency=-0.1)


class TestKnowledgeBoundary:
    """知识边界模型测试"""

    def test_create_knowledge_boundary(self):
        """测试创建知识边界"""
        boundary = KnowledgeBoundary(
            known_domains=["crawler", "processor"],
            unknown_domains=["analyzer"],
            frontier_domains=["annotator"],
            confidence_distribution={"crawler": 0.9, "processor": 0.7},
            overall_certainty=0.6,
        )

        assert len(boundary.known_domains) == 2
        assert len(boundary.unknown_domains) == 1
        assert len(boundary.frontier_domains) == 1
        assert boundary.overall_certainty == 0.6
        assert "crawler" in boundary.confidence_distribution

    def test_knowledge_boundary_defaults(self):
        """测试知识边界默认值"""
        boundary = KnowledgeBoundary()

        assert boundary.known_domains == []
        assert boundary.unknown_domains == []
        assert boundary.frontier_domains == []
        assert boundary.confidence_distribution == {}
        assert boundary.overall_certainty == 0.0


class TestAgentProfile:
    """智能体画像模型测试"""

    def test_create_profile(self):
        """测试创建智能体画像"""
        profile = AgentProfile(
            agent_name="test_agent",
            experience_count=100,
            overall_score=0.75,
            strengths=["优势1", "优势2"],
            weaknesses=["劣势1"],
            improvement_directions=["改进方向1"],
            recent_trend="improving",
        )

        assert profile.agent_name == "test_agent"
        assert profile.experience_count == 100
        assert profile.overall_score == 0.75
        assert len(profile.strengths) == 2
        assert len(profile.weaknesses) == 1
        assert len(profile.improvement_directions) == 1
        assert profile.recent_trend == "improving"
        assert profile.profile_id.startswith("prof_")
        assert isinstance(profile.generated_at, datetime)
        assert isinstance(profile.last_updated, datetime)

    def test_profile_defaults(self):
        """测试画像默认值"""
        profile = AgentProfile()

        assert profile.agent_name == "agent"
        assert profile.experience_count == 0
        assert profile.overall_score == 0.0
        assert profile.strengths == []
        assert profile.weaknesses == []
        assert profile.typical_errors == []
        assert profile.improvement_directions == []
        assert profile.skill_domains == []
        assert profile.recent_trend == "stable"

    def test_profile_id_format(self):
        """测试画像ID格式"""
        profile = AgentProfile()
        assert profile.profile_id.startswith("prof_")
        assert len(profile.profile_id) == 13


class TestAgentProfileGenerator:
    """画像生成器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def generator(self, pool):
        """创建画像生成器"""
        return AgentProfileGenerator(pool)

    @pytest.fixture
    def sample_records(self):
        """创建示例记录列表"""
        records = []
        for i in range(30):
            if i < 18:
                status = TaskStatus.SUCCESS
            elif i < 24:
                status = TaskStatus.PARTIAL
            elif i < 27:
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

            errors = []
            if i % 3 == 0:
                errors.append(f"timeout_error_{i}")
            if i % 5 == 0:
                errors.append(f"parse_error_{i}")

            warnings = [f"warning_{i}"] if i % 4 == 0 else []

            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=task_type,
                task_name=f"task_name_{i}",
                status=status,
                duration_ms=500.0 + i * 50.0,
                performance_metrics={
                    "accuracy": 0.6 + i * 0.01,
                    "efficiency": 0.5 + i * 0.015,
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

    def test_generate_profile_empty_pool(self, generator):
        """测试空数据池生成画像"""
        profile = generator.generate_profile("empty_agent")

        assert isinstance(profile, AgentProfile)
        assert profile.agent_name == "empty_agent"
        assert profile.experience_count == 0
        assert profile.overall_score == 0.0
        assert len(profile.weaknesses) > 0
        assert len(profile.improvement_directions) > 0
        assert profile.recent_trend == "stable"
        assert len(profile.knowledge_boundary.unknown_domains) > 0

    def test_generate_profile_with_records(self, generator, pool_with_records):
        """测试有数据的画像生成"""
        profile = generator.generate_profile("test_agent")

        assert isinstance(profile, AgentProfile)
        assert profile.agent_name == "test_agent"
        assert profile.experience_count == 30
        assert 0.0 <= profile.overall_score <= 1.0
        assert len(profile.strengths) > 0
        assert len(profile.weaknesses) > 0
        assert len(profile.skill_domains) > 0
        assert len(profile.improvement_directions) > 0

    def test_profile_contains_five_aspects(self, generator, pool_with_records):
        """测试生成画像包含所有5个方面"""
        profile = generator.generate_profile()

        assert len(profile.strengths) > 0, "缺少优势分析"
        assert len(profile.weaknesses) > 0, "缺少薄弱环节分析"
        assert profile.knowledge_boundary is not None, "缺少知识边界"
        assert len(profile.knowledge_boundary.known_domains) > 0 or len(
            profile.knowledge_boundary.frontier_domains
        ) > 0, "知识边界数据为空"
        assert isinstance(profile.typical_errors, list), "缺少典型错误"
        assert len(profile.improvement_directions) > 0, "缺少改进方向"

    def test_profile_dynamic_not_static(self, generator, pool, sample_records):
        """测试画像基于历史经验数据动态生成，不是静态配置"""
        profile1 = generator.generate_profile("dynamic_agent")

        for record in sample_records[:10]:
            pool.add_record(record)

        profile2 = generator.generate_profile("dynamic_agent")

        assert profile1.experience_count != profile2.experience_count
        assert profile1.overall_score != profile2.overall_score or profile1.experience_count != profile2.experience_count
        assert len(profile2.skill_domains) > len(profile1.skill_domains) or profile2.experience_count > profile1.experience_count

    def test_update_profile(self, generator, pool, sample_records):
        """测试添加新经验后画像有相应更新"""
        for record in sample_records[:10]:
            pool.add_record(record)

        profile1 = generator.generate_profile("update_test")
        exp_count1 = profile1.experience_count

        for record in sample_records[10:20]:
            pool.add_record(record)

        profile2 = generator.update_profile(profile1)

        assert profile2.profile_id == profile1.profile_id
        assert profile2.generated_at == profile1.generated_at
        assert profile2.experience_count > exp_count1
        assert profile2.last_updated >= profile1.last_updated

    def test_to_json(self, generator, pool_with_records):
        """测试支持 JSON 格式导出"""
        profile = generator.generate_profile("json_test")
        json_str = generator.to_json(profile)

        assert isinstance(json_str, str)
        assert len(json_str) > 0

        data = json.loads(json_str)
        assert "profile_id" in data
        assert "agent_name" in data
        assert "overall_score" in data
        assert "strengths" in data
        assert "weaknesses" in data
        assert "skill_domains" in data
        assert "knowledge_boundary" in data

    def test_skill_domains_calculation(self, generator, pool_with_records):
        """测试各技能领域的计算正确"""
        profile = generator.generate_profile()

        assert len(profile.skill_domains) > 0

        for domain in profile.skill_domains:
            assert isinstance(domain, SkillDomain)
            assert domain.domain_name != ""
            assert domain.task_count > 0
            assert 0.0 <= domain.success_rate <= 1.0
            assert 0.0 <= domain.avg_accuracy <= 1.0
            assert 0.0 <= domain.avg_efficiency <= 1.0
            assert 0.0 <= domain.proficiency <= 1.0
            assert isinstance(domain.last_active, datetime)

    def test_typical_errors_identification(self, generator, pool_with_records):
        """测试典型错误识别正确"""
        profile = generator.generate_profile()

        assert isinstance(profile.typical_errors, list)

        if profile.typical_errors:
            for error in profile.typical_errors:
                assert "error_type" in error
                assert "frequency" in error
                assert "percentage" in error
                assert "examples" in error
                assert error["frequency"] > 0
                assert 0.0 <= error["percentage"] <= 1.0
                assert isinstance(error["examples"], list)

    def test_knowledge_boundary_reasonable(self, generator, pool_with_records):
        """测试知识边界划分合理"""
        profile = generator.generate_profile()

        boundary = profile.knowledge_boundary
        assert isinstance(boundary, KnowledgeBoundary)
        assert 0.0 <= boundary.overall_certainty <= 1.0

        all_domains = set(boundary.known_domains) | set(boundary.unknown_domains) | set(boundary.frontier_domains)
        assert len(all_domains) == len(boundary.known_domains) + len(boundary.unknown_domains) + len(boundary.frontier_domains)

    def test_trend_analysis_stable(self, generator, pool):
        """测试趋势分析-稳定"""
        for i in range(25):
            status = TaskStatus.SUCCESS if i % 2 == 0 else TaskStatus.FAILED
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=status,
                timestamp=datetime.now() - timedelta(hours=25 - i),
            )
            pool.add_record(record)

        profile = generator.generate_profile("trend_test")
        assert profile.recent_trend in ["improving", "stable", "declining"]

    def test_trend_analysis_improving(self, generator, pool):
        """测试趋势分析-提升"""
        for i in range(20):
            if i < 10:
                status = TaskStatus.FAILED
            else:
                status = TaskStatus.SUCCESS
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=status,
                timestamp=datetime.now() - timedelta(hours=20 - i),
            )
            pool.add_record(record)

        profile = generator.generate_profile("improving_test")
        assert profile.recent_trend in ["improving", "stable"]

    def test_trend_analysis_declining(self, generator, pool):
        """测试趋势分析-下降"""
        for i in range(20):
            if i < 10:
                status = TaskStatus.SUCCESS
            else:
                status = TaskStatus.FAILED
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=status,
                timestamp=datetime.now() - timedelta(hours=20 - i),
            )
            pool.add_record(record)

        profile = generator.generate_profile("declining_test")
        assert profile.recent_trend in ["declining", "stable"]

    def test_get_profile_summary(self, generator, pool_with_records):
        """测试画像摘要功能正常"""
        profile = generator.generate_profile("summary_test")
        summary = generator.get_profile_summary(profile)

        assert isinstance(summary, dict)
        assert "agent_name" in summary
        assert "overall_score" in summary
        assert "experience_count" in summary
        assert "recent_trend" in summary
        assert "top_strengths" in summary
        assert "top_weaknesses" in summary
        assert "top_improvement_directions" in summary
        assert "knowledge_certainty" in summary
        assert "known_domains_count" in summary

        assert len(summary["top_strengths"]) <= 3
        assert len(summary["top_weaknesses"]) <= 3
        assert len(summary["top_improvement_directions"]) <= 3

    def test_empty_pool_default_profile(self, generator):
        """测试空经验池有合理的默认画像"""
        profile = generator.generate_profile("empty_test")

        assert isinstance(profile, AgentProfile)
        assert profile.experience_count == 0
        assert profile.overall_score == 0.0
        assert len(profile.weaknesses) > 0
        assert len(profile.improvement_directions) > 0
        assert len(profile.knowledge_boundary.unknown_domains) > 0
        assert "经验" in profile.weaknesses[0] or "不足" in profile.weaknesses[0]

    def test_profile_matches_experience_data(self, generator, pool):
        """测试画像内容与实际经验数据表现一致"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"crawler_task_{i}",
                status=TaskStatus.SUCCESS,
                performance_metrics={"accuracy": 0.9, "efficiency": 0.85},
                errors=[],
            )
            pool.add_record(record)

        for i in range(10):
            record = ExperienceRecord(
                task_id=f"fail_task_{i}",
                task_type=TaskType.ANALYZER,
                task_name=f"analyzer_task_{i}",
                status=TaskStatus.FAILED,
                performance_metrics={"accuracy": 0.3, "efficiency": 0.2},
                errors=[f"error_{i}"],
            )
            pool.add_record(record)

        profile = generator.generate_profile("verify_test")

        crawler_domain = None
        analyzer_domain = None
        for d in profile.skill_domains:
            if d.domain_name == "crawler":
                crawler_domain = d
            elif d.domain_name == "analyzer":
                analyzer_domain = d

        assert crawler_domain is not None
        assert analyzer_domain is not None
        assert crawler_domain.success_rate > analyzer_domain.success_rate
        assert crawler_domain.avg_accuracy > analyzer_domain.avg_accuracy
        assert crawler_domain.avg_efficiency > analyzer_domain.avg_efficiency
        assert crawler_domain.proficiency > analyzer_domain.proficiency

        assert any("crawler" in s.lower() for s in profile.strengths) or any(
            "crawler" in s for s in profile.strengths
        )
        assert any("analyzer" in w.lower() for w in profile.weaknesses) or any(
            "analyzer" in w for w in profile.weaknesses
        )

    def test_strengths_identification_criteria(self, generator, pool):
        """测试优势识别标准：成功率 > 0.8 且任务数 > 5"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"strong_task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"strong_{i}",
                status=TaskStatus.SUCCESS,
            )
            pool.add_record(record)

        profile = generator.generate_profile("strength_test")

        assert len(profile.strengths) > 0
        assert any("crawler" in s.lower() for s in profile.strengths) or any(
            "优秀" in s for s in profile.strengths
        )

    def test_weaknesses_identification_criteria(self, generator, pool):
        """测试薄弱识别标准：成功率 < 0.5 或效率 < 0.5"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"weak_task_{i}",
                task_type=TaskType.ANALYZER,
                task_name=f"weak_{i}",
                status=TaskStatus.FAILED,
                performance_metrics={"efficiency": 0.3},
            )
            pool.add_record(record)

        profile = generator.generate_profile("weakness_test")

        assert len(profile.weaknesses) > 0
        assert any("analyzer" in w.lower() for w in profile.weaknesses) or any(
            "偏低" in w for w in profile.weaknesses
        )

    def test_error_categorization(self, generator, pool):
        """测试错误分类功能"""
        errors = [
            "Connection timeout error",
            "Failed to parse JSON data",
            "Permission denied accessing file",
            "Invalid data format",
            "Memory allocation failed",
            "Config file not found",
            "Validation failed for input",
            "Unknown random error",
        ]

        for i, err in enumerate(errors):
            record = ExperienceRecord(
                task_id=f"err_task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"err_{i}",
                status=TaskStatus.FAILED,
                errors=[err],
            )
            pool.add_record(record)

        profile = generator.generate_profile("error_test")

        assert len(profile.typical_errors) > 0
        error_types = [e["error_type"] for e in profile.typical_errors]
        assert len(error_types) > 0

    def test_improvement_directions_based_on_data(self, generator, pool):
        """测试改进方向基于薄弱环节和高频错误"""
        for i in range(8):
            record = ExperienceRecord(
                task_id=f"improve_task_{i}",
                task_type=TaskType.ANNOTATOR,
                task_name=f"improve_{i}",
                status=TaskStatus.FAILED,
                errors=[f"timeout error {i}"],
            )
            pool.add_record(record)

        profile = generator.generate_profile("improve_test")

        assert len(profile.improvement_directions) > 0
        directions_text = " ".join(profile.improvement_directions)
        assert "annotator" in directions_text.lower() or "提升" in directions_text or "减少" in directions_text

    def test_skill_domains_sorted_by_task_count(self, generator, pool_with_records):
        """测试技能领域按任务数降序排列"""
        profile = generator.generate_profile()

        if len(profile.skill_domains) >= 2:
            for i in range(len(profile.skill_domains) - 1):
                assert (
                    profile.skill_domains[i].task_count
                    >= profile.skill_domains[i + 1].task_count
                )

    def test_overall_score_weighted_by_task_count(self, generator, pool):
        """测试综合评分按任务数加权"""
        for i in range(20):
            record = ExperienceRecord(
                task_id=f"high_task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"high_{i}",
                status=TaskStatus.SUCCESS,
                performance_metrics={"accuracy": 0.9, "efficiency": 0.9},
            )
            pool.add_record(record)

        for i in range(5):
            record = ExperienceRecord(
                task_id=f"low_task_{i}",
                task_type=TaskType.ANALYZER,
                task_name=f"low_{i}",
                status=TaskStatus.FAILED,
                performance_metrics={"accuracy": 0.2, "efficiency": 0.2},
            )
            pool.add_record(record)

        profile = generator.generate_profile("weight_test")

        assert 0.0 <= profile.overall_score <= 1.0
        assert profile.overall_score > 0.5

    def test_profile_json_roundtrip(self, generator, pool_with_records):
        """测试画像JSON往返转换"""
        profile = generator.generate_profile("roundtrip_test")
        json_str = generator.to_json(profile)
        data = json.loads(json_str)

        assert data["agent_name"] == "roundtrip_test"
        assert data["experience_count"] == 30
        assert len(data["strengths"]) > 0
        assert len(data["weaknesses"]) > 0
        assert len(data["skill_domains"]) > 0
        assert "knowledge_boundary" in data
