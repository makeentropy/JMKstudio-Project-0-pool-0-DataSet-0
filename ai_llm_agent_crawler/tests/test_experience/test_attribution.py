"""
错误归因与经验总结模块单元测试

测试错误归因器、经验总结器的各功能。
"""

from datetime import datetime, timedelta

import pytest

from ai_llm_agent_crawler.experience import (
    AttributionResult,
    ErrorAttributor,
    ErrorCategory,
    ExperienceDataPool,
    ExperienceRecord,
    ExperienceSummarizer,
    Heuristic,
    TaskStatus,
    TaskType,
)


class TestErrorCategory:
    """错误分类枚举测试"""

    def test_category_values(self):
        """测试错误分类枚举值"""
        assert ErrorCategory.DATA_ISSUE == "data_issue"
        assert ErrorCategory.STRATEGY_ISSUE == "strategy_issue"
        assert ErrorCategory.PARAMETER_ISSUE == "parameter_issue"
        assert ErrorCategory.ENVIRONMENT_ISSUE == "environment_issue"
        assert ErrorCategory.UNKNOWN == "unknown"

    def test_category_count(self):
        """测试错误分类数量"""
        assert len(ErrorCategory) == 5


class TestAttributionResult:
    """归因结果模型测试"""

    def test_create_attribution_result(self):
        """测试创建归因结果"""
        result = AttributionResult(
            error_category=ErrorCategory.DATA_ISSUE,
            confidence=0.85,
            key_evidence=["证据1", "证据2"],
            root_cause="数据质量问题",
            related_experience_ids=["exp_001"],
            suggested_fix="检查数据质量",
        )

        assert result.error_category == ErrorCategory.DATA_ISSUE
        assert result.confidence == 0.85
        assert len(result.key_evidence) == 2
        assert result.root_cause == "数据质量问题"
        assert len(result.related_experience_ids) == 1
        assert result.suggested_fix == "检查数据质量"
        assert isinstance(result.attribution_time, datetime)

    def test_attribution_result_defaults(self):
        """测试归因结果默认值"""
        result = AttributionResult(
            error_category=ErrorCategory.UNKNOWN,
            confidence=0.5,
        )

        assert result.key_evidence == []
        assert result.root_cause == ""
        assert result.related_experience_ids == []
        assert result.suggested_fix == ""

    def test_attribution_result_validation(self):
        """测试归因结果验证"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AttributionResult(
                error_category=ErrorCategory.DATA_ISSUE,
                confidence=1.5,
            )

        with pytest.raises(ValidationError):
            AttributionResult(
                error_category=ErrorCategory.DATA_ISSUE,
                confidence=-0.1,
            )


class TestHeuristic:
    """经验模式模型测试"""

    def test_create_heuristic(self):
        """测试创建经验模式"""
        heuristic = Heuristic(
            heuristic_id="heur_12345678",
            name="测试模式",
            description="测试模式描述",
            pattern_type="success_pattern",
            frequency=10,
            typical_features=["特征1", "特征2"],
            applicable_scenarios=["场景1"],
            related_tasks=["crawler"],
            confidence=0.9,
        )

        assert heuristic.heuristic_id == "heur_12345678"
        assert heuristic.name == "测试模式"
        assert heuristic.pattern_type == "success_pattern"
        assert heuristic.frequency == 10
        assert len(heuristic.typical_features) == 2
        assert heuristic.confidence == 0.9
        assert isinstance(heuristic.created_at, datetime)

    def test_heuristic_defaults(self):
        """测试经验模式默认值"""
        heuristic = Heuristic(
            heuristic_id="heur_test",
            name="测试",
            description="描述",
            pattern_type="failure_pattern",
        )

        assert heuristic.frequency == 0
        assert heuristic.typical_features == []
        assert heuristic.applicable_scenarios == []
        assert heuristic.related_tasks == []
        assert heuristic.confidence == 0.0
        assert heuristic.metadata == {}


class TestErrorAttributor:
    """错误归因器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def attributor(self, pool):
        """创建错误归因器"""
        return ErrorAttributor(pool)

    @pytest.fixture
    def data_error_record(self):
        """创建数据问题的错误记录"""
        return ExperienceRecord(
            task_id="task_data",
            task_type=TaskType.CRAWLER,
            task_name="data_error_task",
            status=TaskStatus.FAILED,
            errors=["数据质量差，存在大量缺失值", "格式错误导致解析失败"],
        )

    @pytest.fixture
    def strategy_error_record(self):
        """创建策略问题的错误记录"""
        return ExperienceRecord(
            task_id="task_strategy",
            task_type=TaskType.ANALYZER,
            task_name="strategy_error_task",
            status=TaskStatus.FAILED,
            errors=["算法错误导致结果偏差", "逻辑错误引起判断失误"],
        )

    @pytest.fixture
    def parameter_error_record(self):
        """创建参数问题的错误记录"""
        return ExperienceRecord(
            task_id="task_param",
            task_type=TaskType.PROCESSOR,
            task_name="param_error_task",
            status=TaskStatus.FAILED,
            errors=["参数配置错误", "阈值不当导致结果异常"],
        )

    @pytest.fixture
    def environment_error_record(self):
        """创建环境问题的错误记录"""
        return ExperienceRecord(
            task_id="task_env",
            task_type=TaskType.CRAWLER,
            task_name="env_error_task",
            status=TaskStatus.FAILED,
            errors=["网络错误，连接超时", "依赖缺失导致失败"],
        )

    @pytest.fixture
    def unknown_error_record(self):
        """创建未知错误的记录"""
        return ExperienceRecord(
            task_id="task_unknown",
            task_type=TaskType.OTHER,
            task_name="unknown_error_task",
            status=TaskStatus.FAILED,
            errors=["something went wrong", "mysterious failure"],
        )

    @pytest.fixture
    def no_error_record(self):
        """创建无错误的记录"""
        return ExperienceRecord(
            task_id="task_no_error",
            task_type=TaskType.CRAWLER,
            task_name="no_error_task",
            status=TaskStatus.SUCCESS,
            errors=[],
        )

    def test_attribute_data_issue(self, attributor, data_error_record):
        """测试数据问题归因"""
        result = attributor.attribute_error(data_error_record)

        assert isinstance(result, AttributionResult)
        assert result.error_category == ErrorCategory.DATA_ISSUE
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.key_evidence) > 0
        assert result.root_cause != ""
        assert result.suggested_fix != ""
        assert len(result.related_experience_ids) >= 1

    def test_attribute_strategy_issue(self, attributor, strategy_error_record):
        """测试策略问题归因"""
        result = attributor.attribute_error(strategy_error_record)

        assert isinstance(result, AttributionResult)
        assert result.error_category == ErrorCategory.STRATEGY_ISSUE
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.key_evidence) > 0

    def test_attribute_parameter_issue(self, attributor, parameter_error_record):
        """测试参数问题归因"""
        result = attributor.attribute_error(parameter_error_record)

        assert isinstance(result, AttributionResult)
        assert result.error_category == ErrorCategory.PARAMETER_ISSUE
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.key_evidence) > 0

    def test_attribute_environment_issue(self, attributor, environment_error_record):
        """测试环境问题归因"""
        result = attributor.attribute_error(environment_error_record)

        assert isinstance(result, AttributionResult)
        assert result.error_category == ErrorCategory.ENVIRONMENT_ISSUE
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.key_evidence) > 0

    def test_attribute_unknown_error(self, attributor, unknown_error_record):
        """测试未知错误归因"""
        result = attributor.attribute_error(unknown_error_record)

        assert isinstance(result, AttributionResult)
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.key_evidence) > 0

    def test_attribute_no_error(self, attributor, no_error_record):
        """测试无错误经验的归因"""
        result = attributor.attribute_error(no_error_record)

        assert isinstance(result, AttributionResult)
        assert result.error_category == ErrorCategory.UNKNOWN
        assert result.confidence < 0.5
        assert "无错误信息" in result.key_evidence[0]

    def test_attribute_batch(self, attributor, data_error_record, strategy_error_record, parameter_error_record):
        """测试批量归因"""
        experiences = [data_error_record, strategy_error_record, parameter_error_record]
        results = attributor.attribute_batch(experiences)

        assert len(results) == 3
        assert all(isinstance(r, AttributionResult) for r in results)
        assert results[0].error_category == ErrorCategory.DATA_ISSUE
        assert results[1].error_category == ErrorCategory.STRATEGY_ISSUE
        assert results[2].error_category == ErrorCategory.PARAMETER_ISSUE

    def test_attribute_with_historical_data(self, pool, attributor, data_error_record):
        """测试带历史数据的归因"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"hist_task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"hist_task_{i}",
                status=TaskStatus.FAILED,
                errors=["数据质量差", "数据缺失"],
            )
            pool.add_record(record)

        result = attributor.attribute_error(data_error_record)

        assert isinstance(result, AttributionResult)
        assert result.error_category == ErrorCategory.DATA_ISSUE
        assert len(result.related_experience_ids) > 1

    def test_get_error_statistics_empty(self, attributor):
        """测试空数据池的错误统计"""
        stats = attributor.get_error_statistics()

        assert stats["total_failed"] == 0
        assert stats["by_category"] == {}
        assert stats["top_errors"] == []
        assert stats["by_task_type"] == {}

    def test_get_error_statistics_with_data(self, pool, attributor):
        """测试有数据的错误统计"""
        error_templates = {
            ErrorCategory.DATA_ISSUE: ["数据质量差", "格式错误"],
            ErrorCategory.STRATEGY_ISSUE: ["算法错误", "逻辑错误"],
            ErrorCategory.PARAMETER_ISSUE: ["参数错误", "配置错误"],
            ErrorCategory.ENVIRONMENT_ISSUE: ["网络错误", "连接超时"],
        }

        idx = 0
        for category, errors in error_templates.items():
            for i in range(5):
                record = ExperienceRecord(
                    task_id=f"task_{idx}",
                    task_type=TaskType.CRAWLER if category in (ErrorCategory.DATA_ISSUE, ErrorCategory.ENVIRONMENT_ISSUE) else TaskType.ANALYZER,
                    task_name=f"task_{idx}",
                    status=TaskStatus.FAILED,
                    errors=errors,
                )
                pool.add_record(record)
                idx += 1

        stats = attributor.get_error_statistics()

        assert stats["total_failed"] == 20
        assert len(stats["by_category"]) >= 4
        assert len(stats["top_errors"]) > 0
        assert len(stats["by_task_type"]) >= 2
        assert "attribution_summary" in stats

    def test_get_error_statistics_with_filters(self, pool, attributor):
        """测试带过滤条件的错误统计"""
        for i in range(5):
            record = ExperienceRecord(
                task_id=f"crawler_task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"crawler_{i}",
                status=TaskStatus.FAILED,
                errors=["数据质量差"],
            )
            pool.add_record(record)

        for i in range(5):
            record = ExperienceRecord(
                task_id=f"processor_task_{i}",
                task_type=TaskType.PROCESSOR,
                task_name=f"processor_{i}",
                status=TaskStatus.FAILED,
                errors=["参数错误"],
            )
            pool.add_record(record)

        stats = attributor.get_error_statistics({"task_type": "crawler"})
        assert stats["total_failed"] == 5
        assert len(stats["by_task_type"]) == 1
        assert "crawler" in stats["by_task_type"]

    def test_classify_by_error_messages(self, attributor):
        """测试基于错误消息的分类"""
        errors = ["数据质量差，格式错误", "数据缺失严重"]
        category, confidence, evidence = attributor._classify_by_error_messages(errors)

        assert category == ErrorCategory.DATA_ISSUE
        assert 0.0 < confidence <= 1.0
        assert len(evidence) > 0

    def test_classify_by_context(self, attributor):
        """测试基于上下文的分类"""
        record = ExperienceRecord(
            task_id="ctx_task",
            task_type=TaskType.CRAWLER,
            task_name="ctx_task",
            status=TaskStatus.FAILED,
            performance_metrics={"data_quality": 0.3, "completeness": 0.4},
            duration_ms=45000,
            errors=["error"],
        )
        category, confidence, evidence = attributor._classify_by_context(record)

        assert 0.0 <= confidence <= 1.0
        assert isinstance(evidence, list)

    def test_classify_by_historical_similarity_empty(self, attributor):
        """测试无历史数据的相似案例分类"""
        record = ExperienceRecord(
            task_id="test_task",
            task_type=TaskType.CRAWLER,
            task_name="test",
            status=TaskStatus.FAILED,
            errors=["error"],
        )
        category, confidence, evidence = attributor._classify_by_historical_similarity(record)

        assert category == ErrorCategory.UNKNOWN
        assert confidence == 0.0

    def test_combine_attributions(self, attributor):
        """测试综合归因结果"""
        results = [
            (ErrorCategory.DATA_ISSUE, 0.8, ["证据1", "证据2"]),
            (ErrorCategory.DATA_ISSUE, 0.6, ["证据3"]),
            (ErrorCategory.UNKNOWN, 0.1, ["证据4"]),
        ]
        combined = attributor._combine_attributions(results)

        assert combined.error_category == ErrorCategory.DATA_ISSUE
        assert combined.confidence > 0.5
        assert len(combined.key_evidence) > 0
        assert combined.root_cause != ""

    def test_generate_suggested_fix(self, attributor):
        """测试生成建议修复方案"""
        categories = [
            ErrorCategory.DATA_ISSUE,
            ErrorCategory.STRATEGY_ISSUE,
            ErrorCategory.PARAMETER_ISSUE,
            ErrorCategory.ENVIRONMENT_ISSUE,
            ErrorCategory.UNKNOWN,
        ]

        for cat in categories:
            fix = attributor._generate_suggested_fix(cat, ["证据"])
            assert isinstance(fix, str)
            assert len(fix) > 0
            assert "建议" in fix

    def test_all_five_categories_identifiable(self, attributor):
        """测试所有5种错误分类都能被识别"""
        test_cases = {
            ErrorCategory.DATA_ISSUE: ["数据质量差", "格式错误"],
            ErrorCategory.STRATEGY_ISSUE: ["算法错误", "逻辑错误"],
            ErrorCategory.PARAMETER_ISSUE: ["参数错误", "配置错误"],
            ErrorCategory.ENVIRONMENT_ISSUE: ["网络错误", "连接超时"],
        }

        for expected_category, errors in test_cases.items():
            record = ExperienceRecord(
                task_id=f"test_{expected_category.value}",
                task_type=TaskType.CRAWLER,
                task_name=f"test_{expected_category.value}",
                status=TaskStatus.FAILED,
                errors=errors,
            )
            result = attributor.attribute_error(record)
            assert result.error_category == expected_category, (
                f"期望 {expected_category.value}，实际 {result.error_category.value}"
            )


class TestExperienceSummarizer:
    """经验总结器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def summarizer(self, pool):
        """创建经验总结器"""
        return ExperienceSummarizer(pool)

    @pytest.fixture
    def pool_with_100_records(self, pool):
        """创建包含100条经验记录的数据池"""
        task_types = [TaskType.CRAWLER, TaskType.PROCESSOR, TaskType.ANALYZER, TaskType.ANNOTATOR, TaskType.VALIDATOR]

        for i in range(100):
            task_type = task_types[i % len(task_types)]
            if i % 3 == 0:
                status = TaskStatus.FAILED
                errors = [f"数据质量差_{i % 3}", f"格式错误"] if i % 5 == 0 else [f"网络错误_{i % 4}"]
                warnings = [f"warning_{i}"] if i % 2 == 0 else []
                quality = 0.2 + (i % 20) * 0.01
            else:
                status = TaskStatus.SUCCESS
                errors = []
                warnings = [f"warning_{i}"] if i % 7 == 0 else []
                quality = 0.7 + (i % 20) * 0.01

            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=task_type,
                task_name=f"task_name_{i}",
                status=status,
                duration_ms=500.0 + (i % 50) * 50.0,
                performance_metrics={
                    "accuracy": 0.5 + (i % 40) * 0.01,
                    "efficiency": 0.4 + (i % 40) * 0.012,
                    "data_quality": 0.6 + (i % 30) * 0.01,
                },
                input_summary=f"input_{i}",
                output_summary=f"output_{i}_result",
                errors=errors,
                warnings=warnings,
                quality_score=quality,
                metadata={"index": i, "batch": i // 10},
            )
            pool.add_record(record)

        return pool

    def test_extract_heuristics_empty_pool(self, summarizer):
        """测试空数据池提取模式"""
        heuristics = summarizer.extract_heuristics()
        assert heuristics == []

    def test_extract_heuristics_100_records(self, summarizer, pool_with_100_records):
        """测试从100条经验中提取模式"""
        heuristics = summarizer.extract_heuristics(min_frequency=3)

        assert len(heuristics) >= 3
        assert all(isinstance(h, Heuristic) for h in heuristics)

        pattern_types = set(h.pattern_type for h in heuristics)
        assert len(pattern_types) >= 2

    def test_extract_success_patterns(self, summarizer, pool_with_100_records):
        """测试提取成功模式"""
        all_exps = pool_with_100_records.query({}, limit=200)
        patterns = summarizer._extract_success_patterns(all_exps)

        assert isinstance(patterns, list)
        assert all(h.pattern_type == "success_pattern" for h in patterns)
        assert all(h.frequency >= 0 for h in patterns)

    def test_extract_failure_patterns(self, summarizer, pool_with_100_records):
        """测试提取失败模式"""
        all_exps = pool_with_100_records.query({}, limit=200)
        patterns = summarizer._extract_failure_patterns(all_exps)

        assert isinstance(patterns, list)
        assert all(h.pattern_type == "failure_pattern" for h in patterns)

    def test_extract_best_practices(self, summarizer, pool_with_100_records):
        """测试提取最佳实践"""
        all_exps = pool_with_100_records.query({}, limit=200)
        patterns = summarizer._extract_best_practices(all_exps)

        assert isinstance(patterns, list)
        assert all(h.pattern_type == "best_practice" for h in patterns)

    def test_extract_pitfalls(self, summarizer, pool_with_100_records):
        """测试提取陷阱模式"""
        all_exps = pool_with_100_records.query({}, limit=200)
        patterns = summarizer._extract_pitfalls(all_exps)

        assert isinstance(patterns, list)
        assert all(h.pattern_type == "pitfall" for h in patterns)

    def test_heuristic_has_frequency_and_features(self, summarizer, pool_with_100_records):
        """测试模式包含频率、特征和适用场景"""
        heuristics = summarizer.extract_heuristics(min_frequency=3)

        for h in heuristics:
            assert h.frequency >= 0
            assert isinstance(h.typical_features, list)
            assert isinstance(h.applicable_scenarios, list)
            assert isinstance(h.related_tasks, list)
            assert 0.0 <= h.confidence <= 1.0
            assert h.heuristic_id.startswith("heur_")
            assert len(h.heuristic_id) == len("heur_") + 8

    def test_success_and_failure_patterns_distinct(self, summarizer, pool_with_100_records):
        """测试成功模式和失败模式分别识别"""
        heuristics = summarizer.extract_heuristics(min_frequency=3)

        success_patterns = [h for h in heuristics if h.pattern_type == "success_pattern"]
        failure_patterns = [h for h in heuristics if h.pattern_type == "failure_pattern"]

        assert len(success_patterns) >= 1
        assert len(failure_patterns) >= 1

    def test_summarize_period_empty(self, summarizer):
        """测试空周期总结"""
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        summary = summarizer.summarize_period(start, end)

        assert summary["total_records"] == 0
        assert "message" in summary["overview"]

    def test_summarize_period_with_data(self, pool, summarizer):
        """测试有数据的周期总结"""
        now = datetime.now()
        for i in range(20):
            record = ExperienceRecord(
                task_id=f"period_task_{i}",
                task_type=TaskType.CRAWLER if i % 2 == 0 else TaskType.PROCESSOR,
                task_name=f"period_{i}",
                status=TaskStatus.SUCCESS if i % 3 != 0 else TaskStatus.FAILED,
                timestamp=now - timedelta(days=i),
                errors=["数据质量差"] if i % 3 == 0 else [],
                quality_score=0.8 if i % 3 != 0 else 0.3,
                duration_ms=1000.0 + i * 50,
            )
            pool.add_record(record)

        start = now - timedelta(days=20)
        end = now + timedelta(days=1)
        summary = summarizer.summarize_period(start, end)

        assert summary["total_records"] == 20
        assert "success_count" in summary["overview"]
        assert "failed_count" in summary["overview"]
        assert "success_rate" in summary["overview"]
        assert "avg_duration_ms" in summary["overview"]
        assert isinstance(summary["success_patterns"], list)
        assert isinstance(summary["failure_patterns"], list)
        assert isinstance(summary["key_lessons"], list)
        assert isinstance(summary["improvement_suggestions"], list)
        assert len(summary["improvement_suggestions"]) > 0

    def test_summarize_period_filters_correctly(self, pool, summarizer):
        """测试周期总结的时间过滤"""
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

        start = now - timedelta(days=7)
        end = now + timedelta(days=1)
        summary = summarizer.summarize_period(start, end)

        assert summary["total_records"] == 1

    def test_get_top_insights_empty(self, summarizer):
        """测试空数据池的Top洞察"""
        insights = summarizer.get_top_insights()
        assert insights == []

    def test_get_top_insights_with_data(self, summarizer, pool_with_100_records):
        """测试有数据的Top洞察"""
        insights = summarizer.get_top_insights(top_n=5)

        assert isinstance(insights, list)
        assert len(insights) <= 5
        assert len(insights) >= 1

        for insight in insights:
            assert "heuristic_id" in insight
            assert "name" in insight
            assert "pattern_type" in insight
            assert "frequency" in insight
            assert "confidence" in insight
            assert "importance_score" in insight
            assert "typical_features" in insight
            assert "applicable_scenarios" in insight
            assert "related_tasks" in insight

    def test_get_top_insights_sorted(self, summarizer, pool_with_100_records):
        """测试Top洞察按重要性排序"""
        insights = summarizer.get_top_insights(top_n=10)

        if len(insights) >= 2:
            scores = [i["importance_score"] for i in insights]
            assert scores == sorted(scores, reverse=True)

    def test_min_frequency_threshold(self, summarizer, pool_with_100_records):
        """测试最小频率阈值"""
        low_freq = summarizer.extract_heuristics(min_frequency=100)
        high_freq = summarizer.extract_heuristics(min_frequency=3)

        assert len(low_freq) <= len(high_freq)

    def test_heuristic_id_format(self, summarizer, pool_with_100_records):
        """测试模式ID格式"""
        heuristics = summarizer.extract_heuristics(min_frequency=3)

        for h in heuristics:
            assert h.heuristic_id.startswith("heur_")
            assert len(h.heuristic_id) == 13

    def test_boundary_all_success(self, pool, summarizer):
        """测试边界情况：全部成功"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"success_task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"success_{i}",
                status=TaskStatus.SUCCESS,
                quality_score=0.9,
                duration_ms=500.0,
            )
            pool.add_record(record)

        heuristics = summarizer.extract_heuristics(min_frequency=3)
        assert len(heuristics) >= 1

        failure_patterns = [h for h in heuristics if h.pattern_type == "failure_pattern"]
        assert len(failure_patterns) == 0

    def test_boundary_all_failure(self, pool, summarizer):
        """测试边界情况：全部失败"""
        for i in range(10):
            record = ExperienceRecord(
                task_id=f"fail_task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"fail_{i}",
                status=TaskStatus.FAILED,
                errors=["数据质量差", "格式错误"],
                quality_score=0.2,
                duration_ms=500.0,
            )
            pool.add_record(record)

        heuristics = summarizer.extract_heuristics(min_frequency=3)
        assert len(heuristics) >= 1

        success_patterns = [h for h in heuristics if h.pattern_type == "success_pattern"]
        assert len(success_patterns) == 0

    def test_boundary_single_record(self, pool, summarizer):
        """测试边界情况：单条记录"""
        record = ExperienceRecord(
            task_id="single_task",
            task_type=TaskType.CRAWLER,
            task_name="single",
            status=TaskStatus.SUCCESS,
            quality_score=0.8,
        )
        pool.add_record(record)

        heuristics = summarizer.extract_heuristics(min_frequency=3)
        assert len(heuristics) == 0
