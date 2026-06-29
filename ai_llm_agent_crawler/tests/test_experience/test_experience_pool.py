"""
经验数据池单元测试

测试经验记录模型、数据池的核心功能。
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from ai_llm_agent_crawler.experience import (
    ExperienceDataPool,
    ExperienceRecord,
    ExperienceType,
    TaskStatus,
    TaskType,
)


class TestExperienceRecord:
    """经验记录模型测试"""

    def test_create_record_defaults(self):
        """测试创建记录（默认值）"""
        record = ExperienceRecord(
            task_id="task_001",
            task_type=TaskType.CRAWLER,
            task_name="test_crawl",
            status=TaskStatus.SUCCESS,
        )

        assert record.experience_id.startswith("exp_")
        assert record.task_id == "task_001"
        assert record.task_type == "crawler"
        assert record.task_name == "test_crawl"
        assert record.status == "success"
        assert isinstance(record.timestamp, datetime)
        assert record.duration_ms == 0.0
        assert record.performance_metrics == {}
        assert record.input_summary == ""
        assert record.output_summary == ""
        assert record.errors == []
        assert record.warnings == []
        assert record.quality_score is None
        assert record.metadata == {}

    def test_create_record_with_all_fields(self):
        """测试创建记录（所有字段）"""
        record = ExperienceRecord(
            experience_id="exp_custom_001",
            task_id="task_002",
            task_type=TaskType.PROCESSOR,
            task_name="data_process",
            status=TaskStatus.PARTIAL,
            duration_ms=1500.5,
            performance_metrics={"accuracy": 0.95, "efficiency": 0.8},
            input_summary="测试输入",
            output_summary="测试输出",
            errors=["error1", "error2"],
            warnings=["warning1"],
            quality_score=0.75,
            metadata={"key": "value"},
        )

        assert record.experience_id == "exp_custom_001"
        assert record.task_type == "processor"
        assert record.status == "partial"
        assert record.duration_ms == 1500.5
        assert record.performance_metrics["accuracy"] == 0.95
        assert record.errors == ["error1", "error2"]
        assert record.quality_score == 0.75
        assert record.metadata["key"] == "value"

    def test_unique_ids(self):
        """测试ID唯一性"""
        records = [
            ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=TaskStatus.SUCCESS,
            )
            for i in range(100)
        ]
        ids = [r.experience_id for r in records]
        assert len(set(ids)) == 100

    def test_to_dict_and_from_dict(self):
        """测试字典序列化和反序列化"""
        original = ExperienceRecord(
            task_id="task_001",
            task_type=TaskType.ANALYZER,
            task_name="analysis",
            status=TaskStatus.SUCCESS,
            duration_ms=100.0,
            performance_metrics={"accuracy": 0.9},
            input_summary="输入",
            output_summary="输出",
            errors=["e1"],
            warnings=["w1"],
            quality_score=0.8,
            metadata={"meta": "data"},
        )

        data = original.to_dict()
        assert isinstance(data, dict)
        assert data["task_id"] == "task_001"
        assert isinstance(data["timestamp"], str)

        restored = ExperienceRecord.from_dict(data)
        assert restored.experience_id == original.experience_id
        assert restored.task_id == original.task_id
        assert restored.task_type == original.task_type
        assert restored.status == original.status
        assert restored.duration_ms == original.duration_ms
        assert restored.quality_score == original.quality_score
        assert restored.errors == original.errors
        assert restored.metadata == original.metadata
        assert isinstance(restored.timestamp, datetime)


class TestExperienceDataPool:
    """经验数据池测试"""

    @pytest.fixture
    def pool(self):
        """创建空数据池"""
        return ExperienceDataPool()

    @pytest.fixture
    def sample_records(self):
        """创建示例记录列表"""
        records = []
        for i in range(10):
            status = TaskStatus.SUCCESS if i < 6 else TaskStatus.FAILED
            task_type = TaskType.CRAWLER if i < 5 else TaskType.PROCESSOR
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=task_type,
                task_name=f"task_name_{i}",
                status=status,
                duration_ms=100.0 * i,
                performance_metrics={
                    "accuracy": 0.5 + i * 0.05,
                    "efficiency": 0.4 + i * 0.06,
                },
                input_summary=f"input_{i}",
                output_summary=f"output_{i}",
                errors=[f"error_{i}"] if i % 3 == 0 else [],
                warnings=[f"warning_{i}"] if i % 2 == 0 else [],
            )
            records.append(record)
        return records

    def test_add_and_get_record(self, pool):
        """测试添加和查询记录"""
        record = ExperienceRecord(
            task_id="task_001",
            task_type=TaskType.CRAWLER,
            task_name="test",
            status=TaskStatus.SUCCESS,
        )

        record_id = pool.add_record(record)
        assert record_id == record.experience_id

        retrieved = pool.get_record(record_id)
        assert retrieved is not None
        assert retrieved.task_id == "task_001"
        assert retrieved.experience_id == record_id

    def test_get_nonexistent_record(self, pool):
        """测试查询不存在的记录"""
        result = pool.get_record("nonexistent_id")
        assert result is None

    def test_count_empty_pool(self, pool):
        """测试空池统计"""
        assert pool.count() == 0

    def test_count_with_records(self, pool, sample_records):
        """测试记录统计"""
        for record in sample_records:
            pool.add_record(record)

        assert pool.count() == 10

    def test_delete_record(self, pool, sample_records):
        """测试删除记录"""
        record = sample_records[0]
        pool.add_record(record)

        assert pool.count() == 1
        result = pool.delete_record(record.experience_id)
        assert result is True
        assert pool.count() == 0

    def test_delete_nonexistent_record(self, pool):
        """测试删除不存在的记录"""
        result = pool.delete_record("nonexistent")
        assert result is False

    def test_query_by_task_type(self, pool, sample_records):
        """测试按任务类型查询"""
        for record in sample_records:
            pool.add_record(record)

        results = pool.query({"task_type": "crawler"})
        assert len(results) == 5
        for r in results:
            assert r.task_type == "crawler"

    def test_query_by_status(self, pool, sample_records):
        """测试按状态查询"""
        for record in sample_records:
            pool.add_record(record)

        results = pool.query({"status": "success"})
        assert len(results) == 6
        for r in results:
            assert r.status == "success"

    def test_query_by_time_range(self, pool):
        """测试按时间范围查询"""
        now = datetime.now()

        for i in range(5):
            record = ExperienceRecord(
                task_id=f"task_{i}",
                task_type=TaskType.CRAWLER,
                task_name=f"task_{i}",
                status=TaskStatus.SUCCESS,
                timestamp=now - timedelta(hours=i),
            )
            pool.add_record(record)

        start_time = now - timedelta(hours=2.5)
        end_time = now - timedelta(minutes=30)
        results = pool.query({"time_range": {"start": start_time, "end": end_time}})

        assert len(results) == 2

    def test_query_by_quality_score(self, pool, sample_records):
        """测试按质量评分查询"""
        for record in sample_records:
            pool.add_record(record)

        pool.compute_quality_scores()

        results = pool.query({"min_quality_score": 0.5})
        assert len(results) > 0
        for r in results:
            assert r.quality_score >= 0.5

        results = pool.query({"max_quality_score": 0.5})
        assert len(results) > 0
        for r in results:
            assert r.quality_score <= 0.5

    def test_query_combined_filters(self, pool, sample_records):
        """测试组合过滤条件"""
        for record in sample_records:
            pool.add_record(record)

        results = pool.query(
            {"task_type": "crawler", "status": "success"}
        )
        assert len(results) > 0
        for r in results:
            assert r.task_type == "crawler"
            assert r.status == "success"

    def test_query_with_limit_and_offset(self, pool, sample_records):
        """测试分页查询"""
        for record in sample_records:
            pool.add_record(record)

        results = pool.query({}, limit=3, offset=0)
        assert len(results) == 3

        results = pool.query({}, limit=3, offset=8)
        assert len(results) == 2

    def test_query_empty_pool(self, pool):
        """测试空池查询"""
        results = pool.query({"task_type": "crawler"})
        assert results == []

    def test_deduplicate(self, pool):
        """测试去重功能"""
        base_record = ExperienceRecord(
            task_id="dup_task",
            task_type=TaskType.CRAWLER,
            task_name="dup_task_name",
            status=TaskStatus.SUCCESS,
            input_summary="same_input",
        )

        for i in range(5):
            dup_record = ExperienceRecord(
                task_id="dup_task",
                task_type=TaskType.CRAWLER,
                task_name=f"dup_name_{i}",
                status=TaskStatus.SUCCESS,
                input_summary="same_input",
                duration_ms=float(i * 100),
            )
            pool.add_record(dup_record)

        assert pool.count() == 5

        removed = pool.deduplicate()
        assert removed == 4
        assert pool.count() == 1

    def test_deduplicate_no_duplicates(self, pool, sample_records):
        """测试无重复数据的去重"""
        for record in sample_records:
            pool.add_record(record)

        removed = pool.deduplicate()
        assert removed == 0
        assert pool.count() == 10

    def test_deduplicate_empty_pool(self, pool):
        """测试空池去重"""
        removed = pool.deduplicate()
        assert removed == 0

    def test_compute_quality_scores(self, pool):
        """测试质量评分计算"""
        records = [
            ExperienceRecord(
                task_id="success_task",
                task_type=TaskType.CRAWLER,
                task_name="success",
                status=TaskStatus.SUCCESS,
                performance_metrics={"accuracy": 0.9, "efficiency": 0.8},
                errors=[],
                warnings=[],
            ),
            ExperienceRecord(
                task_id="failed_task",
                task_type=TaskType.PROCESSOR,
                task_name="failed",
                status=TaskStatus.FAILED,
                performance_metrics={"accuracy": 0.3, "efficiency": 0.2},
                errors=["err1", "err2", "err3"],
                warnings=["warn1"],
            ),
            ExperienceRecord(
                task_id="partial_task",
                task_type=TaskType.ANALYZER,
                task_name="partial",
                status=TaskStatus.PARTIAL,
                performance_metrics={"accuracy": 0.7, "efficiency": 0.6},
                errors=["err1"],
                warnings=[],
            ),
            ExperienceRecord(
                task_id="skipped_task",
                task_type=TaskType.VALIDATOR,
                task_name="skipped",
                status=TaskStatus.SKIPPED,
                performance_metrics={},
                errors=[],
                warnings=[],
            ),
        ]

        for record in records:
            pool.add_record(record)

        updated = pool.compute_quality_scores()
        assert updated == 4

        for record_id, record in pool._records.items():
            assert record.quality_score is not None
            assert 0.0 <= record.quality_score <= 1.0

        success_record = pool.get_record(records[0].experience_id)
        failed_record = pool.get_record(records[1].experience_id)

        assert success_record.quality_score > failed_record.quality_score

    def test_compute_quality_scores_idempotent(self, pool, sample_records):
        """测试质量评分计算的幂等性"""
        for record in sample_records:
            pool.add_record(record)

        first_update = pool.compute_quality_scores()
        assert first_update == 10

        second_update = pool.compute_quality_scores()
        assert second_update == 0

    def test_compute_quality_scores_error_penalty_cap(self, pool):
        """测试错误惩罚上限"""
        record = ExperienceRecord(
            task_id="many_errors",
            task_type=TaskType.CRAWLER,
            task_name="errors",
            status=TaskStatus.SUCCESS,
            performance_metrics={"accuracy": 1.0, "efficiency": 1.0},
            errors=["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"],
            warnings=[],
        )
        pool.add_record(record)
        pool.compute_quality_scores()

        result = pool.get_record(record.experience_id)
        assert result.quality_score >= 0.0
        base_score = 1.0 * 0.5 + 1.0 * 0.3 + 1.0 * 0.2
        expected_min = base_score - 0.5 - 0.2
        assert result.quality_score >= expected_min

    def test_export_to_dataframe(self, pool, sample_records):
        """测试导出为DataFrame"""
        for record in sample_records:
            pool.add_record(record)

        df = pool.export_to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "task_id" in df.columns
        assert "status" in df.columns

    def test_export_to_dataframe_empty(self, pool):
        """测试空池导出DataFrame"""
        df = pool.export_to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_export_and_load_json(self, pool, sample_records):
        """测试JSON导出和加载"""
        for record in sample_records:
            pool.add_record(record)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_success = pool.export_to_json(temp_path)
            assert export_success

            new_pool = ExperienceDataPool()
            loaded = new_pool.load_from_json(temp_path)
            assert loaded == 10
            assert new_pool.count() == 10

            original_ids = set(pool._records.keys())
            loaded_ids = set(new_pool._records.keys())
            assert original_ids == loaded_ids

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_json_nonexistent_file(self, pool):
        """测试加载不存在的JSON文件"""
        loaded = pool.load_from_json("/nonexistent/path/file.json")
        assert loaded == 0

    def test_get_statistics_empty(self, pool):
        """测试空池统计信息"""
        stats = pool.get_statistics()
        assert stats["total_records"] == 0
        assert stats["by_task_type"] == {}
        assert stats["by_status"] == {}
        assert stats["average_quality_score"] is None
        assert stats["avg_duration_ms"] == 0.0
        assert stats["total_errors"] == 0
        assert stats["total_warnings"] == 0

    def test_get_statistics_with_records(self, pool, sample_records):
        """测试统计信息"""
        for record in sample_records:
            pool.add_record(record)

        pool.compute_quality_scores()
        stats = pool.get_statistics()

        assert stats["total_records"] == 10
        assert "crawler" in stats["by_task_type"]
        assert stats["by_task_type"]["crawler"] == 5
        assert "success" in stats["by_status"]
        assert stats["by_status"]["success"] == 6
        assert stats["average_quality_score"] is not None
        assert 0.0 <= stats["average_quality_score"] <= 1.0
        assert stats["avg_duration_ms"] > 0
        assert stats["total_errors"] > 0
        assert stats["total_warnings"] > 0

    def test_count_with_filters(self, pool, sample_records):
        """测试带过滤条件的count"""
        for record in sample_records:
            pool.add_record(record)

        crawler_count = pool.count({"task_type": "crawler"})
        assert crawler_count == 5

        success_count = pool.count({"status": "success"})
        assert success_count == 6


class TestExperienceEnum:
    """经验类型枚举测试"""

    def test_experience_type_values(self):
        """测试经验类型枚举值"""
        assert ExperienceType.TASK_EXECUTION == "task_execution"
        assert ExperienceType.SKILL_USAGE == "skill_usage"
        assert ExperienceType.ERROR_OCCURRENCE == "error_occurrence"
        assert ExperienceType.OPTIMIZATION == "optimization"
        assert ExperienceType.LEARNING == "learning"
        assert ExperienceType.OTHER == "other"

    def test_task_type_values(self):
        """测试任务类型枚举值"""
        assert TaskType.CRAWLER == "crawler"
        assert TaskType.PROCESSOR == "processor"
        assert TaskType.ANALYZER == "analyzer"
        assert TaskType.ANNOTATOR == "annotator"
        assert TaskType.VALIDATOR == "validator"
        assert TaskType.OTHER == "other"

    def test_task_status_values(self):
        """测试任务状态枚举值"""
        assert TaskStatus.SUCCESS == "success"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.PARTIAL == "partial"
        assert TaskStatus.SKIPPED == "skipped"
