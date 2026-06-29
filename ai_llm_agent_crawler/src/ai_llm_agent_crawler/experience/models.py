"""
经验数据模型模块

定义经验记录的数据结构、类型枚举和相关工具方法。
"""

import hashlib
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExperienceType(str, Enum):
    """经验类型枚举"""

    TASK_EXECUTION = "task_execution"
    SKILL_USAGE = "skill_usage"
    ERROR_OCCURRENCE = "error_occurrence"
    OPTIMIZATION = "optimization"
    LEARNING = "learning"
    OTHER = "other"


class TaskType(str, Enum):
    """任务类型枚举"""

    CRAWLER = "crawler"
    PROCESSOR = "processor"
    ANALYZER = "analyzer"
    ANNOTATOR = "annotator"
    VALIDATOR = "validator"
    OTHER = "other"


class TaskStatus(str, Enum):
    """任务状态枚举"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


def _generate_experience_id() -> str:
    """生成经验记录唯一ID

    Returns:
        经验记录ID，格式为 exp_ + 时间戳 + 8位hash
    """
    timestamp = str(int(time.time() * 1000))
    random_hash = hashlib.md5(uuid.uuid4().hex.encode()).hexdigest()[:8]
    return f"exp_{timestamp}_{random_hash}"


class ExperienceRecord(BaseModel):
    """经验记录模型"""

    experience_id: str = Field(
        default_factory=_generate_experience_id,
        description="经验记录唯一ID",
    )
    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    task_name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="记录时间戳",
    )
    duration_ms: float = Field(default=0.0, description="执行耗时（毫秒）")
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="性能指标字典",
    )
    input_summary: str = Field(default="", description="输入摘要")
    output_summary: str = Field(default="", description="输出摘要")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    quality_score: Optional[float] = Field(
        default=None,
        description="质量评分（0-1）",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展元数据",
    )

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            经验记录的字典表示
        """
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceRecord":
        """从字典创建经验记录

        Args:
            data: 经验记录字典

        Returns:
            ExperienceRecord实例
        """
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data = data.copy()
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
