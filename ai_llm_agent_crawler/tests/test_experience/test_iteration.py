"""
技能自迭代闭环模块单元测试

测试技能迭代引擎的触发检测、迭代执行、版本管理、应用回滚等功能。
"""

import json
from datetime import datetime, timedelta

import pytest

from ai_llm_agent_crawler.experience import (
    ExperienceDataPool,
    ExperienceRecord,
    IterationConfig,
    IterationRecord,
    IterationTriggerType,
    OptimizationStrategyType,
    SkillIterationEngine,
    TaskStatus,
    TaskType,
)


class TestIterationTriggerType:
    """迭代触发类型枚举测试"""

    def test_trigger_type_values(self):
        """测试触发类型枚举值"""
        assert IterationTriggerType.PERFORMANCE_DEGRADATION == "performance_degradation"
        assert IterationTriggerType.EXPERIENCE_ACCUMULATION == "experience_accumulation"
        assert IterationTriggerType.MANUAL == "manual"
        assert IterationTriggerType.SCHEDULED == "scheduled"

    def test_trigger_type_count(self):
        """测试触发类型数量"""
        assert len(IterationTriggerType) == 4


class TestOptimizationStrategyType:
    """优化策略类型枚举测试"""

    def test_strategy_type_values(self):
        """测试策略类型枚举值"""
        assert OptimizationStrategyType.RULE_TUNING == "rule_tuning"
        assert OptimizationStrategyType.PARAMETER_ADJUSTMENT == "parameter_adjustment"
        assert OptimizationStrategyType.CODE_REFINEMENT == "code_refinement"
        assert OptimizationStrategyType.HYBRID == "hybrid"

    def test_strategy_type_count(self):
        """测试策略类型数量"""
        assert len(OptimizationStrategyType) == 4


class TestIterationRecord:
    """迭代记录模型测试"""

    def test_create_iteration_record(self):
        """测试创建迭代记录"""
        record = IterationRecord(
            skill_id="skill_001",
            skill_name="测试技能",
            trigger_type=IterationTriggerType.MANUAL,
            strategy=OptimizationStrategyType.HYBRID,
            original_version="1.0.0",
            optimized_version="1.0.1",
            reason="手动触发测试",
            changes=["测试变更1", "测试变更2"],
            improvements={"accuracy": 0.05, "efficiency": 0.03},
            before_metrics={"accuracy": 0.7, "efficiency": 0.6},
            after_metrics={"accuracy": 0.75, "efficiency": 0.63},
            overall_improvement=0.1,
        )

        assert record.skill_id == "skill_001"
        assert record.skill_name == "测试技能"
        assert record.trigger_type == IterationTriggerType.MANUAL
        assert record.strategy == OptimizationStrategyType.HYBRID
        assert record.original_version == "1.0.0"
        assert record.optimized_version == "1.0.1"
        assert record.reason == "手动触发测试"
        assert len(record.changes) == 2
        assert record.overall_improvement == 0.1
        assert record.is_approved is False
        assert record.is_applied is False
        assert record.rollback_available is True
        assert isinstance(record.created_at, datetime)
        assert record.applied_at is None

    def test_iteration_record_defaults(self):
        """测试迭代记录默认值"""
        record = IterationRecord(
            skill_id="skill_001",
            skill_name="测试技能",
            trigger_type=IterationTriggerType.MANUAL,
            strategy=OptimizationStrategyType.HYBRID,
            original_version="1.0.0",
            optimized_version="1.0.1",
        )

        assert record.reason == ""
        assert record.changes == []
        assert record.improvements == {}
        assert record.before_metrics == {}
        assert record.after_metrics == {}
        assert record.overall_improvement == 0.0
        assert record.test_results == {}

    def test_iteration_id_format(self):
        """测试迭代ID格式"""
        record = IterationRecord(
            skill_id="skill_001",
            skill_name="测试技能",
            trigger_type=IterationTriggerType.MANUAL,
            strategy=OptimizationStrategyType.HYBRID,
            original_version="1.0.0",
            optimized_version="1.0.1",
        )

        assert record.iteration_id.startswith("iter_")
        assert len(record.iteration_id) > 20

    def test_iteration_record_validation(self):
        """测试迭代记录验证"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            IterationRecord(
                skill_id="skill_001",
                skill_name="测试技能",
                trigger_type=IterationTriggerType.MANUAL,
                strategy=OptimizationStrategyType.HYBRID,
                original_version="1.0.0",
                optimized_version="1.0.1",
                overall_improvement=1.5,
            )

        with pytest.raises(ValidationError):
            IterationRecord(
                skill_id="skill_001",
                skill_name="测试技能",
                trigger_type=IterationTriggerType.MANUAL,
                strategy=OptimizationStrategyType.HYBRID,
                original_version="1.0.0",
                optimized_version="1.0.1",
                overall_improvement=-0.1,
            )


class TestIterationConfig:
    """迭代配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = IterationConfig()

        assert config.min_experience_count == 10
        assert config.performance_degradation_threshold == 0.1
        assert config.auto_apply is False
        assert config.require_approval is True
        assert config.rollback_enabled is True
        assert config.default_strategy == OptimizationStrategyType.HYBRID
        assert config.max_iterations_without_improvement == 3
        assert config.test_sample_size == 20

    def test_custom_config(self):
        """测试自定义配置"""
        config = IterationConfig(
            min_experience_count=5,
            performance_degradation_threshold=0.2,
            auto_apply=True,
            require_approval=False,
            rollback_enabled=False,
            default_strategy=OptimizationStrategyType.PARAMETER_ADJUSTMENT,
            max_iterations_without_improvement=5,
            test_sample_size=10,
        )

        assert config.min_experience_count == 5
        assert config.performance_degradation_threshold == 0.2
        assert config.auto_apply is True
        assert config.require_approval is False
        assert config.rollback_enabled is False
        assert config.default_strategy == OptimizationStrategyType.PARAMETER_ADJUSTMENT
        assert config.max_iterations_without_improvement == 5
        assert config.test_sample_size == 10


class TestSkillIterationEngine:
    """技能迭代引擎测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def engine(self, pool):
        """创建技能迭代引擎"""
        return SkillIterationEngine(pool)

    @pytest.fixture
    def sample_records(self):
        """创建示例经验记录列表"""
        records = []
        now = datetime.now()
        for i in range(15):
            if i < 10:
                status = TaskStatus.SUCCESS
            elif i < 13:
                status = TaskStatus.PARTIAL
            else:
                status = TaskStatus.FAILED

            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"skill_task_{i}",
                status=status,
                timestamp=now - timedelta(hours=15 - i),
                duration_ms=500.0 + i * 50.0,
                performance_metrics={
                    "accuracy": 0.6 + i * 0.02,
                    "efficiency": 0.5 + i * 0.015,
                },
                input_summary=f"input_{i}",
                output_summary=f"output_{i}_result",
                errors=[f"error_type_{i % 3}"] if i % 3 == 0 else [],
                warnings=[f"warning_{i}"] if i % 4 == 0 else [],
                metadata={"skill_id": "skill_test", "index": i},
            )
            records.append(record)
        return records

    @pytest.fixture
    def pool_with_records(self, pool, sample_records):
        """创建包含示例记录的数据池"""
        for record in sample_records:
            pool.add_record(record)
        return pool

    @pytest.fixture
    def engine_with_data(self, pool_with_records):
        """创建有数据的迭代引擎"""
        return SkillIterationEngine(pool_with_records)

    def test_engine_initialization(self, pool):
        """测试引擎初始化"""
        engine = SkillIterationEngine(pool)
        assert engine is not None

        config = IterationConfig(min_experience_count=5)
        engine2 = SkillIterationEngine(pool, config)
        assert engine2 is not None

    def test_check_trigger_empty_pool(self, engine):
        """测试空数据池触发检测"""
        triggered, trigger_type = engine.check_trigger("skill_unknown")
        assert triggered is False
        assert trigger_type is None

    def test_check_trigger_experience_accumulation(self, engine_with_data):
        """测试经验积累触发"""
        triggered, trigger_type = engine_with_data.check_trigger("skill_test")
        assert triggered is True
        assert trigger_type == IterationTriggerType.EXPERIENCE_ACCUMULATION

    def test_check_trigger_performance_degradation(self, pool):
        """测试性能下降触发"""
        now = datetime.now()

        for i in range(10):
            if i < 5:
                status = TaskStatus.SUCCESS
                accuracy = 0.9 - i * 0.01
            else:
                status = TaskStatus.FAILED
                accuracy = 0.4 + (i - 5) * 0.02

            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"test_task_{i}",
                status=status,
                timestamp=now - timedelta(hours=10 - i),
                duration_ms=1000.0,
                performance_metrics={"accuracy": accuracy, "efficiency": 0.7},
                input_summary=f"input_{i}",
                output_summary=f"output_{i}",
                errors=[],
                warnings=[],
                metadata={"skill_id": "skill_degrade"},
            )
            pool.add_record(record)

        engine = SkillIterationEngine(pool)
        triggered, trigger_type = engine.check_trigger("skill_degrade")
        assert triggered is True

    def test_run_iteration_manual(self, engine_with_data):
        """测试手动触发完整迭代"""
        record = engine_with_data.run_iteration("skill_test", IterationTriggerType.MANUAL)

        assert record is not None
        assert isinstance(record, IterationRecord)
        assert record.skill_id == "skill_test"
        assert record.trigger_type == IterationTriggerType.MANUAL
        assert record.original_version == "1.0.0"
        assert record.optimized_version != record.original_version
        assert len(record.changes) > 0
        assert 0.0 <= record.overall_improvement <= 1.0
        assert record.is_applied is False
        assert record.is_approved is False

    def test_run_iteration_all_required_fields(self, engine_with_data):
        """测试迭代记录包含所有必要字段"""
        record = engine_with_data.run_iteration("skill_test")

        assert record is not None
        assert record.iteration_id is not None
        assert record.skill_id is not None
        assert record.skill_name is not None
        assert record.trigger_type is not None
        assert record.strategy is not None
        assert record.original_version is not None
        assert record.optimized_version is not None
        assert record.created_at is not None
        assert "accuracy" in record.before_metrics
        assert "efficiency" in record.before_metrics
        assert "success_rate" in record.before_metrics
        assert "accuracy" in record.after_metrics
        assert "efficiency" in record.after_metrics
        assert "success_rate" in record.after_metrics

    def test_version_increment(self, engine_with_data):
        """测试优化前后版本号正确递增"""
        record1 = engine_with_data.run_iteration("skill_test")
        assert record1 is not None

        record1.is_approved = True
        engine_with_data.apply_iteration(record1.iteration_id)

        record2 = engine_with_data.run_iteration("skill_test")
        assert record2 is not None

        assert record2.original_version == record1.optimized_version

        v1_parts = record1.original_version.split(".")
        v2_parts = record1.optimized_version.split(".")
        assert len(v1_parts) == 3
        assert len(v2_parts) == 3

    def test_evaluate_improvement(self, engine):
        """测试改进率计算正确"""
        before = {"accuracy": 0.5, "efficiency": 0.5, "success_rate": 0.5}
        after = {"accuracy": 0.75, "efficiency": 0.75, "success_rate": 0.75}

        improvement = engine._evaluate_improvement(before, after)
        assert 0.0 < improvement <= 1.0

    def test_evaluate_improvement_no_change(self, engine):
        """测试无改进时改进率为0"""
        before = {"accuracy": 0.7, "efficiency": 0.6, "success_rate": 0.8}
        after = {"accuracy": 0.7, "efficiency": 0.6, "success_rate": 0.8}

        improvement = engine._evaluate_improvement(before, after)
        assert improvement == 0.0

    def test_apply_iteration(self, engine_with_data):
        """测试应用迭代功能"""
        record = engine_with_data.run_iteration("skill_test")
        assert record is not None
        assert record.is_applied is False

        record.is_approved = True
        success = engine_with_data.apply_iteration(record.iteration_id)
        assert success is True
        assert record.is_applied is True
        assert record.applied_at is not None

    def test_apply_iteration_not_approved(self, engine_with_data):
        """测试未批准的迭代无法应用"""
        record = engine_with_data.run_iteration("skill_test")
        assert record is not None

        success = engine_with_data.apply_iteration(record.iteration_id)
        assert success is False

    def test_apply_iteration_not_exist(self, engine):
        """测试应用不存在的迭代"""
        success = engine.apply_iteration("nonexistent_iter_id")
        assert success is False

    def test_rollback(self, engine_with_data):
        """测试回滚功能"""
        record1 = engine_with_data.run_iteration("skill_test")
        assert record1 is not None
        record1.is_approved = True
        engine_with_data.apply_iteration(record1.iteration_id)

        record2 = engine_with_data.run_iteration("skill_test")
        assert record2 is not None
        record2.is_approved = True
        engine_with_data.apply_iteration(record2.iteration_id)

        success = engine_with_data.rollback("skill_test")
        assert success is True

    def test_rollback_no_versions(self, engine):
        """测试无可回滚版本时回滚失败"""
        success = engine.rollback("skill_unknown")
        assert success is False

    def test_rollback_disabled(self, pool):
        """测试关闭回滚功能"""
        config = IterationConfig(rollback_enabled=False)
        engine = SkillIterationEngine(pool, config)
        success = engine.rollback("skill_test")
        assert success is False

    def test_get_iteration_history(self, engine_with_data):
        """测试迭代历史查询"""
        history = engine_with_data.get_iteration_history("skill_test")
        assert isinstance(history, list)
        assert len(history) == 0

        record1 = engine_with_data.run_iteration("skill_test")
        assert record1 is not None

        record2 = engine_with_data.run_iteration("skill_test")
        assert record2 is not None

        history = engine_with_data.get_iteration_history("skill_test")
        assert len(history) == 2

        for i in range(len(history) - 1):
            assert history[i].created_at >= history[i + 1].created_at

    def test_get_iteration(self, engine_with_data):
        """测试获取单条迭代记录"""
        record = engine_with_data.run_iteration("skill_test")
        assert record is not None

        retrieved = engine_with_data.get_iteration(record.iteration_id)
        assert retrieved is not None
        assert retrieved.iteration_id == record.iteration_id
        assert retrieved.skill_id == record.skill_id

    def test_get_iteration_not_exist(self, engine):
        """测试获取不存在的迭代记录"""
        result = engine.get_iteration("nonexistent")
        assert result is None

    def test_get_evolution_trajectory(self, engine_with_data):
        """测试进化轨迹功能"""
        trajectory = engine_with_data.get_evolution_trajectory("skill_test")
        assert isinstance(trajectory, dict)
        assert "skill_id" in trajectory
        assert "versions" in trajectory
        assert "version_count" in trajectory
        assert "performance_curve" in trajectory
        assert "key_iterations" in trajectory
        assert "current_version" in trajectory
        assert "total_iterations" in trajectory

        record = engine_with_data.run_iteration("skill_test")
        assert record is not None
        record.is_approved = True
        engine_with_data.apply_iteration(record.iteration_id)

        trajectory = engine_with_data.get_evolution_trajectory("skill_test")
        assert trajectory["version_count"] >= 2
        assert trajectory["total_iterations"] == 1

    def test_auto_apply_config(self, pool):
        """测试自动应用配置"""
        config = IterationConfig(
            auto_apply=True,
            require_approval=False,
            min_experience_count=5,
        )

        now = datetime.now()
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=TaskStatus.SUCCESS,
                timestamp=now - timedelta(hours=i),
                duration_ms=1000.0,
                performance_metrics={"accuracy": 0.7, "efficiency": 0.6},
                input_summary=f"input_{i}",
                output_summary=f"output_{i}",
                metadata={"skill_id": "skill_auto"},
            )
            pool.add_record(record)

        engine = SkillIterationEngine(pool, config)
        record = engine.run_iteration("skill_auto")
        assert record is not None
        assert record.is_applied is True
        assert record.is_approved is True

    def test_max_iterations_without_improvement(self, pool):
        """测试无改进最大迭代次数限制"""
        config = IterationConfig(
            max_iterations_without_improvement=2,
            min_experience_count=3,
        )

        now = datetime.now()
        for i in range(5):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=TaskStatus.SUCCESS,
                timestamp=now - timedelta(hours=i),
                duration_ms=1000.0,
                performance_metrics={"accuracy": 0.95, "efficiency": 0.95},
                input_summary=f"input_{i}",
                output_summary=f"output_{i}",
                metadata={"skill_id": "skill_no_improve"},
            )
            pool.add_record(record)

        engine = SkillIterationEngine(pool, config)

        count = 0
        for i in range(5):
            record = engine.run_iteration("skill_no_improve")
            if record is not None:
                count += 1
            else:
                break

        assert count <= 3

    def test_unknown_skill_id(self, engine):
        """测试未知skill_id的边界情况"""
        triggered, _ = engine.check_trigger("unknown_skill")
        assert triggered is False

        history = engine.get_iteration_history("unknown_skill")
        assert history == []

        trajectory = engine.get_evolution_trajectory("unknown_skill")
        assert trajectory["total_iterations"] == 0

    def test_empty_experiences_run_iteration(self, engine):
        """测试空经验数据时运行迭代"""
        result = engine.run_iteration("empty_skill")
        assert result is None

    def test_run_tests_function(self, engine_with_data):
        """测试测试验证功能正常"""
        test_data = [
            {"test_id": "t1", "expected_accuracy": 0.8, "expected_efficiency": 0.7},
            {"test_id": "t2", "expected_accuracy": 0.6, "expected_efficiency": 0.5},
            {"test_id": "t3", "expected_accuracy": 0.9, "expected_efficiency": 0.8},
        ]

        metrics = engine_with_data._run_tests("skill_test", "1.0.0", test_data)
        assert "accuracy" in metrics
        assert "efficiency" in metrics
        assert "success_rate" in metrics
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["efficiency"] <= 1.0
        assert 0.0 <= metrics["success_rate"] <= 1.0

    def test_iteration_record_json_serializable(self, engine_with_data):
        """测试迭代记录可序列化为JSON"""
        record = engine_with_data.run_iteration("skill_test")
        assert record is not None

        json_str = record.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        data = json.loads(json_str)
        assert "iteration_id" in data
        assert "skill_id" in data
        assert "overall_improvement" in data

    def test_analyze_experiences(self, engine_with_data):
        """测试经验分析功能"""
        analysis = engine_with_data._analyze_experiences("skill_test")
        assert analysis["experiences_available"] is True
        assert analysis["total_count"] > 0
        assert "success_rate" in analysis
        assert "avg_accuracy" in analysis
        assert "avg_efficiency" in analysis
        assert "common_errors" in analysis
        assert "weak_points" in analysis
        assert "performance_trend" in analysis

    def test_generate_optimization_plan(self, engine_with_data):
        """测试优化方案生成"""
        analysis = engine_with_data._analyze_experiences("skill_test")
        strategy, changes = engine_with_data._generate_optimization_plan(analysis)

        assert strategy is not None
        assert isinstance(strategy, OptimizationStrategyType)
        assert isinstance(changes, list)
        assert len(changes) > 0

    def test_create_optimized_version(self, engine):
        """测试创建优化版本"""
        version_info = engine._create_optimized_version(
            "skill_test",
            OptimizationStrategyType.PARAMETER_ADJUSTMENT,
            ["change1", "change2"],
        )

        assert "version" in version_info
        assert "strategy" in version_info
        assert "changes" in version_info
        assert "expected_metrics" in version_info
        assert version_info["version"] != "1.0.0"

    def test_multiple_iterations_improvement(self, engine_with_data):
        """测试多次迭代后性能趋势"""
        records = []
        for i in range(3):
            record = engine_with_data.run_iteration("skill_test")
            if record:
                record.is_approved = True
                engine_with_data.apply_iteration(record.iteration_id)
                records.append(record)

        assert len(records) >= 1
