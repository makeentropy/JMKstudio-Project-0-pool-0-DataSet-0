"""
资源管理器

管理 Agent 使用的三大核心资源：
- Dataset Pool（数据集池）
- Skill Pool（技能池）
- Storage Pool（存储池）
"""

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.dataset.schema import DatasetSchema
from ai_llm_agent_crawler.dataset.skill_engine import SkillMetadata
from ai_llm_agent_crawler.storage.pool import NASStoragePool, NASStoragePoolConfig
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceType(str, Enum):
    """资源类型枚举"""

    DATASET = "dataset"
    SKILL = "skill"
    STORAGE = "storage"
    MODEL = "model"
    COMPUTE = "compute"


class ResourceStatus(str, Enum):
    """资源状态枚举"""

    AVAILABLE = "available"
    IN_USE = "in_use"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    DEPLETED = "depleted"
    ERROR = "error"


class ResourceInfo(BaseModel):
    """资源信息"""

    resource_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    resource_type: ResourceType
    name: str
    status: ResourceStatus = ResourceStatus.AVAILABLE
    description: str = ""
    version: str = "1.0.0"

    size_bytes: int = 0
    used_bytes: int = 0
    capacity: int = 0

    owner_agent_id: Optional[str] = None
    access_count: int = 0
    last_access_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    path: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class DatasetPoolManager:
    """
    数据集池管理器

    管理数据集的注册、检索、分配和生命周期。
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化数据集池管理器

        Args:
            base_dir: 数据集基础目录
        """
        self.base_dir = base_dir or Path("data/datasets")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._datasets: Dict[str, ResourceInfo] = {}
        self._schemas: Dict[str, DatasetSchema] = {}
        self.logger = get_logger(f"{__name__}.DatasetPoolManager")

    def register_dataset(
        self,
        name: str,
        schema: DatasetSchema,
        path: Optional[str] = None,
        size_bytes: int = 0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceInfo:
        """
        注册数据集到池中

        Args:
            name: 数据集名称
            schema: 数据集模式
            path: 数据集路径
            size_bytes: 数据大小（字节）
            tags: 标签列表
            metadata: 元数据

        Returns:
            资源信息
        """
        resource_id = f"dataset_{uuid.uuid4().hex[:8]}"
        dataset_path = path or str(self.base_dir / name)

        resource = ResourceInfo(
            resource_id=resource_id,
            resource_type=ResourceType.DATASET,
            name=name,
            status=ResourceStatus.AVAILABLE,
            description=schema.description or f"Dataset: {name}",
            version=schema.version,
            size_bytes=size_bytes,
            capacity=size_bytes * 10 if size_bytes > 0 else 1024 * 1024 * 100,
            path=dataset_path,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._datasets[resource_id] = resource
        self._schemas[resource_id] = schema

        self.logger.info(f"数据集已注册: {name} ({resource_id})")
        return resource

    def get_dataset(self, resource_id: str) -> Optional[ResourceInfo]:
        """获取数据集资源信息"""
        return self._datasets.get(resource_id)

    def get_schema(self, resource_id: str) -> Optional[DatasetSchema]:
        """获取数据集模式"""
        return self._schemas.get(resource_id)

    def list_datasets(
        self,
        tags: Optional[List[str]] = None,
        status: Optional[ResourceStatus] = None,
    ) -> List[ResourceInfo]:
        """
        列出数据集

        Args:
            tags: 按标签过滤
            status: 按状态过滤

        Returns:
            数据集资源列表
        """
        datasets = list(self._datasets.values())

        if status:
            datasets = [d for d in datasets if d.status == status]

        if tags:
            datasets = [d for d in datasets if all(t in d.tags for t in tags)]

        return datasets

    def find_by_name(self, name: str) -> Optional[ResourceInfo]:
        """按名称查找数据集"""
        for dataset in self._datasets.values():
            if dataset.name == name:
                return dataset
        return None

    def acquire_dataset(
        self,
        resource_id: str,
        agent_id: str,
    ) -> bool:
        """
        申请使用数据集

        Args:
            resource_id: 资源ID
            agent_id: Agent ID

        Returns:
            是否申请成功
        """
        dataset = self._datasets.get(resource_id)
        if not dataset or dataset.status != ResourceStatus.AVAILABLE:
            return False

        dataset.status = ResourceStatus.IN_USE
        dataset.owner_agent_id = agent_id
        dataset.access_count += 1
        dataset.last_access_time = datetime.now()

        self.logger.info(f"数据集已分配: {dataset.name} -> {agent_id}")
        return True

    def release_dataset(self, resource_id: str) -> bool:
        """
        释放数据集

        Args:
            resource_id: 资源ID

        Returns:
            是否释放成功
        """
        dataset = self._datasets.get(resource_id)
        if not dataset or dataset.status != ResourceStatus.IN_USE:
            return False

        dataset.status = ResourceStatus.AVAILABLE
        dataset.owner_agent_id = None

        self.logger.info(f"数据集已释放: {dataset.name}")
        return True

    def remove_dataset(self, resource_id: str) -> bool:
        """移除数据集"""
        if resource_id in self._datasets:
            del self._datasets[resource_id]
            if resource_id in self._schemas:
                del self._schemas[resource_id]
            return True
        return False

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取数据集池统计信息"""
        total = len(self._datasets)
        available = sum(1 for d in self._datasets.values() if d.status == ResourceStatus.AVAILABLE)
        in_use = sum(1 for d in self._datasets.values() if d.status == ResourceStatus.IN_USE)
        total_size = sum(d.size_bytes for d in self._datasets.values())

        return {
            "total_datasets": total,
            "available": available,
            "in_use": in_use,
            "total_size_bytes": total_size,
            "datasets": list(self._datasets.keys()),
        }


class SkillPoolManager:
    """
    技能池管理器

    管理 Skill 的注册、检索、分配和版本管理。
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        """
        初始化技能池管理器

        Args:
            skills_dir: 技能目录
        """
        self.skills_dir = skills_dir or Path("skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, ResourceInfo] = {}
        self._skill_metadata: Dict[str, SkillMetadata] = {}
        self.logger = get_logger(f"{__name__}.SkillPoolManager")

    def register_skill(
        self,
        metadata: SkillMetadata,
        skill_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ResourceInfo:
        """
        注册技能到池中

        Args:
            metadata: Skill 元数据
            skill_path: Skill 文件路径
            tags: 标签列表

        Returns:
            资源信息
        """
        resource_id = f"skill_{uuid.uuid4().hex[:8]}"
        path = skill_path or str(self.skills_dir / metadata.id)

        resource = ResourceInfo(
            resource_id=resource_id,
            resource_type=ResourceType.SKILL,
            name=metadata.name,
            status=ResourceStatus.AVAILABLE,
            description=metadata.description,
            version=metadata.version,
            path=path,
            tags=tags or metadata.tags,
            metadata={"skill_type": metadata.skill_type, "accuracy": metadata.accuracy},
        )

        self._skills[resource_id] = resource
        self._skill_metadata[resource_id] = metadata

        self.logger.info(f"技能已注册: {metadata.name} ({resource_id})")
        return resource

    def get_skill(self, resource_id: str) -> Optional[ResourceInfo]:
        """获取技能资源信息"""
        return self._skills.get(resource_id)

    def get_skill_metadata(self, resource_id: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        return self._skill_metadata.get(resource_id)

    def list_skills(
        self,
        skill_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[ResourceStatus] = None,
    ) -> List[ResourceInfo]:
        """
        列出技能

        Args:
            skill_type: 按技能类型过滤
            tags: 按标签过滤
            status: 按状态过滤

        Returns:
            技能资源列表
        """
        skills = list(self._skills.values())

        if status:
            skills = [s for s in skills if s.status == status]

        if tags:
            skills = [s for s in skills if all(t in s.tags for t in tags)]

        if skill_type:
            skills = [
                s for s in skills
                if s.metadata.get("skill_type") == skill_type
            ]

        return skills

    def find_by_name(self, name: str) -> Optional[ResourceInfo]:
        """按名称查找技能"""
        for skill in self._skills.values():
            if skill.name == name:
                return skill
        return None

    def acquire_skill(self, resource_id: str, agent_id: str) -> bool:
        """
        申请使用技能

        Args:
            resource_id: 资源ID
            agent_id: Agent ID

        Returns:
            是否申请成功
        """
        skill = self._skills.get(resource_id)
        if not skill or skill.status == ResourceStatus.MAINTENANCE:
            return False

        skill.access_count += 1
        skill.last_access_time = datetime.now()
        if not skill.owner_agent_id:
            skill.owner_agent_id = agent_id

        self.logger.info(f"技能已分配: {skill.name} -> {agent_id}")
        return True

    def release_skill(self, resource_id: str) -> bool:
        """释放技能"""
        skill = self._skills.get(resource_id)
        if not skill:
            return False
        skill.owner_agent_id = None
        return True

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取技能池统计信息"""
        total = len(self._skills)
        available = sum(1 for s in self._skills.values() if s.status == ResourceStatus.AVAILABLE)
        total_accesses = sum(s.access_count for s in self._skills.values())

        return {
            "total_skills": total,
            "available": available,
            "total_accesses": total_accesses,
            "skills": list(self._skills.keys()),
        }


class StoragePoolManager:
    """
    存储池管理器

    封装 NASStoragePool，提供统一的存储资源管理接口。
    """

    def __init__(self, pool_config: Optional[NASStoragePoolConfig] = None):
        """
        初始化存储池管理器

        Args:
            pool_config: 存储池配置
        """
        self._pool_config = pool_config or NASStoragePoolConfig()
        self._pool: Optional[NASStoragePool] = None
        self._resources: Dict[str, ResourceInfo] = {}
        self.logger = get_logger(f"{__name__}.StoragePoolManager")

    def initialize_pool(
        self,
        backend_configs: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        初始化存储池

        Args:
            backend_configs: 后端配置列表

        Returns:
            是否初始化成功
        """
        try:
            from ai_llm_agent_crawler.storage.pool import create_nas_pool

            self._pool = create_nas_pool(
                backend_configs=backend_configs,
                pool_config=self._pool_config,
            )

            resource = ResourceInfo(
                resource_id="storage_pool_main",
                resource_type=ResourceType.STORAGE,
                name="main_storage_pool",
                status=ResourceStatus.AVAILABLE,
                description="主存储池",
            )
            self._resources["main"] = resource

            self.logger.info("存储池初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"存储池初始化失败: {e}", exc_info=True)
            return False

    @property
    def pool(self) -> Optional[NASStoragePool]:
        """获取存储池实例"""
        return self._pool

    def write_data(self, path: str, data: Union[bytes, str], **kwargs) -> bool:
        """写入数据到存储池"""
        if not self._pool:
            return False
        result = self._pool.write(path, data, **kwargs)
        return result.success

    def read_data(self, path: str) -> Optional[bytes]:
        """从存储池读取数据"""
        if not self._pool:
            return None
        return self._pool.read(path)

    def get_storage_status(self) -> Dict[str, Any]:
        """获取存储状态"""
        if not self._pool:
            return {"initialized": False}
        return self._pool.get_storage_status()

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取存储池统计"""
        return self.get_storage_status()


class ResourceManager:
    """
    统一资源管理器

    整合数据集池、技能池、存储池的统一管理接口。
    """

    def __init__(
        self,
        dataset_base_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        storage_config: Optional[NASStoragePoolConfig] = None,
    ):
        """
        初始化资源管理器

        Args:
            dataset_base_dir: 数据集基础目录
            skills_dir: 技能目录
            storage_config: 存储配置
        """
        self.dataset_pool = DatasetPoolManager(dataset_base_dir)
        self.skill_pool = SkillPoolManager(skills_dir)
        self.storage_pool = StoragePoolManager(storage_config)
        self.logger = get_logger(f"{__name__}.ResourceManager")

        self._resource_bindings: Dict[str, Dict[str, List[str]]] = {}

    def bind_agent_resources(
        self,
        agent_id: str,
        dataset_ids: Optional[List[str]] = None,
        skill_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        为 Agent 绑定资源

        Args:
            agent_id: Agent ID
            dataset_ids: 数据集ID列表
            skill_ids: 技能ID列表

        Returns:
            绑定结果
        """
        results = {"datasets": True, "skills": True}

        if agent_id not in self._resource_bindings:
            self._resource_bindings[agent_id] = {"datasets": [], "skills": []}

        if dataset_ids:
            for ds_id in dataset_ids:
                if self.dataset_pool.acquire_dataset(ds_id, agent_id):
                    self._resource_bindings[agent_id]["datasets"].append(ds_id)
                else:
                    results["datasets"] = False

        if skill_ids:
            for skill_id in skill_ids:
                if self.skill_pool.acquire_skill(skill_id, agent_id):
                    self._resource_bindings[agent_id]["skills"].append(skill_id)
                else:
                    results["skills"] = False

        return results

    def release_agent_resources(self, agent_id: str) -> bool:
        """
        释放 Agent 绑定的所有资源

        Args:
            agent_id: Agent ID

        Returns:
            是否释放成功
        """
        if agent_id not in self._resource_bindings:
            return True

        bindings = self._resource_bindings[agent_id]

        for ds_id in bindings.get("datasets", []):
            self.dataset_pool.release_dataset(ds_id)

        for skill_id in bindings.get("skills", []):
            self.skill_pool.release_skill(skill_id)

        del self._resource_bindings[agent_id]
        self.logger.info(f"Agent 资源已释放: {agent_id}")
        return True

    def get_agent_resources(self, agent_id: str) -> Dict[str, List[str]]:
        """获取 Agent 绑定的资源"""
        return self._resource_bindings.get(agent_id, {"datasets": [], "skills": []})

    def get_overall_stats(self) -> Dict[str, Any]:
        """获取整体资源统计"""
        return {
            "dataset_pool": self.dataset_pool.get_pool_stats(),
            "skill_pool": self.skill_pool.get_pool_stats(),
            "storage_pool": self.storage_pool.get_pool_stats(),
            "active_bindings": len(self._resource_bindings),
        }
