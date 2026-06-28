"""
数据冗余备份机制模块

实现数据的多副本存储、同步复制、异步复制和一致性检查机制。
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from ai_llm_agent_crawler.storage.backends import StorageBackend
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ReplicationMode(Enum):
    """复制模式枚举"""
    SYNC = "sync"  # 同步复制（等待所有副本写入完成）
    ASYNC = "async"  # 异步复制（立即返回，后台复制）
    SEMI_SYNC = "semi_sync"  # 半同步（至少一个副本写入完成）
    BEST_EFFORT = "best_effort"  # 尽力复制（不保证完成）


class ConsistencyLevel(Enum):
    """一致性级别枚举"""
    STRONG = "strong"  # 强一致性（所有副本必须一致）
    EVENTUAL = "eventual"  # 最终一致性（允许短暂不一致）
    QUORUM = "quorum"  # 写入多数副本即可
    ONE = "one"  # 至少一个副本


@dataclass
class ReplicaInfo:
    """副本信息"""
    backend_name: str  # 后端名称
    path: str  # 文件路径
    checksum: Optional[str] = None  # 数据校验和
    size: Optional[int] = None  # 数据大小
    created_at: Optional[float] = None  # 创建时间
    updated_at: Optional[float] = None  # 更新时间
    synced: bool = False  # 是否同步完成
    version: Optional[int] = None  # 版本号


@dataclass
class ReplicationResult:
    """复制结果"""
    success: bool
    total_replicas: int
    successful_replicas: int
    failed_backends: List[str]
    primary_backend: Optional[str] = None
    checksum: Optional[str] = None
    message: str = ""


@dataclass
class ConsistencyCheckResult:
    """一致性检查结果"""
    is_consistent: bool
    inconsistent_files: List[str]
    missing_replicas: Dict[str, List[str]]  # 文件 -> 缺失副本的后端
    checksum_mismatch: Dict[str, Dict[str, str]]  # 文件 -> {后端: 校验和}
    message: str = ""


class ReplicationManager:
    """
    数据复制管理器
    
    负责数据的多副本存储、同步和一致性管理。
    """
    
    def __init__(
        self,
        default_mode: ReplicationMode = ReplicationMode.SYNC,
        default_replicas: int = 3,
        consistency_level: ConsistencyLevel = ConsistencyLevel.QUORUM,
        checksum_algorithm: str = "md5"
    ):
        """
        初始化复制管理器
        
        Args:
            default_mode: 默认复制模式
            default_replicas: 默认副本数
            consistency_level: 默认一致性级别
            checksum_algorithm: 校验和算法
        """
        self.default_mode = default_mode
        self.default_replicas = default_replicas
        self.consistency_level = consistency_level
        self.checksum_algorithm = checksum_algorithm
        self._backends: Dict[str, StorageBackend] = {}
        self._replica_map: Dict[str, List[ReplicaInfo]] = {}  # 文件路径 -> 副本信息列表
        self._pending_replications: Dict[str, asyncio.Task] = {}  # 待处理的异步复制任务
        self.logger = get_logger(f"{__name__}.ReplicationManager")
    
    def register_backend(self, backend: StorageBackend) -> bool:
        """
        注册存储后端
        
        Args:
            backend: 存储后端
            
        Returns:
            注册是否成功
        """
        name = backend.config.name
        if name in self._backends:
            self.logger.warning(f"后端已注册: {name}")
            return False
        
        if not backend.is_connected():
            if not backend.connect():
                self.logger.error(f"后端连接失败: {name}")
                return False
        
        self._backends[name] = backend
        self.logger.info(f"注册后端成功: {name}")
        return True
    
    def unregister_backend(self, name: str) -> bool:
        """
        注销存储后端
        
        Args:
            name: 后端名称
            
        Returns:
            注销是否成功
        """
        if name not in self._backends:
            return False
        
        backend = self._backends[name]
        backend.disconnect()
        del self._backends[name]
        
        # 清理相关副本信息
        for path, replicas in self._replica_map.items():
            self._replica_map[path] = [r for r in replicas if r.backend_name != name]
        
        self.logger.info(f"注销后端: {name}")
        return True
    
    def get_backend(self, name: str) -> Optional[StorageBackend]:
        """
        获取指定后端
        
        Args:
            name: 后端名称
            
        Returns:
            存储后端
        """
        return self._backends.get(name)
    
    def get_all_backends(self) -> List[StorageBackend]:
        """
        获取所有后端
        
        Returns:
            后端列表
        """
        return list(self._backends.values())
    
    def write_with_replication(
        self,
        path: str,
        data: Union[bytes, str],
        replicas: Optional[int] = None,
        mode: Optional[ReplicationMode] = None,
        backends: Optional[List[str]] = None,
        overwrite: bool = False
    ) -> ReplicationResult:
        """
        写入数据并创建副本
        
        Args:
            path: 文件路径
            data: 数据内容
            replicas: 副本数量
            mode: 复制模式
            backends: 指定的后端列表
            overwrite: 是否覆盖
            
        Returns:
            复制结果
        """
        replica_count = replicas or self.default_replicas
        replication_mode = mode or self.default_mode
        
        # 选择后端
        target_backends = self._select_backends_for_replication(backends, replica_count)
        
        if not target_backends:
            return ReplicationResult(
                success=False,
                total_replicas=replica_count,
                successful_replicas=0,
                failed_backends=[],
                message="没有可用的存储后端"
            )
        
        # 计算校验和
        checksum = self._calculate_checksum(data)
        
        # 根据复制模式执行写入
        if replication_mode == ReplicationMode.SYNC:
            return self._sync_replicate(path, data, checksum, target_backends, overwrite)
        elif replication_mode == ReplicationMode.ASYNC:
            return self._async_replicate(path, data, checksum, target_backends, overwrite)
        elif replication_mode == ReplicationMode.SEMI_SYNC:
            return self._semi_sync_replicate(path, data, checksum, target_backends, overwrite)
        else:
            return self._best_effort_replicate(path, data, checksum, target_backends, overwrite)
    
    def read_with_replication(
        self,
        path: str,
        prefer_backend: Optional[str] = None,
        fallback: bool = True
    ) -> Optional[bytes]:
        """
        从副本读取数据
        
        Args:
            path: 文件路径
            prefer_backend: 首选后端
            fallback: 是否在其他副本中回退
            
        Returns:
            数据内容
        """
        # 检查是否有副本信息
        if path in self._replica_map:
            replicas = self._replica_map[path]
            
            # 如果指定了首选后端
            if prefer_backend:
                for replica in replicas:
                    if replica.backend_name == prefer_backend:
                        backend = self._backends.get(replica.backend_name)
                        if backend:
                            data = backend.read(path)
                            if data:
                                return data
            
            # 尝试从所有副本读取
            if fallback:
                for replica in replicas:
                    backend = self._backends.get(replica.backend_name)
                    if backend and backend.is_connected():
                        data = backend.read(path)
                        if data:
                            return data
        
        # 尝试从所有后端读取（用于未记录的文件）
        if fallback:
            for backend in self._backends.values():
                if backend.is_connected():
                    data = backend.read(path)
                    if data:
                        # 记录副本信息
                        self._update_replica_info(path, backend.config.name, len(data))
                        return data
        
        return None
    
    def delete_with_replication(
        self,
        path: str,
        delete_all_replicas: bool = True,
        backends: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        删除数据和副本
        
        Args:
            path: 文件路径
            delete_all_replicas: 是否删除所有副本
            backends: 指定的后端列表
            
        Returns:
            每个后端的删除结果
        """
        results = {}
        target_backends = backends or list(self._backends.keys())
        
        # 如果有副本信息，优先从副本信息获取后端
        if path in self._replica_map:
            replica_backends = [r.backend_name for r in self._replica_map[path]]
            if delete_all_replicas:
                target_backends = replica_backends
        
        for backend_name in target_backends:
            backend = self._backends.get(backend_name)
            if backend:
                results[backend_name] = backend.delete(path)
        
        # 清理副本信息
        if delete_all_replicas and path in self._replica_map:
            del self._replica_map[path]
        
        return results
    
    def sync_replicas(
        self,
        path: str,
        force: bool = False
    ) -> ReplicationResult:
        """
        同步副本
        
        Args:
            path: 文件路径
            force: 是否强制同步（即使标记为已同步）
            
        Returns:
            同步结果
        """
        if path not in self._replica_map:
            return ReplicationResult(
                success=False,
                total_replicas=0,
                successful_replicas=0,
                failed_backends=[],
                message="文件副本信息不存在"
            )
        
        replicas = self._replica_map[path]
        
        # 找到已同步的副本作为源
        source_replica = None
        source_data = None
        
        for replica in replicas:
            if replica.synced or force:
                backend = self._backends.get(replica.backend_name)
                if backend:
                    source_data = backend.read(path)
                    if source_data:
                        source_replica = replica
                        break
        
        if not source_replica or not source_data:
            # 尝试从任何副本读取
            for replica in replicas:
                backend = self._backends.get(replica.backend_name)
                if backend:
                    source_data = backend.read(path)
                    if source_data:
                        source_replica = replica
                        break
        
        if not source_data:
            return ReplicationResult(
                success=False,
                total_replicas=len(replicas),
                successful_replicas=0,
                failed_backends=[r.backend_name for r in replicas],
                message="无法读取源数据"
            )
        
        checksum = self._calculate_checksum(source_data)
        failed_backends = []
        successful_count = 0
        
        # 同步到所有副本
        for replica in replicas:
            if replica.backend_name == source_replica.backend_name:
                replica.synced = True
                replica.checksum = checksum
                replica.updated_at = time.time()
                successful_count += 1
                continue
            
            backend = self._backends.get(replica.backend_name)
            if backend:
                if backend.write(path, source_data, overwrite=True):
                    replica.synced = True
                    replica.checksum = checksum
                    replica.updated_at = time.time()
                    successful_count += 1
                else:
                    replica.synced = False
                    failed_backends.append(replica.backend_name)
        
        return ReplicationResult(
            success=successful_count >= len(replicas) // 2 + 1,
            total_replicas=len(replicas),
            successful_replicas=successful_count,
            failed_backends=failed_backends,
            checksum=checksum,
            message=f"同步完成，{successful_count}/{len(replicas)}副本成功"
        )
    
    def check_consistency(
        self,
        paths: Optional[List[str]] = None
    ) -> ConsistencyCheckResult:
        """
        检查副本一致性
        
        Args:
            paths: 要检查的文件路径列表，None表示检查所有
            
        Returns:
            一致性检查结果
        """
        check_paths = paths or list(self._replica_map.keys())
        
        inconsistent_files = []
        missing_replicas = {}
        checksum_mismatch = {}
        
        for path in check_paths:
            if path not in self._replica_map:
                continue
            
            replicas = self._replica_map[path]
            checksums: Dict[str, str] = {}
            missing = []
            
            for replica in replicas:
                backend = self._backends.get(replica.backend_name)
                if not backend:
                    missing.append(replica.backend_name)
                    continue
                
                data = backend.read(path)
                if not data:
                    missing.append(replica.backend_name)
                    continue
                
                checksum = self._calculate_checksum(data)
                checksums[replica.backend_name] = checksum
                
                # 更新副本信息
                replica.checksum = checksum
                replica.size = len(data)
                replica.synced = True
            
            # 检查一致性
            unique_checksums = set(checksums.values())
            
            if len(unique_checksums) > 1:
                inconsistent_files.append(path)
                checksum_mismatch[path] = checksums
            elif missing:
                missing_replicas[path] = missing
        
        is_consistent = len(inconsistent_files) == 0 and len(missing_replicas) == 0
        
        return ConsistencyCheckResult(
            is_consistent=is_consistent,
            inconsistent_files=inconsistent_files,
            missing_replicas=missing_replicas,
            checksum_mismatch=checksum_mismatch,
            message=f"检查完成，发现{len(inconsistent_files)}个不一致文件，{len(missing_replicas)}个缺失副本"
        )
    
    def repair_consistency(
        self,
        path: str
    ) -> ReplicationResult:
        """
        修复副本一致性
        
        Args:
            path: 文件路径
            
        Returns:
            修复结果
        """
        return self.sync_replicas(path, force=True)
    
    def get_replica_info(self, path: str) -> List[ReplicaInfo]:
        """
        获取副本信息
        
        Args:
            path: 文件路径
            
        Returns:
            副本信息列表
        """
        return self._replica_map.get(path, [])
    
    def get_replication_status(self) -> Dict[str, Any]:
        """
        获取复制状态
        
        Returns:
            状态字典
        """
        synced_count = 0
        unsynced_count = 0
        
        for replicas in self._replica_map.values():
            for replica in replicas:
                if replica.synced:
                    synced_count += 1
                else:
                    unsynced_count += 1
        
        return {
            "backend_count": len(self._backends),
            "file_count": len(self._replica_map),
            "total_replicas": synced_count + unsynced_count,
            "synced_replicas": synced_count,
            "unsynced_replicas": unsynced_count,
            "pending_replications": len(self._pending_replications),
            "default_replicas": self.default_replicas,
            "replication_mode": self.default_mode.value,
            "consistency_level": self.consistency_level.value,
        }
    
    def _select_backends_for_replication(
        self,
        specified_backends: Optional[List[str]] = None,
        count: int = 1
    ) -> List[StorageBackend]:
        """
        选择用于复制的后端
        
        Args:
            specified_backends: 指定的后端名称列表
            count: 需要的数量
            
        Returns:
            后端列表
        """
        if specified_backends:
            backends = [self._backends.get(name) for name in specified_backends]
            return [b for b in backends if b and b.is_connected() and not b.config.read_only]
        
        # 自动选择：优先选择可用空间最大的
        available_backends = [
            b for b in self._backends.values()
            if b.is_connected() and not b.config.read_only
        ]
        
        # 按可用空间排序
        available_backends.sort(
            key=lambda b: b.get_available_space(),
            reverse=True
        )
        
        return available_backends[:count]
    
    def _sync_replicate(
        self,
        path: str,
        data: Union[bytes, str],
        checksum: str,
        backends: List[StorageBackend],
        overwrite: bool
    ) -> ReplicationResult:
        """
        同步复制
        
        Args:
            path: 文件路径
            data: 数据
            checksum: 校验和
            backends: 后端列表
            overwrite: 是否覆盖
            
        Returns:
            复制结果
        """
        successful = []
        failed = []
        
        for backend in backends:
            if backend.write(path, data, overwrite=overwrite):
                successful.append(backend.config.name)
            else:
                failed.append(backend.config.name)
        
        # 更新副本信息
        self._update_replica_map(path, successful, checksum, len(data) if isinstance(data, bytes) else len(data.encode()))
        
        # 判断是否成功（根据一致性级别）
        success = self._check_success(len(successful), len(backends))
        
        return ReplicationResult(
            success=success,
            total_replicas=len(backends),
            successful_replicas=len(successful),
            failed_backends=failed,
            primary_backend=successful[0] if successful else None,
            checksum=checksum,
            message=f"同步复制完成，{len(successful)}/{len(backends)}成功"
        )
    
    def _async_replicate(
        self,
        path: str,
        data: Union[bytes, str],
        checksum: str,
        backends: List[StorageBackend],
        overwrite: bool
    ) -> ReplicationResult:
        """
        异步复制
        
        Args:
            path: 文件路径
            data: 数据
            checksum: 校验和
            backends: 后端列表
            overwrite: 是否覆盖
            
        Returns:
            复制结果（立即返回，后台复制）
        """
        # 立即写入第一个后端
        primary_backend = backends[0]
        primary_success = primary_backend.write(path, data, overwrite=overwrite)
        
        if not primary_success:
            return ReplicationResult(
                success=False,
                total_replicas=len(backends),
                successful_replicas=0,
                failed_backends=[primary_backend.config.name],
                message="主副本写入失败"
            )
        
        # 后台异步复制
        async def replicate_async():
            for backend in backends[1:]:
                try:
                    if backend.write(path, data, overwrite=overwrite):
                        self.logger.debug(f"异步复制成功: {path} -> {backend.config.name}")
                except Exception as e:
                    self.logger.error(f"异步复制失败: {path} -> {backend.config.name}: {e}")
        
        # 创建异步任务（如果支持）
        try:
            loop = asyncio.get_event_loop()
            task = loop.create_task(replicate_async())
            self._pending_replications[path] = task
        except:
            # 不支持异步，同步执行
            for backend in backends[1:]:
                backend.write(path, data, overwrite=overwrite)
        
        # 更新副本信息（标记为未同步）
        self._update_replica_map(path, [primary_backend.config.name], checksum, len(data) if isinstance(data, bytes) else len(data.encode()), synced=False)
        
        return ReplicationResult(
            success=True,
            total_replicas=len(backends),
            successful_replicas=1,
            failed_backends=[],
            primary_backend=primary_backend.config.name,
            checksum=checksum,
            message="异步复制启动，主副本已写入"
        )
    
    def _semi_sync_replicate(
        self,
        path: str,
        data: Union[bytes, str],
        checksum: str,
        backends: List[StorageBackend],
        overwrite: bool
    ) -> ReplicationResult:
        """
        半同步复制
        
        Args:
            path: 文件路径
            data: 数据
            checksum: 校验和
            backends: 后端列表
            overwrite: 是否覆盖
            
        Returns:
            复制结果（至少一个副本写入完成）
        """
        # 写入主副本
        primary_backend = backends[0]
        primary_success = primary_backend.write(path, data, overwrite=overwrite)
        
        if not primary_success:
            # 尝试其他后端
            for backend in backends[1:]:
                if backend.write(path, data, overwrite=overwrite):
                    primary_backend = backend
                    primary_success = True
                    break
        
        if not primary_success:
            return ReplicationResult(
                success=False,
                total_replicas=len(backends),
                successful_replicas=0,
                failed_backends=[b.config.name for b in backends],
                message="所有副本写入失败"
            )
        
        # 尝试写入至少一个额外副本
        extra_success = 0
        for backend in backends[1:]:
            if backend.config.name != primary_backend.config.name:
                if backend.write(path, data, overwrite=overwrite):
                    extra_success += 1
                    break  # 至少一个就够了
        
        successful = [primary_backend.config.name]
        if extra_success > 0:
            successful.append(backends[1].config.name)
        
        # 更新副本信息
        self._update_replica_map(path, successful, checksum, len(data) if isinstance(data, bytes) else len(data.encode()))
        
        return ReplicationResult(
            success=True,
            total_replicas=len(backends),
            successful_replicas=len(successful),
            failed_backends=[b.config.name for b in backends if b.config.name not in successful],
            primary_backend=primary_backend.config.name,
            checksum=checksum,
            message=f"半同步复制完成，{len(successful)}副本成功"
        )
    
    def _best_effort_replicate(
        self,
        path: str,
        data: Union[bytes, str],
        checksum: str,
        backends: List[StorageBackend],
        overwrite: bool
    ) -> ReplicationResult:
        """
        尽力复制
        
        Args:
            path: 文件路径
            data: 数据
            checksum: 校验和
            backends: 后端列表
            overwrite: 是否覆盖
            
        Returns:
            复制结果
        """
        successful = []
        failed = []
        
        for backend in backends:
            try:
                if backend.write(path, data, overwrite=overwrite):
                    successful.append(backend.config.name)
            except Exception as e:
                self.logger.warning(f"复制失败: {path} -> {backend.config.name}: {e}")
                failed.append(backend.config.name)
        
        # 更新副本信息
        if successful:
            self._update_replica_map(path, successful, checksum, len(data) if isinstance(data, bytes) else len(data.encode()))
        
        return ReplicationResult(
            success=len(successful) > 0,
            total_replicas=len(backends),
            successful_replicas=len(successful),
            failed_backends=failed,
            primary_backend=successful[0] if successful else None,
            checksum=checksum,
            message=f"尽力复制完成，{len(successful)}/{len(backends)}成功"
        )
    
    def _calculate_checksum(self, data: Union[bytes, str]) -> str:
        """
        计算数据校验和
        
        Args:
            data: 数据
            
        Returns:
            校验和字符串
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        if self.checksum_algorithm == "md5":
            return hashlib.md5(data).hexdigest()
        elif self.checksum_algorithm == "sha256":
            return hashlib.sha256(data).hexdigest()
        elif self.checksum_algorithm == "sha1":
            return hashlib.sha1(data).hexdigest()
        else:
            return hashlib.md5(data).hexdigest()
    
    def _check_success(self, successful_count: int, total_count: int) -> bool:
        """
        检查是否满足一致性要求
        
        Args:
            successful_count: 成功数量
            total_count: 总数量
            
        Returns:
            是否成功
        """
        if self.consistency_level == ConsistencyLevel.STRONG:
            return successful_count == total_count
        elif self.consistency_level == ConsistencyLevel.QUORUM:
            return successful_count >= total_count // 2 + 1
        elif self.consistency_level == ConsistencyLevel.ONE:
            return successful_count >= 1
        elif self.consistency_level == ConsistencyLevel.EVENTUAL:
            return successful_count >= 1
        else:
            return successful_count >= 1
    
    def _update_replica_map(
        self,
        path: str,
        backend_names: List[str],
        checksum: str,
        size: int,
        synced: bool = True
    ) -> None:
        """
        更新副本映射
        
        Args:
            path: 文件路径
            backend_names: 后端名称列表
            checksum: 校验和
            size: 数据大小
            synced: 是否同步
        """
        replicas = []
        now = time.time()
        
        for name in backend_names:
            replicas.append(ReplicaInfo(
                backend_name=name,
                path=path,
                checksum=checksum,
                size=size,
                created_at=now,
                updated_at=now,
                synced=synced,
                version=1
            ))
        
        self._replica_map[path] = replicas
    
    def _update_replica_info(
        self,
        path: str,
        backend_name: str,
        size: int
    ) -> None:
        """
        更新单个副本信息
        
        Args:
            path: 文件路径
            backend_name: 后端名称
            size: 数据大小
        """
        if path not in self._replica_map:
            self._replica_map[path] = []
        
        # 检查是否已存在
        for replica in self._replica_map[path]:
            if replica.backend_name == backend_name:
                replica.size = size
                replica.updated_at = time.time()
                return
        
        # 添加新副本信息
        self._replica_map[path].append(ReplicaInfo(
            backend_name=backend_name,
            path=path,
            size=size,
            created_at=time.time(),
            updated_at=time.time(),
            synced=False
        ))