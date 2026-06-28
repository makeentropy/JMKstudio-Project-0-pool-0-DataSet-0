"""
版本管理模块

提供数据版本控制、变更追踪和历史管理功能。
"""

from ai_llm_agent_crawler.versioning.version_manager import (
    VersionType,
    VersionStatus,
    VersionInfo,
    VersionChange,
    VersionDiff,
    VersionBranch,
    VersionStorageBackend,
    VersionManager,
    VersionControlSystem,
)

__all__ = [
    "VersionType",
    "VersionStatus",
    "VersionInfo",
    "VersionChange",
    "VersionDiff",
    "VersionBranch",
    "VersionStorageBackend",
    "VersionManager",
    "VersionControlSystem",
]