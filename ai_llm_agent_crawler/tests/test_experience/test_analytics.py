"""
经验分析工具集单元测试

测试趋势分析器、模式挖掘器和对比分析器的各功能。
"""

from datetime import datetime, timedelta

import pytest

from ai_llm_agent_crawler.experience import (
    ComparisonResult,
    ExperienceComparator,
    ExperienceDataPool,
    ExperienceRecord,
    PatternMiner,
    TaskStatus,
    TaskType,
    TrendAnalysisResult,
    TrendAnalyzer,
    TrendPoint,
)


class TestTrendPoint:
    """趋势点模型测试"""

    def test_create_trend_point(self):
        """测试创建趋势点"""
        point = TrendPoint(
            timestamp=datetime.now(),
            overall_score=0.75,
            dimension_scores={"accuracy": 0.8, "efficiency": 0.7},
            experience_count=10,
        )

        assert isinstance(point.timestamp, datetime)
        assert point.overall_score == 0.75
        assert point.dimension_scores["accuracy"] == 0.8
        assert point.experience_count == 10
        assert point.is_inflection is False
        assert point.inflection_type is None

    def test_trend_point_with_inflection(self):
        """测试带拐点标记的趋势点"""
        point = TrendPoint(
            timestamp=datetime.now(),
            overall_score=0.9,
            is_inflection=True,
            inflection_type="peak",
            description="峰值点",
        )

        assert point.is_inflection is True
        assert point.inflection_type == "peak"
        assert point.description == "峰值点"


class TestTrendAnalysisResult:
    """趋势分析结果模型测试"""

    def test_create_result_defaults(self):
        """测试创建趋势分析结果（默认值）"""
        result = TrendAnalysisResult(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
        )

        assert result.total_points == 0
        assert result.overall_trend == "stable"
        assert result.trend_slope == 0.0
        assert result.trend_points == []
        assert result.dimension_trends == {}
        assert result.inflection_points == []
        assert result.key_findings == []
        assert result.prediction == {}


class TestComparisonResult:
    """对比分析结果模型测试"""

    def test_create_comparison_result(self):
        """测试创建对比分析结果"""
        result = ComparisonResult(
            comparison_type="task_type",
            group_a_name="crawler",
            group_b_name="processor",
            metrics_a={"success_rate": 0.8},
            metrics_b={"success_rate": 0.6},
            differences={"success_rate": 0.2},
            winner="A",
            summary="crawler表现更优",
        )

        assert result.comparison_type == "task_type"
        assert result.group_a_name == "crawler"
        assert result.winner == "A"
        assert result.differences["success_rate"] == 0.2


class TestTrendAnalyzer:
    """趋势分析器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def analyzer(self, pool):
        """创建趋势分析器"""
        return TrendAnalyzer(pool)

    @pytest.fixture
    def pool_with_trend_data(self, pool):
        """创建包含趋势数据的池（15天上升趋势）"""
        now = datetime.now()
        for day in range(15):
            base_quality = 0.4 + day * 0.03
            base_acc = 0.5 + day * 0.025
            base_eff = 0.45 + day * 0.02
            for i in range(3):
                record = ExperienceRecord(
                    task_id=f"task_{day}_{i}",
                    task_type=TaskType.CRAWLER if i % 2 == 0 else TaskType.PROCESSOR,
                    task_name=f"trend_task_{day}_{i}",
                    status=TaskStatus.SUCCESS if i < 2 else TaskStatus.FAILED,
                    timestamp=now - timedelta(days=14 - day, hours=i),
                    duration_ms=500.0 + day * 10,
                    performance_metrics={
                        "accuracy": min(base_acc + i * 0.02, 1.0),
                        "efficiency": min(base_eff + i * 0.01, 1.0),
                    },
                    input_summary=f"input_{day}_{i}",
                    output_summary=f"output_{day}_{i}",
                    errors=[f"error_{day}"] if i == 2 else [],
                    warnings=[f"warn_{day}"] if i == 1 else [],
                    quality_score=min(base_quality + i * 0.05, 1.0),
                )
                pool.add_record(record)
        return pool

    def test_analyze_trend_with_sufficient_data(self, analyzer, pool_with_trend_data):
        """测试有10个以上时间点时能生成趋势分析报告"""
        result = analyzer.analyze_trend(days=30, granularity="day")

        assert isinstance(result, TrendAnalysisResult)
        assert result.total_points >= 10
        assert len(result.trend_points) >= 10
        assert result.start_date < result.end_date

    def test_trend_type_improving(self, analyzer, pool_with_trend_data):
        """测试趋势类型判断正确（improving）"""
        result = analyzer.analyze_trend(days=30, granularity="day")

        assert result.overall_trend == "improving"
        assert result.trend_slope > 0

    def test_trend_type_declining(self, analyzer, pool):
        """测试趋势类型判断正确（declining）"""
        now = datetime.now()
        for day in range(12):
            base_quality = 0.9 - day * 0.05
            for i in range(2):
                record = ExperienceRecord(
                    task_id=f"decline_{day}_{i}",
                    task_type=TaskType.ANALYZER,
                    task_name=f"decline_{day}_{i}",
                    status=TaskStatus.SUCCESS if day < 6 else TaskStatus.FAILED,
                    timestamp=now - timedelta(days=11 - day),
                    performance_metrics={
                        "accuracy": max(0.9 - day * 0.05, 0.2),
                        "efficiency": max(0.85 - day * 0.04, 0.2),
                    },
                    quality_score=max(base_quality, 0.1),
                )
                pool.add_record(record)

        result = analyzer.analyze_trend(days=30, granularity="day")
        assert result.overall_trend == "declining"
        assert result.trend_slope < 0

    def test_trend_type_stable(self, analyzer, pool):
        """测试趋势类型判断正确（stable）"""
        now = datetime.now()
        for day in range(10):
            for i in range(2):
                record = ExperienceRecord(
                    task_id=f"stable_{day}_{i}",
                    task_type=TaskType.CRAWLER,
                    task_name=f"stable_{day}_{i}",
                    status=TaskStatus.SUCCESS,
                    timestamp=now - timedelta(days=9 - day),
                    performance_metrics={
                        "accuracy": 0.7 + (day % 3) * 0.01,
                        "efficiency": 0.65 + (day % 2) * 0.01,
                    },
                    quality_score=0.7 + (day % 3) * 0.01,
                )
                pool.add_record(record)

        result = analyzer.analyze_trend(days=30, granularity="day")
        assert result.overall_trend == "stable"

    def test_inflection_points_detection(self, analyzer, pool):
        """测试拐点检测功能正常"""
        now = datetime.now()
        scores = [0.4, 0.5, 0.6, 0.7, 0.85, 0.9, 0.88, 0.75, 0.6, 0.5, 0.45, 0.55, 0.7, 0.8, 0.85]
        for day, score in enumerate(scores):
            for i in range(2):
                record = ExperienceRecord(
                    task_id=f"inflect_{day}_{i}",
                    task_type=TaskType.CRAWLER,
                    task_name=f"inflect_{day}_{i}",
                    status=TaskStatus.SUCCESS if score > 0.5 else TaskStatus.FAILED,
                    timestamp=now - timedelta(days=len(scores) - 1 - day),
                    performance_metrics={
                        "accuracy": score,
                        "efficiency": score * 0.9,
                    },
                    quality_score=score,
                )
                pool.add_record(record)

        result = analyzer.analyze_trend(days=30, granularity="day")
        assert isinstance(result.inflection_points, list)
        assert len(result.inflection_points) >= 1
        for ip in result.inflection_points:
            assert ip.is_inflection is True
            assert ip.inflection_type in ("peak", "trough", "breaking")

    def test_dimension_trends_computed(self, analyzer, pool_with_trend_data):
        """测试各维度趋势分别计算"""
        result = analyzer.analyze_trend(days=30, granularity="day")

        assert isinstance(result.dimension_trends, dict)
        assert len(result.dimension_trends) >= 2
        for dim, trend in result.dimension_trends.items():
            assert trend in ("improving", "declining", "stable")

    def test_key_findings_not_empty(self, analyzer, pool_with_trend_data):
        """测试关键发现列表不为空"""
        result = analyzer.analyze_trend(days=30, granularity="day")

        assert len(result.key_findings) > 0
        assert all(isinstance(f, str) for f in result.key_findings)

    def test_prediction_function(self, analyzer, pool_with_trend_data):
        """测试预测功能正常"""
        result = analyzer.analyze_trend(days=30, granularity="day")

        pred = result.prediction
        assert "periods" in pred
        assert "predictions" in pred
        assert "confidence" in pred
        assert "method" in pred
        assert isinstance(pred["predictions"], list)
        assert len(pred["predictions"]) == 3
        for p in pred["predictions"]:
            assert "period_index" in p
            assert "predicted_score" in p
            assert 0.0 <= p["predicted_score"] <= 1.0

    def test_predict_next_period_direct(self, analyzer, pool_with_trend_data):
        """测试直接调用预测方法"""
        result = analyzer.analyze_trend(days=30, granularity="day")
        pred = analyzer.predict_next_period(result, periods=5)

        assert pred["periods"] == 5
        assert len(pred["predictions"]) == 5
        assert 0.0 <= pred["confidence"] <= 1.0

    def test_different_granularity_week(self, analyzer, pool_with_trend_data):
        """测试不同粒度（week）正常工作"""
        result = analyzer.analyze_trend(days=30, granularity="week")

        assert isinstance(result, TrendAnalysisResult)
        assert result.total_points >= 1
        assert len(result.trend_points) >= 1

    def test_empty_data_handling(self, analyzer, pool):
        """测试空数据时有合理处理"""
        result = analyzer.analyze_trend(days=30, granularity="day")

        assert result.total_points == 0
        assert result.trend_points == []
        assert len(result.key_findings) >= 1
        assert "无足够经验数据" in result.key_findings[0]

    def test_single_data_point(self, analyzer, pool):
        """测试单个数据点的处理"""
        record = ExperienceRecord(
            task_id="single",
            task_type=TaskType.CRAWLER,
            task_name="single",
            status=TaskStatus.SUCCESS,
            quality_score=0.8,
        )
        pool.add_record(record)

        result = analyzer.analyze_trend(days=30, granularity="day")
        assert isinstance(result, TrendAnalysisResult)
        assert result.total_points >= 0

    def test_aggregate_by_period_hour(self, analyzer, pool):
        """测试按小时聚合"""
        now = datetime.now()
        for hour in range(5):
            record = ExperienceRecord(
                task_id=f"hour_{hour}",
                task_type=TaskType.CRAWLER,
                task_name=f"hour_{hour}",
                status=TaskStatus.SUCCESS,
                timestamp=now - timedelta(hours=4 - hour),
            )
            pool.add_record(record)

        exps = pool.query({}, limit=100)
        aggregated = analyzer._aggregate_by_period(exps, "hour")
        assert len(aggregated) >= 3

    def test_compute_period_score_empty(self, analyzer):
        """测试空经验列表的评分计算"""
        score, dims = analyzer._compute_period_score([])
        assert score == 0.0
        assert dims == {}

    def test_compute_trend_slope_rising(self, analyzer):
        """测试上升趋势斜率计算"""
        points = [
            TrendPoint(timestamp=datetime(2024, 1, i + 1), overall_score=0.5 + i * 0.1)
            for i in range(5)
        ]
        slope = analyzer._compute_trend_slope(points)
        assert slope > 0

    def test_compute_trend_slope_falling(self, analyzer):
        """测试下降趋势斜率计算"""
        points = [
            TrendPoint(timestamp=datetime(2024, 1, i + 1), overall_score=0.9 - i * 0.1)
            for i in range(5)
        ]
        slope = analyzer._compute_trend_slope(points)
        assert slope < 0

    def test_generate_trend_description(self, analyzer):
        """测试趋势描述生成"""
        assert analyzer._generate_trend_description(0.01) == "improving"
        assert analyzer._generate_trend_description(-0.01) == "declining"
        assert analyzer._generate_trend_description(0.001) == "stable"
        assert analyzer._generate_trend_description(-0.001) == "stable"


class TestPatternMiner:
    """模式挖掘器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def miner(self, pool):
        """创建模式挖掘器"""
        return PatternMiner(pool)

    @pytest.fixture
    def pool_with_100_records(self, pool):
        """创建包含100条经验记录的数据池"""
        task_types = [
            TaskType.CRAWLER,
            TaskType.PROCESSOR,
            TaskType.ANALYZER,
            TaskType.ANNOTATOR,
            TaskType.VALIDATOR,
        ]

        for i in range(100):
            task_type = task_types[i % len(task_types)]
            if i % 3 == 0:
                status = TaskStatus.FAILED
                errors = [f"数据质量差_{i % 3}", "格式错误"] if i % 5 == 0 else [f"网络错误_{i % 4}"]
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

    def test_mine_patterns_from_100_records(self, miner, pool_with_100_records):
        """测试从100条以上经验中能挖掘出至少3种模式"""
        patterns = miner.mine_patterns(min_frequency=3)

        assert len(patterns) >= 3
        assert all(isinstance(p, dict) for p in patterns)

    def test_success_and_failure_patterns_distinct(self, miner, pool_with_100_records):
        """测试成功模式和失败模式分别识别"""
        patterns = miner.mine_patterns(min_frequency=3)

        success_patterns = [p for p in patterns if p["pattern_type"] == "success_pattern"]
        failure_patterns = [p for p in patterns if p["pattern_type"] == "failure_pattern"]

        assert len(success_patterns) >= 1
        assert len(failure_patterns) >= 1

    def test_patterns_have_frequency_and_features(self, miner, pool_with_100_records):
        """测试模式包含频率、特征、适用场景"""
        patterns = miner.mine_patterns(min_frequency=3)

        for p in patterns:
            assert "frequency" in p
            assert p["frequency"] >= 0
            assert "typical_features" in p
            assert isinstance(p["typical_features"], list)
            assert len(p["typical_features"]) > 0
            assert "applicable_scenarios" in p
            assert isinstance(p["applicable_scenarios"], list)
            assert "name" in p
            assert "confidence" in p
            assert 0.0 <= p["confidence"] <= 1.0

    def test_high_performing_combinations(self, miner, pool_with_100_records):
        """测试高绩效组合识别正常"""
        combos = miner.identify_high_performing_combinations(top_n=5)

        assert isinstance(combos, list)
        assert len(combos) >= 1
        assert len(combos) <= 5

        for c in combos:
            assert "task_type" in c
            assert "success_rate" in c
            assert "combined_score" in c
            assert 0.0 <= c["success_rate"] <= 1.0

        if len(combos) >= 2:
            scores = [c["combined_score"] for c in combos]
            assert scores == sorted(scores, reverse=True)

    def test_low_performing_combinations(self, miner, pool_with_100_records):
        """测试低绩效组合识别正常"""
        combos = miner.identify_low_performing_combinations(top_n=5)

        assert isinstance(combos, list)
        assert len(combos) >= 1
        assert len(combos) <= 5

        for c in combos:
            assert "task_type" in c
            assert "fail_rate" in c
            assert "combined_score" in c
            assert 0.0 <= c["fail_rate"] <= 1.0

    def test_find_correlations(self, miner, pool_with_100_records):
        """测试相关性计算功能正常"""
        result = miner.find_correlations("accuracy", "efficiency")

        assert isinstance(result, dict)
        assert "correlation" in result
        assert "sample_size" in result
        assert "method" in result
        assert -1.0 <= result["correlation"] <= 1.0
        assert result["sample_size"] > 0

    def test_correlation_strength_and_direction(self, miner, pool_with_100_records):
        """测试相关性强度和方向描述"""
        result = miner.find_correlations("accuracy", "efficiency")

        assert "correlation_strength" in result
        assert "correlation_direction" in result
        assert result["correlation_strength"] in ("极弱", "弱", "中等", "强", "极强")
        assert result["correlation_direction"] in ("正相关", "负相关", "无相关")

    def test_correlation_with_insufficient_data(self, miner, pool):
        """测试数据不足时的相关性计算"""
        record = ExperienceRecord(
            task_id="only_one",
            task_type=TaskType.CRAWLER,
            task_name="only_one",
            status=TaskStatus.SUCCESS,
            performance_metrics={"accuracy": 0.9, "efficiency": 0.8},
        )
        pool.add_record(record)

        result = miner.find_correlations("accuracy", "efficiency")
        assert result["sample_size"] < 3
        assert "样本量不足" in result.get("message", "")

    def test_patterns_interpretable(self, miner, pool_with_100_records):
        """测试挖掘结果具有可解释性"""
        patterns = miner.mine_patterns(min_frequency=3)

        for p in patterns:
            assert isinstance(p["name"], str)
            assert len(p["name"]) > 0
            assert len(p["typical_features"]) > 0
            assert all(isinstance(f, str) for f in p["typical_features"])
            assert len(p["applicable_scenarios"]) > 0

    def test_mine_success_patterns_direct(self, miner, pool_with_100_records):
        """测试直接调用成功模式挖掘"""
        exps = pool_with_100_records.query({}, limit=200)
        patterns = miner._mine_success_patterns(exps, min_freq=3)

        assert isinstance(patterns, list)
        assert all(p["pattern_type"] == "success_pattern" for p in patterns)

    def test_mine_failure_patterns_direct(self, miner, pool_with_100_records):
        """测试直接调用失败模式挖掘"""
        exps = pool_with_100_records.query({}, limit=200)
        patterns = miner._mine_failure_patterns(exps, min_freq=3)

        assert isinstance(patterns, list)
        assert all(p["pattern_type"] == "failure_pattern" for p in patterns)

    def test_empty_pool_patterns(self, miner, pool):
        """测试空池模式挖掘"""
        patterns = miner.mine_patterns(min_frequency=3)
        assert patterns == []

    def test_empty_pool_high_combinations(self, miner, pool):
        """测试空池高绩效组合"""
        combos = miner.identify_high_performing_combinations()
        assert combos == []

    def test_empty_pool_low_combinations(self, miner, pool):
        """测试空池低绩效组合"""
        combos = miner.identify_low_performing_combinations()
        assert combos == []


class TestExperienceComparator:
    """经验对比分析器测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def comparator(self, pool):
        """创建对比分析器"""
        return ExperienceComparator(pool)

    @pytest.fixture
    def pool_with_comparison_data(self, pool):
        """创建用于对比测试的数据池"""
        for i in range(30):
            record = ExperienceRecord(
                task_id=f"crawler_good_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"crawler_task_{i}",
                status=TaskStatus.SUCCESS if i < 22 else TaskStatus.FAILED,
                duration_ms=300.0 + i * 10,
                performance_metrics={
                    "accuracy": 0.75 + (i % 10) * 0.02,
                    "efficiency": 0.7 + (i % 10) * 0.015,
                },
                errors=["网络超时"] if i >= 22 else [],
                quality_score=0.75 + (i % 10) * 0.015 if i < 22 else 0.3,
            )
            pool.add_record(record)

        for i in range(30):
            record = ExperienceRecord(
                task_id=f"processor_mid_{i}",
                task_type=TaskType.PROCESSOR,
                task_name=f"processor_task_{i}",
                status=TaskStatus.SUCCESS if i < 15 else TaskStatus.FAILED,
                duration_ms=800.0 + i * 15,
                performance_metrics={
                    "accuracy": 0.6 + (i % 10) * 0.02,
                    "efficiency": 0.55 + (i % 10) * 0.02,
                },
                errors=["数据格式错误"] if i >= 15 else [],
                quality_score=0.65 + (i % 10) * 0.01 if i < 15 else 0.25,
            )
            pool.add_record(record)

        now = datetime.now()
        for i in range(20):
            record = ExperienceRecord(
                task_id=f"recent_{i}",
                task_type=TaskType.ANALYZER,
                task_name=f"recent_{i}",
                status=TaskStatus.SUCCESS if i < 16 else TaskStatus.FAILED,
                timestamp=now - timedelta(days=5 - (i // 4)),
                performance_metrics={"accuracy": 0.8, "efficiency": 0.75},
                quality_score=0.8 if i < 16 else 0.3,
            )
            pool.add_record(record)

        return pool

    def test_compare_by_task_type(self, comparator, pool_with_comparison_data):
        """测试按任务类型对比正常"""
        result = comparator.compare_by_task_type("crawler", "processor")

        assert isinstance(result, ComparisonResult)
        assert result.comparison_type == "task_type"
        assert result.group_a_name == "crawler"
        assert result.group_b_name == "processor"
        assert "success_rate" in result.metrics_a
        assert "success_rate" in result.metrics_b
        assert "success_rate" in result.differences

    def test_compare_by_time_range(self, comparator, pool_with_comparison_data):
        """测试按时间范围对比正常"""
        now = datetime.now()
        start_a = now - timedelta(days=7)
        end_a = now - timedelta(days=3)
        start_b = now - timedelta(days=3)
        end_b = now + timedelta(days=1)

        result = comparator.compare_by_time_range(start_a, end_a, start_b, end_b)

        assert isinstance(result, ComparisonResult)
        assert result.comparison_type == "time_range"
        assert "~" in result.group_a_name
        assert "~" in result.group_b_name

    def test_compare_by_status(self, comparator, pool_with_comparison_data):
        """测试按状态对比正常"""
        result = comparator.compare_by_status("success", "failed")

        assert isinstance(result, ComparisonResult)
        assert result.comparison_type == "status"
        assert result.group_a_name == "success"
        assert result.group_b_name == "failed"

    def test_differences_and_winner(self, comparator, pool_with_comparison_data):
        """测试对比结果包含差异值和优胜方"""
        result = comparator.compare_by_task_type("crawler", "processor")

        assert isinstance(result.differences, dict)
        assert len(result.differences) > 0
        assert result.winner in ("A", "B", None)

    def test_summary_reasonable(self, comparator, pool_with_comparison_data):
        """测试总结描述合理"""
        result = comparator.compare_by_task_type("crawler", "processor")

        assert isinstance(result.summary, str)
        assert len(result.summary) > 0
        assert "crawler" in result.summary

    def test_compute_group_metrics(self, comparator, pool_with_comparison_data):
        """测试组指标计算"""
        exps = pool_with_comparison_data.query({"task_type": "crawler"}, limit=100)
        metrics = comparator._compute_group_metrics(exps)

        assert "total_count" in metrics
        assert "success_rate" in metrics
        assert "fail_rate" in metrics
        assert "avg_accuracy" in metrics
        assert "avg_efficiency" in metrics
        assert "avg_duration_ms" in metrics
        assert "avg_quality_score" in metrics
        assert "error_rate" in metrics
        assert 0.0 <= metrics["success_rate"] <= 1.0
        assert metrics["total_count"] == 30

    def test_determine_winner_a_better(self, comparator):
        """测试A组更好时的优胜判断"""
        metrics_a = {
            "total_count": 100,
            "success_rate": 0.9,
            "avg_quality_score": 0.85,
            "avg_accuracy": 0.88,
            "avg_efficiency": 0.82,
        }
        metrics_b = {
            "total_count": 100,
            "success_rate": 0.6,
            "avg_quality_score": 0.55,
            "avg_accuracy": 0.58,
            "avg_efficiency": 0.52,
        }
        winner = comparator._determine_winner(metrics_a, metrics_b)
        assert winner == "A"

    def test_determine_winner_b_better(self, comparator):
        """测试B组更好时的优胜判断"""
        metrics_a = {
            "total_count": 100,
            "success_rate": 0.5,
            "avg_quality_score": 0.5,
            "avg_accuracy": 0.5,
            "avg_efficiency": 0.5,
        }
        metrics_b = {
            "total_count": 100,
            "success_rate": 0.85,
            "avg_quality_score": 0.8,
            "avg_accuracy": 0.82,
            "avg_efficiency": 0.78,
        }
        winner = comparator._determine_winner(metrics_a, metrics_b)
        assert winner == "B"

    def test_determine_winner_tie(self, comparator):
        """测试两组相近时无优胜方"""
        metrics = {
            "total_count": 100,
            "success_rate": 0.7,
            "avg_quality_score": 0.7,
            "avg_accuracy": 0.7,
            "avg_efficiency": 0.7,
        }
        winner = comparator._determine_winner(metrics, metrics)
        assert winner is None

    def test_empty_groups_comparison(self, comparator, pool):
        """测试空组对比"""
        result = comparator.compare_by_task_type("nonexistent_a", "nonexistent_b")

        assert result.metrics_a["total_count"] == 0
        assert result.metrics_b["total_count"] == 0
        assert result.winner is None
