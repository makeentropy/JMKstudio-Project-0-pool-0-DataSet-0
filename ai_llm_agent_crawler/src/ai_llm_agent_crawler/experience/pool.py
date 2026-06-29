"""
经验数据池模块

提供经验记录的存储、查询、去重、质量评分计算等核心功能。
使用 pandas DataFrame 作为内存索引，支持本地文件系统持久化。
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ai_llm_agent_crawler.experience.models import ExperienceRecord
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ExperienceDataPool:
    """
    经验数据池

    管理经验记录的存储、查询、统计和质量评估。
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化经验数据池

        Args:
            storage_path: 数据存储路径，默认为内存模式
        """
        self._storage_path = Path(storage_path) if storage_path else None
        self._records: Dict[str, ExperienceRecord] = {}
        self._df: pd.DataFrame = pd.DataFrame()
        self._logger = get_logger(f"{__name__}.ExperienceDataPool")

        if self._storage_path:
            self._storage_path.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"经验数据池初始化，存储路径: {self._storage_path}")
        else:
            self._logger.info("经验数据池初始化（内存模式）")

    def _update_dataframe(self) -> None:
        """更新内存索引DataFrame"""
        if not self._records:
            self._df = pd.DataFrame()
            return

        records_list = [record.to_dict() for record in self._records.values()]
        self._df = pd.DataFrame(records_list)
        if "timestamp" in self._df.columns:
            self._df["timestamp"] = pd.to_datetime(self._df["timestamp"])

    def add_record(self, record: ExperienceRecord) -> str:
        """
        添加经验记录

        Args:
            record: 经验记录对象

        Returns:
            经验记录ID
        """
        self._records[record.experience_id] = record
        self._update_dataframe()
        self._logger.debug(f"添加经验记录: {record.experience_id}")
        return record.experience_id

    def get_record(self, experience_id: str) -> Optional[ExperienceRecord]:
        """
        按ID查询经验记录

        Args:
            experience_id: 经验记录ID

        Returns:
            经验记录对象，不存在则返回None
        """
        return self._records.get(experience_id)

    def query(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExperienceRecord]:
        """
        多条件过滤查询

        Args:
            filters: 过滤条件字典，支持：task_type, status, time_range (start/end),
                     min_quality_score, max_quality_score
            limit: 返回记录数上限
            offset: 偏移量

        Returns:
            经验记录列表
        """
        if self._df.empty:
            return []

        mask = pd.Series(True, index=self._df.index)

        if "task_type" in filters:
            mask &= self._df["task_type"] == filters["task_type"]

        if "status" in filters:
            mask &= self._df["status"] == filters["status"]

        if "time_range" in filters:
            time_range = filters["time_range"]
            if "start" in time_range:
                start = pd.to_datetime(time_range["start"])
                mask &= self._df["timestamp"] >= start
            if "end" in time_range:
                end = pd.to_datetime(time_range["end"])
                mask &= self._df["timestamp"] <= end

        if "min_quality_score" in filters:
            min_score = filters["min_quality_score"]
            mask &= (self._df["quality_score"].notna()) & (
                self._df["quality_score"] >= min_score
            )

        if "max_quality_score" in filters:
            max_score = filters["max_quality_score"]
            mask &= (self._df["quality_score"].notna()) & (
                self._df["quality_score"] <= max_score
            )

        filtered = self._df[mask]
        filtered = filtered.iloc[offset : offset + limit]

        results = []
        for _, row in filtered.iterrows():
            record_data = row.to_dict()
            record = ExperienceRecord.from_dict(record_data)
            results.append(record)

        return results

    def delete_record(self, experience_id: str) -> bool:
        """
        删除经验记录

        Args:
            experience_id: 经验记录ID

        Returns:
            删除是否成功
        """
        if experience_id in self._records:
            del self._records[experience_id]
            self._update_dataframe()
            self._logger.debug(f"删除经验记录: {experience_id}")
            return True
        return False

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计记录数

        Args:
            filters: 可选过滤条件

        Returns:
            记录数量
        """
        if not filters:
            return len(self._records)

        results = self.query(filters, limit=len(self._records))
        return len(results)

    def _compute_dedupe_hash(self, record: ExperienceRecord) -> str:
        """计算去重哈希值

        基于task_id + task_type + status + input_summary计算hash。

        Args:
            record: 经验记录

        Returns:
            哈希字符串
        """
        key = f"{record.task_id}|{record.task_type}|{record.status}|{record.input_summary}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def deduplicate(self) -> int:
        """
        去重

        基于task_id + task_type + status + input_summary判断重复，
        保留最早的记录，删除重复记录。

        Returns:
            删除的重复记录数
        """
        if len(self._records) <= 1:
            return 0

        seen_hashes: Dict[str, str] = {}
        to_delete: List[str] = []

        sorted_records = sorted(
            self._records.values(), key=lambda r: r.timestamp
        )

        for record in sorted_records:
            dedupe_hash = self._compute_dedupe_hash(record)
            if dedupe_hash in seen_hashes:
                to_delete.append(record.experience_id)
            else:
                seen_hashes[dedupe_hash] = record.experience_id

        for exp_id in to_delete:
            del self._records[exp_id]

        if to_delete:
            self._update_dataframe()
            self._logger.info(f"去重完成，删除 {len(to_delete)} 条重复记录")

        return len(to_delete)

    def compute_quality_scores(self) -> int:
        """
        计算所有未评分记录的质量评分

        评分算法：
        - 成功状态基础分：success=1.0, partial=0.6, failed=0.2, skipped=0.0
        - performance_metrics.accuracy 权重 0.3
        - performance_metrics.efficiency 权重 0.2
        - 错误惩罚：每个错误扣 0.1，最多扣 0.5
        - 警告惩罚：每个警告扣 0.05，最多扣 0.2
        - 结果在 0-1 之间

        Returns:
            更新的记录数
        """
        updated_count = 0

        for record in self._records.values():
            if record.quality_score is not None:
                continue

            base_scores = {
                "success": 1.0,
                "partial": 0.6,
                "failed": 0.2,
                "skipped": 0.0,
            }
            base_score = base_scores.get(record.status, 0.0)

            accuracy = record.performance_metrics.get("accuracy", 0.0)
            efficiency = record.performance_metrics.get("efficiency", 0.0)

            error_penalty = min(len(record.errors) * 0.1, 0.5)
            warning_penalty = min(len(record.warnings) * 0.05, 0.2)

            quality_score = (
                base_score * 0.5
                + accuracy * 0.3
                + efficiency * 0.2
                - error_penalty
                - warning_penalty
            )

            quality_score = max(0.0, min(1.0, quality_score))
            record.quality_score = quality_score
            updated_count += 1

        if updated_count > 0:
            self._update_dataframe()
            self._logger.info(f"质量评分计算完成，更新 {updated_count} 条记录")

        return updated_count

    def export_to_dataframe(self) -> pd.DataFrame:
        """
        导出为DataFrame

        Returns:
            包含所有记录的DataFrame
        """
        return self._df.copy()

    def export_to_json(self, file_path: str) -> bool:
        """
        导出为JSON文件

        Args:
            file_path: 输出文件路径

        Returns:
            导出是否成功
        """
        try:
            records_list = [record.to_dict() for record in self._records.values()]
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(records_list, f, ensure_ascii=False, indent=2)

            self._logger.info(f"导出经验记录到 JSON: {file_path}, 共 {len(records_list)} 条")
            return True
        except Exception as e:
            self._logger.error(f"导出JSON失败: {e}")
            return False

    def load_from_json(self, file_path: str) -> int:
        """
        从JSON文件加载经验记录

        Args:
            file_path: JSON文件路径

        Returns:
            加载的记录数
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self._logger.warning(f"JSON文件不存在: {file_path}")
                return 0

            with open(path, "r", encoding="utf-8") as f:
                records_data = json.load(f)

            loaded_count = 0
            for data in records_data:
                record = ExperienceRecord.from_dict(data)
                self._records[record.experience_id] = record
                loaded_count += 1

            if loaded_count > 0:
                self._update_dataframe()

            self._logger.info(f"从 JSON 加载经验记录: {file_path}, 共 {loaded_count} 条")
            return loaded_count
        except Exception as e:
            self._logger.error(f"加载JSON失败: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典，包含总数、按类型分布、按状态分布、平均质量分等
        """
        stats: Dict[str, Any] = {
            "total_records": len(self._records),
            "by_task_type": {},
            "by_status": {},
            "average_quality_score": None,
            "avg_duration_ms": 0.0,
            "total_errors": 0,
            "total_warnings": 0,
        }

        if not self._records:
            return stats

        quality_scores = []
        total_duration = 0.0
        total_errors = 0
        total_warnings = 0

        for record in self._records.values():
            task_type = record.task_type
            status = record.status

            stats["by_task_type"][task_type] = (
                stats["by_task_type"].get(task_type, 0) + 1
            )
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            if record.quality_score is not None:
                quality_scores.append(record.quality_score)

            total_duration += record.duration_ms
            total_errors += len(record.errors)
            total_warnings += len(record.warnings)

        if quality_scores:
            stats["average_quality_score"] = sum(quality_scores) / len(quality_scores)

        stats["avg_duration_ms"] = total_duration / len(self._records)
        stats["total_errors"] = total_errors
        stats["total_warnings"] = total_warnings

        return stats
