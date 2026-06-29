"""
自反思智能体集成测试

测试 IntrospectiveAgent 的所有核心功能。
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from ai_llm_agent_crawler.experience import (
    AgentProfile,
    ExperienceDataPool,
    ExperienceRecord,
    IntrospectiveAgent,
    TaskStatus,
    TaskType,
)


class TestIntrospectiveAgentInit:
    """IntrospectiveAgent 初始化测试"""

    def test_init_defaults(self):
        """测试默认初始化"""
        agent = IntrospectiveAgent()

        assert agent is not None
        assert agent._agent_name == "introspective_agent"
        assert agent._storage_path is None
        assert isinstance(agent.pool, ExperienceDataPool)
        assert agent.snapshot_manager is not None
        assert agent.self_assessment is not None
        assert agent.error_attributor is not None
        assert agent.experience_summarizer is not None
        assert agent.profile_generator is not None
        assert agent.iteration_engine is not None
        assert agent.trend_analyzer is not None
        assert agent.pattern_miner is not None
        assert agent.comparator is not None
        assert agent.dimension_probe is None

    def test_init_with_custom_name(self):
        """测试自定义名称初始化"""
        agent = IntrospectiveAgent(agent_name="test_agent")
        assert agent._agent_name == "test_agent"

    def test_init_with_storage_path(self):
        """测试带存储路径初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = IntrospectiveAgent(storage_path=tmpdir)
            assert agent._storage_path == tmpdir
            assert agent.pool is not None

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {"some_key": "some_value"}
        agent = IntrospectiveAgent(config=config)
        assert agent._config == config

    def test_init_with_dimension_probe_enabled(self):
        """测试启用维度空间探针"""
        config = {"enable_dimension_probe": True}
        agent = IntrospectiveAgent(config=config)
        assert agent.dimension_probe is not None


class TestRecordExperience:
    """记录经验功能测试"""

    def test_record_experience_success(self):
        """测试记录成功经验"""
        agent = IntrospectiveAgent()

        record = agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        assert record is not None
        assert record.task_id == "task_001"
        assert record.task_type == "crawler"
        assert record.status == "success"
        assert record.duration_ms == 1000.0
        assert record.experience_id is not None
        assert agent.pool.count() == 1

    def test_record_experience_with_kwargs(self):
        """测试带额外参数记录经验"""
        agent = IntrospectiveAgent()

        record = agent.record_experience(
            task_id="task_002",
            task_type="processor",
            status="failed",
            duration_ms=2000.0,
            task_name="数据处理任务",
            errors=["数据格式错误"],
            performance_metrics={"accuracy": 0.5},
        )

        assert record.task_name == "数据处理任务"
        assert record.errors == ["数据格式错误"]
        assert record.performance_metrics["accuracy"] == 0.5

    def test_record_multiple_experiences(self):
        """测试记录多条经验"""
        agent = IntrospectiveAgent()

        for i in range(5):
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler",
                status="success" if i % 2 == 0 else "failed",
                duration_ms=1000.0 * (i + 1),
            )

        assert agent.pool.count() == 5

    def test_record_quality_score_computed(self):
        """测试记录后质量评分自动计算"""
        agent = IntrospectiveAgent()

        record = agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=500.0,
        )

        assert record.quality_score is not None
        assert 0.0 <= record.quality_score <= 1.0


class TestSelfReflect:
    """自我反思功能测试"""

    def test_self_reflect_empty_pool(self):
        """测试空数据池自我反思"""
        agent = IntrospectiveAgent()

        result = agent.self_reflect()

        assert result["success"] is True
        assert "reflection_time" in result
        assert "self_assessment" in result
        assert "error_statistics" in result
        assert "profile_summary" in result
        assert result["experience_count"] == 0

    def test_self_reflect_with_data(self):
        """测试有数据时自我反思"""
        agent = IntrospectiveAgent()

        for i in range(10):
            status = "success" if i < 7 else "failed"
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler",
                status=status,
                duration_ms=1000.0,
                performance_metrics={"accuracy": 0.8 if status == "success" else 0.4},
            )

        result = agent.self_reflect()

        assert result["success"] is True
        assert result["experience_count"] == 10
        assert "overall_score" in result["self_assessment"]
        assert result["self_assessment"]["overall_score"] > 0.0
        assert len(result["self_assessment"]["dimensions"]) > 0

    def test_self_reflect_with_specific_experience_id(self):
        """测试指定经验ID的自我反思"""
        agent = IntrospectiveAgent()

        record = agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        result = agent.self_reflect(experience_id=record.experience_id)
        assert result["success"] is True

    def test_self_reflect_invalid_experience_id(self):
        """测试无效经验ID的自我反思"""
        agent = IntrospectiveAgent()

        result = agent.self_reflect(experience_id="invalid_id")
        assert result["success"] is False
        assert "error" in result


class TestGetSelfProfile:
    """获取自我画像功能测试"""

    def test_get_self_profile_empty(self):
        """测试空数据池获取画像"""
        agent = IntrospectiveAgent()

        profile = agent.get_self_profile()

        assert isinstance(profile, AgentProfile)
        assert profile.agent_name == "introspective_agent"
        assert profile.experience_count == 0
        assert profile.overall_score == 0.0

    def test_get_self_profile_with_data(self):
        """测试有数据时获取画像"""
        agent = IntrospectiveAgent()

        for i in range(10):
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler" if i % 2 == 0 else "processor",
                status="success" if i < 7 else "failed",
                duration_ms=1000.0,
            )

        profile = agent.get_self_profile()

        assert profile.experience_count == 10
        assert profile.overall_score > 0.0
        assert len(profile.skill_domains) > 0
        assert len(profile.strengths) > 0


class TestAnalyzeTrend:
    """趋势分析功能测试"""

    def test_analyze_trend_empty(self):
        """测试空数据池趋势分析"""
        agent = IntrospectiveAgent()

        result = agent.analyze_trend(days=30)

        assert "overall_trend" in result
        assert "total_points" in result
        assert result["total_points"] == 0
        assert "key_findings" in result

    def test_analyze_trend_with_data(self):
        """测试有数据时趋势分析"""
        agent = IntrospectiveAgent()

        for i in range(20):
            days_ago = 20 - i
            timestamp = datetime.now() - timedelta(days=days_ago)
            status = "success" if i < 15 else "failed"
            record = agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler",
                status=status,
                duration_ms=1000.0,
            )
            record.timestamp = timestamp
            agent.pool._update_dataframe()

        result = agent.analyze_trend(days=30)

        assert "overall_trend" in result
        assert "dimension_trends" in result
        assert "key_findings" in result
        assert len(result["key_findings"]) > 0


class TestMinePatterns:
    """模式挖掘功能测试"""

    def test_mine_patterns_empty(self):
        """测试空数据池模式挖掘"""
        agent = IntrospectiveAgent()
        patterns = agent.mine_patterns(min_frequency=3)
        assert isinstance(patterns, list)
        assert len(patterns) == 0

    def test_mine_patterns_with_data(self):
        """测试有数据时模式挖掘"""
        agent = IntrospectiveAgent()

        for i in range(10):
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler",
                status="success" if i < 8 else "failed",
                duration_ms=1000.0,
            )

        patterns = agent.mine_patterns(min_frequency=3)
        assert isinstance(patterns, list)
        assert len(patterns) >= 0

    def test_mine_patterns_min_frequency(self):
        """测试最小频率参数"""
        agent = IntrospectiveAgent()

        for i in range(5):
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler",
                status="success",
                duration_ms=1000.0,
            )

        patterns_low = agent.mine_patterns(min_frequency=1)
        patterns_high = agent.mine_patterns(min_frequency=10)

        assert len(patterns_low) >= len(patterns_high)


class TestOptimizeSkill:
    """技能优化功能测试"""

    def test_optimize_skill_basic(self):
        """测试基本技能优化"""
        agent = IntrospectiveAgent()

        for i in range(15):
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="skill_usage",
                status="success" if i < 10 else "failed",
                duration_ms=1000.0,
                performance_metrics={"accuracy": 0.7, "efficiency": 0.6},
                metadata={"skill_id": "test_skill"},
            )

        result = agent.optimize_skill(skill_id="test_skill")

        assert "success" in result
        assert "skill_id" in result
        assert result["skill_id"] == "test_skill"
        if result["success"]:
            assert "iteration_id" in result
            assert "overall_improvement" in result

    def test_optimize_skill_insufficient_data(self):
        """测试经验不足时技能优化"""
        agent = IntrospectiveAgent()

        result = agent.optimize_skill(skill_id="new_skill")
        assert isinstance(result, dict)
        assert "skill_id" in result


class TestSnapshot:
    """快照创建和恢复功能测试"""

    def test_create_snapshot(self):
        """测试创建快照"""
        agent = IntrospectiveAgent()

        agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        snapshot_id = agent.create_snapshot(name="test_snapshot")

        assert snapshot_id is not None
        assert snapshot_id.startswith("snap_")

        snapshots = agent.snapshot_manager.list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].name == "test_snapshot"

    def test_restore_snapshot(self):
        """测试恢复快照"""
        agent = IntrospectiveAgent()

        agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        snapshot_id = agent.create_snapshot(name="snap1")

        agent.record_experience(
            task_id="task_002",
            task_type="processor",
            status="failed",
            duration_ms=2000.0,
        )

        assert agent.pool.count() == 2

        result = agent.restore_snapshot(snapshot_id)

        assert result is True
        assert agent.pool.count() == 1

    def test_restore_invalid_snapshot(self):
        """测试恢复无效快照"""
        agent = IntrospectiveAgent()

        result = agent.restore_snapshot("invalid_snapshot_id")
        assert result is False


class TestExportExperience:
    """经验导出功能测试"""

    def test_export_json_empty(self):
        """测试空数据池JSON导出"""
        agent = IntrospectiveAgent()
        result = agent.export_experience(format="json")
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_export_json_with_data(self):
        """测试有数据JSON导出"""
        agent = IntrospectiveAgent()

        agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        result = agent.export_experience(format="json")
        data = json.loads(result)

        assert len(data) == 1
        assert data[0]["task_id"] == "task_001"

    def test_export_csv_with_data(self):
        """测试CSV导出"""
        agent = IntrospectiveAgent()

        agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        result = agent.export_experience(format="csv")
        assert isinstance(result, str)
        assert "task_id" in result
        assert "task_001" in result

    def test_export_invalid_format(self):
        """测试无效导出格式"""
        agent = IntrospectiveAgent()

        with pytest.raises(ValueError):
            agent.export_experience(format="invalid_format")


class TestGetStatus:
    """状态获取功能测试"""

    def test_get_status_empty(self):
        """测试空数据池状态获取"""
        agent = IntrospectiveAgent()

        status = agent.get_status()

        assert "agent_name" in status
        assert "experience" in status
        assert "snapshots" in status
        assert "profile" in status
        assert "trend" in status
        assert "dimension_probe_enabled" in status
        assert status["experience"]["total_records"] == 0
        assert status["snapshots"]["count"] == 0

    def test_get_status_with_data(self):
        """测试有数据时状态获取"""
        agent = IntrospectiveAgent()

        for i in range(5):
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler",
                status="success" if i < 3 else "failed",
                duration_ms=1000.0,
            )

        agent.create_snapshot(name="test_snap")

        status = agent.get_status()

        assert status["experience"]["total_records"] == 5
        assert status["snapshots"]["count"] == 1
        assert status["profile"]["experience_count"] == 5
        assert "overall_trend" in status["trend"]


class TestIntrospectDeep:
    """深度自省功能测试"""

    def test_introspect_deep_empty(self):
        """测试空数据池深度自省"""
        agent = IntrospectiveAgent()

        result = agent.introspect_deep()

        assert "introspection_time" in result
        assert "agent_name" in result
        assert "profile" in result
        assert "trend" in result
        assert "patterns" in result
        assert "top_insights" in result
        assert "error_statistics" in result
        assert "iteration_suggestions" in result
        assert "overall_summary" in result
        assert isinstance(result["overall_summary"], str)

    def test_introspect_deep_with_data(self):
        """测试有数据时深度自省"""
        agent = IntrospectiveAgent()

        for i in range(20):
            agent.record_experience(
                task_id=f"task_{i}",
                task_type="crawler" if i % 2 == 0 else "processor",
                status="success" if i < 15 else "failed",
                duration_ms=1000.0,
                performance_metrics={"accuracy": 0.75, "efficiency": 0.65},
            )

        result = agent.introspect_deep()

        assert result["profile"]["experience_count"] == 20
        assert result["patterns"]["total_count"] >= 0
        assert len(result["overall_summary"]) > 0
        assert "top_insights" in result


class TestDimensionProbeDataset:
    """维度空间探测功能测试"""

    def test_probe_disabled(self):
        """测试探针未启用时"""
        agent = IntrospectiveAgent()

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = agent.dimension_probe_dataset(df, "test_dataset")

        assert result is None

    def test_probe_enabled(self):
        """测试探针启用时"""
        config = {"enable_dimension_probe": True}
        agent = IntrospectiveAgent(config=config)

        df = pd.DataFrame({
            "col1": [1.0, 2.0, 3.0, 4.0, 5.0],
            "col2": [5.0, 4.0, 3.0, 2.0, 1.0],
            "col3": ["a", "b", "c", "d", "e"],
        })

        result = agent.dimension_probe_dataset(df, "test_dataset")

        assert result is not None
        assert "report_id" in result
        assert "dataset_name" in result
        assert result["dataset_name"] == "test_dataset"
        assert "overall_health_score" in result
        assert "record_count" in result


class TestEmptyPoolBehavior:
    """空数据池各功能合理行为测试"""

    def test_empty_pool_record_and_reflect(self):
        """测试空数据池记录和反思"""
        agent = IntrospectiveAgent()

        record = agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        assert record is not None
        assert agent.pool.count() == 1

        reflect_result = agent.self_reflect()
        assert reflect_result["success"] is True
        assert reflect_result["experience_count"] >= 1

    def test_empty_pool_all_methods(self):
        """测试空数据池所有主要方法"""
        agent = IntrospectiveAgent()

        profile = agent.get_self_profile()
        assert profile is not None

        trend = agent.analyze_trend()
        assert trend is not None

        patterns = agent.mine_patterns()
        assert isinstance(patterns, list)

        snapshot_id = agent.create_snapshot("empty_snap")
        assert snapshot_id is not None

        status = agent.get_status()
        assert status is not None

        deep = agent.introspect_deep()
        assert deep is not None


class TestEdgeCases:
    """边界情况和错误处理测试"""

    def test_record_with_minimal_params(self):
        """测试最少参数记录经验"""
        agent = IntrospectiveAgent()

        record = agent.record_experience(
            task_id="t1",
            task_type="crawler",
            status="success",
            duration_ms=0.0,
        )

        assert record is not None
        assert record.task_id == "t1"

    def test_restore_snapshot_twice(self):
        """测试重复恢复快照"""
        agent = IntrospectiveAgent()

        agent.record_experience(
            task_id="task_001",
            task_type="crawler",
            status="success",
            duration_ms=1000.0,
        )

        snapshot_id = agent.create_snapshot("snap1")

        result1 = agent.restore_snapshot(snapshot_id)
        result2 = agent.restore_snapshot(snapshot_id)

        assert result1 is True
        assert result2 is True

    def test_export_json_then_import(self):
        """测试导出JSON后重新导入（验证数据一致性）"""
        agent1 = IntrospectiveAgent()

        agent1.record_experience(
            task_id="task_001",
            task_type="crawler",
            task_name="test_task",
            status="success",
            duration_ms=1000.0,
            performance_metrics={"accuracy": 0.9},
        )

        json_data = agent1.export_experience(format="json")

        agent2 = IntrospectiveAgent()
        records_data = json.loads(json_data)
        for data in records_data:
            record = ExperienceRecord.from_dict(data)
            agent2.pool.add_record(record)

        assert agent2.pool.count() == 1
        record = agent2.pool.get_record(list(agent2.pool._records.keys())[0])
        assert record.task_id == "task_001"
        assert record.task_name == "test_task"
