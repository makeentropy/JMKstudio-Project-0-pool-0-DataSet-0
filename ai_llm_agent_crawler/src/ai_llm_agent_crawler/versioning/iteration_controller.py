"""
迭代版本控制系统

提供迭代版本控制功能，与version_manager集成：
- 迭代版本追踪
- 版本依赖管理
- 迭代历史记录
- 版本回溯和恢复增强
- 数据一致性保护
"""

import hashlib
import json
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.config import get_settings
from ai_llm_agent_crawler.utils.logging import get_logger
from ai_llm_agent_crawler.versioning.version_manager import (
    VersionInfo,
    VersionManager,
    VersionType,
    VersionStatus,
    VersionChange,
    VersionDiff,
    VersionBranch,
    VersionControlSystem,
)
from ai_llm_agent_crawler.versioning.snapshot_manager import (
    SnapshotManager,
    SnapshotType,
    SnapshotMetadata,
)

logger = get_logger(__name__)


class IterationState(str, Enum):
    """迭代状态"""
    INITIALIZED = "initialized"  # 已初始化
    IN_PROGRESS = "in_progress"  # 进行中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    ABORTED = "aborted"  # 已中止
    REVERTED = "reverted"  # 已回滚


class IterationType(str, Enum):
    """迭代类型"""
    MANUAL = "manual"  # 手动迭代
    AUTOMATED = "automated"  # 自动迭代
    SCHEDULED = "scheduled"  # 定时迭代
    TRIGGERED = "triggered"  # 触发式迭代
    CORRECTIVE = "corrective"  # 修正迭代


class CheckpointType(str, Enum):
    """检查点类型"""
    PRE_OPERATION = "pre_operation"  # 操作前检查点
    POST_OPERATION = "post_operation"  # 操作后检查点
    MILESTONE = "milestone"  # 里程碑检查点
    AUTO = "auto"  # 自动检查点
    MANUAL = "manual"  # 手动检查点


class IterationCheckpoint(BaseModel):
    """迭代检查点"""
    checkpoint_id: str = Field(..., description="检查点ID")
    iteration_id: str = Field(..., description="迭代ID")
    checkpoint_type: CheckpointType = Field(..., description="检查点类型")
    
    # 基本信息
    name: str = Field(default="", description="检查点名称")
    description: str = Field(default="", description="检查点描述")
    
    # 版本信息
    version_before: Optional[str] = Field(default=None, description="检查点前版本")
    version_after: Optional[str] = Field(default=None, description="检查点后版本")
    
    # 快照信息
    snapshot_id: Optional[str] = Field(default=None, description="快照ID")
    
    # 操作信息
    operations: List[Dict[str, Any]] = Field(default_factory=list, description="已执行操作")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    # 验证信息
    is_validated: bool = Field(default=False, description="是否已验证")
    validation_result: Optional[Dict[str, Any]] = Field(default=None, description="验证结果")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class IterationInfo(BaseModel):
    """迭代信息"""
    iteration_id: str = Field(..., description="迭代ID")
    iteration_type: IterationType = Field(..., description="迭代类型")
    state: IterationState = Field(default=IterationState.INITIALIZED, description="迭代状态")
    
    # 基本信息
    name: str = Field(default="", description="迭代名称")
    description: str = Field(default="", description="迭代描述")
    objective: str = Field(default="", description="迭代目标")
    
    # 实体信息
    entity_id: str = Field(..., description="实体ID")
    entity_type: str = Field(default="dataset", description="实体类型")
    
    # 版本信息
    start_version: str = Field(..., description="起始版本")
    current_version: Optional[str] = Field(default=None, description="当前版本")
    target_version: Optional[str] = Field(default=None, description="目标版本")
    final_version: Optional[str] = Field(default=None, description="最终版本")
    
    # 快照信息
    initial_snapshot_id: Optional[str] = Field(default=None, description="初始快照ID")
    final_snapshot_id: Optional[str] = Field(default=None, description="最终快照ID")
    
    # 检查点信息
    checkpoints: List[IterationCheckpoint] = Field(default_factory=list, description="检查点列表")
    current_checkpoint_id: Optional[str] = Field(default=None, description="当前检查点ID")
    
    # 依赖信息
    dependencies: List[str] = Field(default_factory=list, description="依赖迭代ID")
    depends_on_versions: List[str] = Field(default_factory=list, description="依赖版本")
    
    # 操作信息
    planned_operations: List[Dict[str, Any]] = Field(default_factory=list, description="计划操作")
    executed_operations: List[Dict[str, Any]] = Field(default_factory=list, description="已执行操作")
    pending_operations: List[Dict[str, Any]] = Field(default_factory=list, description="待执行操作")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    estimated_duration: Optional[int] = Field(default=None, description="预计时长(秒)")
    actual_duration: Optional[int] = Field(default=None, description="实际时长(秒)")
    
    # 进度信息
    total_steps: int = Field(default=0, description="总步骤数")
    completed_steps: int = Field(default=0, description="已完成步骤数")
    progress_percentage: float = Field(default=0.0, description="进度百分比")
    
    # 操作者
    created_by: str = Field(default="system", description="创建者")
    executed_by: Optional[str] = Field(default=None, description="执行者")
    
    # 错误信息
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    
    # 标签和备注
    tags: List[str] = Field(default_factory=list, description="标签")
    notes: str = Field(default="", description="备注")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class IterationHistory(BaseModel):
    """迭代历史"""
    entity_id: str = Field(..., description="实体ID")
    iterations: List[IterationInfo] = Field(default_factory=list, description="迭代列表")
    total_iterations: int = Field(default=0, description="总迭代数")
    successful_iterations: int = Field(default=0, description="成功迭代数")
    failed_iterations: int = Field(default=0, description="失败迭代数")
    
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class RestorationPlan(BaseModel):
    """恢复计划"""
    plan_id: str = Field(..., description="计划ID")
    entity_id: str = Field(..., description="实体ID")
    
    # 目标信息
    target_version: str = Field(..., description="目标版本")
    target_snapshot_id: Optional[str] = Field(default=None, description="目标快照ID")
    target_checkpoint_id: Optional[str] = Field(default=None, description="目标检查点ID")
    
    # 恢复类型
    restoration_type: str = Field(default="version", description="恢复类型")
    
    # 步骤信息
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="恢复步骤")
    current_step: int = Field(default=0, description="当前步骤")
    
    # 验证信息
    pre_validation: Dict[str, Any] = Field(default_factory=dict, description="恢复前验证")
    post_validation: Dict[str, Any] = Field(default_factory=dict, description="恢复后验证")
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    
    # 状态
    status: str = Field(default="pending", description="状态")
    result: Optional[Dict[str, Any]] = Field(default=None, description="结果")


class IterationController:
    """迭代控制器"""
    
    def __init__(
        self,
        version_manager: Optional[VersionManager] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        vcs: Optional[VersionControlSystem] = None,
    ):
        """
        初始化迭代控制器
        
        Args:
            version_manager: 版本管理器
            snapshot_manager: 快照管理器
            vcs: 版本控制系统
        """
        self.version_manager = version_manager or VersionManager()
        self.snapshot_manager = snapshot_manager or SnapshotManager()
        self.vcs = vcs or VersionControlSystem(self.version_manager)
        
        # 迭代历史
        self.iteration_histories: Dict[str, IterationHistory] = {}
        
        # 当前活跃迭代
        self.active_iterations: Dict[str, IterationInfo] = {}
        
        # 迭代索引
        self.iteration_index_path = self.version_manager.storage_backend.storage_path / "iteration_index.json"
        
        # 加载迭代历史
        self._load_iteration_histories()
    
    def _load_iteration_histories(self) -> None:
        """加载迭代历史"""
        if self.iteration_index_path.exists():
            try:
                with open(self.iteration_index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, history_data in data.items():
                    iterations = [IterationInfo(**i) for i in history_data.get("iterations", [])]
                    self.iteration_histories[key] = IterationHistory(
                        entity_id=history_data["entity_id"],
                        iterations=iterations,
                        total_iterations=history_data.get("total_iterations", 0),
                        successful_iterations=history_data.get("successful_iterations", 0),
                        failed_iterations=history_data.get("failed_iterations", 0),
                    )
                logger.info(f"加载了 {len(self.iteration_histories)} 个迭代历史")
            except Exception as e:
                logger.error(f"加载迭代历史失败: {e}")
    
    def _save_iteration_histories(self) -> None:
        """保存迭代历史"""
        try:
            data = {}
            for key, history in self.iteration_histories.items():
                data[key] = history.model_dump()
            with open(self.iteration_index_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存迭代历史失败: {e}")
    
    def start_iteration(
        self,
        entity_id: str,
        name: str,
        description: str = "",
        iteration_type: IterationType = IterationType.MANUAL,
        objective: str = "",
        planned_operations: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[str]] = None,
        created_by: str = "system",
        create_initial_snapshot: bool = True,
    ) -> IterationInfo:
        """
        开始迭代
        
        Args:
            entity_id: 实体ID
            name: 迭代名称
            description: 迭代描述
            iteration_type: 迭代类型
            objective: 迭代目标
            planned_operations: 计划操作
            dependencies: 依赖迭代ID
            created_by: 创建者
            create_initial_snapshot: 是否创建初始快照
            
        Returns:
            迭代信息
        """
        # 生成迭代ID
        iteration_id = self._generate_iteration_id(entity_id)
        
        # 获取起始版本
        latest_version = self.version_manager.get_latest_version(entity_id)
        start_version = latest_version.version if latest_version else "1.0.0"
        
        # 创建初始快照
        initial_snapshot_id = None
        if create_initial_snapshot and latest_version:
            snapshot = self.snapshot_manager.create_full_snapshot(
                entity_id,
                latest_version.file_path,
                name=f"iteration_{iteration_id}_initial",
                description=f"迭代 {iteration_id} 的初始快照",
                created_by=created_by,
            )
            initial_snapshot_id = snapshot.snapshot_id
        
        # 创建迭代信息
        iteration = IterationInfo(
            iteration_id=iteration_id,
            iteration_type=iteration_type,
            name=name,
            description=description,
            objective=objective,
            entity_id=entity_id,
            start_version=start_version,
            current_version=start_version,
            initial_snapshot_id=initial_snapshot_id,
            planned_operations=planned_operations or [],
            dependencies=dependencies or [],
            created_by=created_by,
            total_steps=len(planned_operations or []),
            state=IterationState.IN_PROGRESS,
            started_at=datetime.now(),
        )
        
        # 记录活跃迭代
        self.active_iterations[iteration_id] = iteration
        
        # 更新迭代历史
        self._add_iteration_to_history(entity_id, iteration)
        
        logger.info(f"开始迭代: {entity_id} -> {iteration_id}")
        return iteration
    
    def create_checkpoint(
        self,
        iteration_id: str,
        checkpoint_type: CheckpointType = CheckpointType.MANUAL,
        name: Optional[str] = None,
        description: str = "",
        create_snapshot: bool = True,
        validate: bool = True,
    ) -> IterationCheckpoint:
        """
        创建检查点
        
        Args:
            iteration_id: 迭代ID
            checkpoint_type: 检查点类型
            name: 检查点名称
            description: 检查点描述
            create_snapshot: 是否创建快照
            validate: 是否验证
            
        Returns:
            检查点信息
        """
        iteration = self.active_iterations.get(iteration_id)
        if iteration is None:
            # 从历史加载
            iteration = self._get_iteration_from_history(iteration_id)
        
        if iteration is None:
            raise ValueError(f"迭代 '{iteration_id}' 不存在")
        
        # 生成检查点ID
        checkpoint_id = self._generate_checkpoint_id(iteration_id)
        
        # 记录当前版本
        version_before = iteration.current_version
        
        # 创建快照
        snapshot_id = None
        if create_snapshot and iteration.current_version:
            version_info = self.version_manager.get_version(iteration.entity_id, iteration.current_version)
            if version_info:
                snapshot = self.snapshot_manager.create_full_snapshot(
                    iteration.entity_id,
                    version_info.file_path,
                    name=f"checkpoint_{checkpoint_id}",
                    description=f"检查点 {checkpoint_id} 的快照",
                )
                snapshot_id = snapshot.snapshot_id
        
        # 创建检查点
        checkpoint = IterationCheckpoint(
            checkpoint_id=checkpoint_id,
            iteration_id=iteration_id,
            checkpoint_type=checkpoint_type,
            name=name or f"checkpoint_{checkpoint_id}",
            description=description,
            version_before=version_before,
            snapshot_id=snapshot_id,
            operations=list(iteration.executed_operations),
            created_at=datetime.now(),
        )
        
        # 验证
        if validate:
            validation_result = self._validate_checkpoint(iteration.entity_id, checkpoint)
            checkpoint.is_validated = True
            checkpoint.validation_result = validation_result
        
        # 添加到迭代
        if iteration_id in self.active_iterations:
            self.active_iterations[iteration_id].checkpoints.append(checkpoint)
            self.active_iterations[iteration_id].current_checkpoint_id = checkpoint_id
        else:
            # 更新历史中的迭代
            self._update_iteration_in_history(iteration.entity_id, iteration_id, {
                "checkpoints": iteration.checkpoints + [checkpoint],
                "current_checkpoint_id": checkpoint_id,
            })
        
        logger.info(f"创建检查点: {iteration_id} -> {checkpoint_id}")
        return checkpoint
    
    def execute_operation(
        self,
        iteration_id: str,
        operation: Dict[str, Any],
        operation_func: Optional[Callable] = None,
        create_checkpoint: bool = False,
    ) -> Dict[str, Any]:
        """
        执行操作
        
        Args:
            iteration_id: 迭代ID
            operation: 操作信息
            operation_func: 操作函数
            create_checkpoint: 是否创建检查点
            
        Returns:
            执行结果
        """
        iteration = self.active_iterations.get(iteration_id)
        if iteration is None:
            raise ValueError(f"迭代 '{iteration_id}' 不存在或已结束")
        
        if iteration.state != IterationState.IN_PROGRESS:
            raise ValueError(f"迭代 '{iteration_id}' 状态为 {iteration.state}, 无法执行操作")
        
        # 操作前检查点
        if create_checkpoint:
            self.create_checkpoint(
                iteration_id,
                CheckpointType.PRE_OPERATION,
                name=f"pre_op_{operation.get('type', 'unknown')}",
            )
        
        # 执行操作
        result = {
            "operation": operation,
            "started_at": datetime.now(),
            "success": False,
        }
        
        try:
            if operation_func:
                # 使用自定义函数
                op_result = operation_func(
                    entity_id=iteration.entity_id,
                    version=iteration.current_version,
                    operation=operation,
                )
                result["result"] = op_result
                result["success"] = True
            else:
                # 使用默认操作执行器
                op_result = self._execute_default_operation(iteration, operation)
                result["result"] = op_result
                result["success"] = True
            
            result["completed_at"] = datetime.now()
            
            # 记录已执行操作
            iteration.executed_operations.append(result)
            iteration.completed_steps += 1
            iteration.progress_percentage = (
                iteration.completed_steps / iteration.total_steps * 100
                if iteration.total_steps > 0 else 100
            )
            
            # 更新版本（如果操作产生了新版本）
            if result.get("result") and result["result"].get("new_version"):
                iteration.current_version = result["result"]["new_version"]
            
            # 操作后检查点
            if create_checkpoint:
                self.create_checkpoint(
                    iteration_id,
                    CheckpointType.POST_OPERATION,
                    name=f"post_op_{operation.get('type', 'unknown')}",
                )
            
        except Exception as e:
            result["error"] = str(e)
            result["completed_at"] = datetime.now()
            iteration.errors.append({
                "operation": operation,
                "error": str(e),
                "timestamp": datetime.now(),
            })
            logger.error(f"执行操作失败: {e}")
        
        # 保存状态
        self._save_iteration_histories()
        
        return result
    
    def complete_iteration(
        self,
        iteration_id: str,
        create_final_snapshot: bool = True,
        validate: bool = True,
    ) -> IterationInfo:
        """
        完成迭代
        
        Args:
            iteration_id: 迭代ID
            create_final_snapshot: 是否创建最终快照
            validate: 是否验证
            
        Returns:
            迭代信息
        """
        iteration = self.active_iterations.get(iteration_id)
        if iteration is None:
            raise ValueError(f"迭代 '{iteration_id}' 不存在")
        
        # 更新状态
        iteration.state = IterationState.COMPLETED
        iteration.completed_at = datetime.now()
        
        # 计算时长
        if iteration.started_at:
            iteration.actual_duration = int(
                (iteration.completed_at - iteration.started_at).total_seconds()
            )
        
        # 创建最终快照
        if create_final_snapshot and iteration.current_version:
            version_info = self.version_manager.get_version(iteration.entity_id, iteration.current_version)
            if version_info:
                snapshot = self.snapshot_manager.create_full_snapshot(
                    iteration.entity_id,
                    version_info.file_path,
                    name=f"iteration_{iteration_id}_final",
                    description=f"迭代 {iteration_id} 的最终快照",
                )
                iteration.final_snapshot_id = snapshot.snapshot_id
        
        # 设置最终版本
        iteration.final_version = iteration.current_version
        
        # 验证
        if validate:
            validation_result = self._validate_iteration(iteration)
            iteration.metadata["validation_result"] = validation_result
        
        # 移除活跃迭代
        self.active_iterations.pop(iteration_id, None)
        
        # 更新历史
        self._update_iteration_in_history(iteration.entity_id, iteration_id, iteration.model_dump())
        
        # 更新迭代历史统计
        history = self.iteration_histories.get(iteration.entity_id)
        if history:
            history.successful_iterations += 1
            history.updated_at = datetime.now()
        
        self._save_iteration_histories()
        
        logger.info(f"完成迭代: {iteration_id}")
        return iteration
    
    def pause_iteration(self, iteration_id: str) -> IterationInfo:
        """
        暂停迭代
        
        Args:
            iteration_id: 迭代ID
            
        Returns:
            迭代信息
        """
        iteration = self.active_iterations.get(iteration_id)
        if iteration is None:
            raise ValueError(f"迭代 '{iteration_id}' 不存在")
        
        if iteration.state != IterationState.IN_PROGRESS:
            raise ValueError(f"迭代 '{iteration_id}' 状态为 {iteration.state}, 无法暂停")
        
        iteration.state = IterationState.PAUSED
        
        # 创建暂停时的检查点
        self.create_checkpoint(
            iteration_id,
            CheckpointType.AUTO,
            name="pause_checkpoint",
            description="暂停迭代时的自动检查点",
        )
        
        self._save_iteration_histories()
        
        logger.info(f"暂停迭代: {iteration_id}")
        return iteration
    
    def resume_iteration(self, iteration_id: str) -> IterationInfo:
        """
        恢复迭代
        
        Args:
            iteration_id: 迭代ID
            
        Returns:
            迭代信息
        """
        # 从历史加载
        iteration = self._get_iteration_from_history(iteration_id)
        if iteration is None:
            raise ValueError(f"迭代 '{iteration_id}' 不存在")
        
        if iteration.state != IterationState.PAUSED:
            raise ValueError(f"迭代 '{iteration_id}' 状态为 {iteration.state}, 无法恢复")
        
        iteration.state = IterationState.IN_PROGRESS
        
        # 添加回活跃迭代
        self.active_iterations[iteration_id] = iteration
        
        self._save_iteration_histories()
        
        logger.info(f"恢复迭代: {iteration_id}")
        return iteration
    
    def abort_iteration(
        self,
        iteration_id: str,
        reason: str = "",
        rollback: bool = True,
    ) -> IterationInfo:
        """
        中止迭代
        
        Args:
            iteration_id: 迭代ID
            reason: 中止原因
            rollback: 是否回滚
            
        Returns:
            迭代信息
        """
        iteration = self.active_iterations.get(iteration_id)
        if iteration is None:
            iteration = self._get_iteration_from_history(iteration_id)
        
        if iteration is None:
            raise ValueError(f"迭代 '{iteration_id}' 不存在")
        
        iteration.state = IterationState.ABORTED
        iteration.notes = f"中止原因: {reason}"
        
        # 回滚
        if rollback and iteration.initial_snapshot_id:
            self.restore_to_snapshot(
                iteration.entity_id,
                iteration.initial_snapshot_id,
            )
            iteration.current_version = iteration.start_version
        
        # 移除活跃迭代
        self.active_iterations.pop(iteration_id, None)
        
        # 更新历史
        self._update_iteration_in_history(iteration.entity_id, iteration_id, iteration.model_dump())
        
        # 更新统计
        history = self.iteration_histories.get(iteration.entity_id)
        if history:
            history.failed_iterations += 1
            history.updated_at = datetime.now()
        
        self._save_iteration_histories()
        
        logger.info(f"中止迭代: {iteration_id}, 原因: {reason}")
        return iteration
    
    def rollback_iteration(
        self,
        iteration_id: str,
        target_checkpoint_id: Optional[str] = None,
        target_version: Optional[str] = None,
        target_snapshot_id: Optional[str] = None,
    ) -> IterationInfo:
        """
        回滚迭代
        
        Args:
            iteration_id: 迭代ID
            target_checkpoint_id: 目标检查点ID
            target_version: 目标版本
            target_snapshot_id: 目标快照ID
            
        Returns:
            迭代信息
        """
        iteration = self.active_iterations.get(iteration_id)
        if iteration is None:
            iteration = self._get_iteration_from_history(iteration_id)
        
        if iteration is None:
            raise ValueError(f"迭代 '{iteration_id}' 不存在")
        
        # 确定回滚目标
        rollback_target = None
        
        if target_checkpoint_id:
            # 回滚到检查点
            checkpoint = self._get_checkpoint(iteration, target_checkpoint_id)
            if checkpoint:
                if checkpoint.snapshot_id:
                    self.restore_to_snapshot(iteration.entity_id, checkpoint.snapshot_id)
                rollback_target = checkpoint.version_before
                # 移除该检查点之后的操作
                iteration.executed_operations = checkpoint.operations.copy()
        
        elif target_snapshot_id:
            # 回滚到快照
            self.restore_to_snapshot(iteration.entity_id, target_snapshot_id)
            rollback_target = target_snapshot_id
        
        elif target_version:
            # 回滚到版本
            self.restore_to_version(iteration.entity_id, target_version)
            rollback_target = target_version
        
        else:
            # 回滚到初始状态
            if iteration.initial_snapshot_id:
                self.restore_to_snapshot(iteration.entity_id, iteration.initial_snapshot_id)
                rollback_target = iteration.start_version
        
        # 更新状态
        iteration.state = IterationState.REVERTED
        if rollback_target:
            iteration.current_version = rollback_target
        
        # 移除活跃迭代
        self.active_iterations.pop(iteration_id, None)
        
        # 更新历史
        self._update_iteration_in_history(iteration.entity_id, iteration_id, iteration.model_dump())
        
        self._save_iteration_histories()
        
        logger.info(f"回滚迭代: {iteration_id} -> {rollback_target}")
        return iteration
    
    def restore_to_version(
        self,
        entity_id: str,
        target_version: str,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        恢复到指定版本
        
        Args:
            entity_id: 实体ID
            target_version: 目标版本
            output_path: 输出路径
            
        Returns:
            恢复的路径
        """
        version_info = self.version_manager.get_version(entity_id, target_version)
        if version_info is None:
            logger.error(f"版本 '{target_version}' 不存在")
            return None
        
        if output_path is None:
            # 使用版本控制系统的checkout功能
            return self.vcs.checkout(entity_id, target_version)
        else:
            return self.vcs.checkout(entity_id, target_version, output_path)
    
    def restore_to_snapshot(
        self,
        entity_id: str,
        snapshot_id: str,
        output_path: Optional[Path] = None,
    ) -> bool:
        """
        恢复到指定快照
        
        Args:
            entity_id: 实体ID
            snapshot_id: 快照ID
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        # 确定输出路径
        if output_path is None:
            version_info = self.version_manager.get_latest_version(entity_id)
            if version_info:
                output_path = version_info.file_path
            else:
                output_path = Path(self.version_manager.storage_backend.storage_path) / entity_id / "restored"
        
        return self.snapshot_manager.restore_snapshot(
            entity_id, snapshot_id, output_path, verify_integrity=True
        )
    
    def restore_to_checkpoint(
        self,
        iteration_id: str,
        checkpoint_id: str,
    ) -> bool:
        """
        恢复到指定检查点
        
        Args:
            iteration_id: 迭代ID
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功
        """
        iteration = self._get_iteration_from_history(iteration_id)
        if iteration is None:
            return False
        
        checkpoint = self._get_checkpoint(iteration, checkpoint_id)
        if checkpoint is None:
            return False
        
        if checkpoint.snapshot_id:
            return self.restore_to_snapshot(iteration.entity_id, checkpoint.snapshot_id)
        
        if checkpoint.version_before:
            return self.restore_to_version(iteration.entity_id, checkpoint.version_before) is not None
        
        return False
    
    def create_restoration_plan(
        self,
        entity_id: str,
        target_version: str,
        target_snapshot_id: Optional[str] = None,
        target_checkpoint_id: Optional[str] = None,
        restoration_type: str = "version",
    ) -> RestorationPlan:
        """
        创建恢复计划
        
        Args:
            entity_id: 实体ID
            target_version: 目标版本
            target_snapshot_id: 目标快照ID
            target_checkpoint_id: 目标检查点ID
            restoration_type: 恢复类型
            
        Returns:
            恢复计划
        """
        plan_id = self._generate_plan_id(entity_id)
        
        # 创建恢复步骤
        steps = []
        
        # 步骤1: 验证当前状态
        steps.append({
            "step": 1,
            "action": "validate_current_state",
            "description": "验证当前数据状态",
        })
        
        # 步骤2: 创建恢复前备份
        steps.append({
            "step": 2,
            "action": "create_pre_backup",
            "description": "创建恢复前备份",
        })
        
        # 步骤3: 执行恢复
        steps.append({
            "step": 3,
            "action": "execute_restoration",
            "description": "执行恢复操作",
            "target_version": target_version,
            "target_snapshot_id": target_snapshot_id,
        })
        
        # 步骤4: 验证恢复结果
        steps.append({
            "step": 4,
            "action": "validate_restoration",
            "description": "验证恢复结果",
        })
        
        # 步骤5: 更新版本索引
        steps.append({
            "step": 5,
            "action": "update_version_index",
            "description": "更新版本索引",
        })
        
        plan = RestorationPlan(
            plan_id=plan_id,
            entity_id=entity_id,
            target_version=target_version,
            target_snapshot_id=target_snapshot_id,
            target_checkpoint_id=target_checkpoint_id,
            restoration_type=restoration_type,
            steps=steps,
            status="pending",
        )
        
        return plan
    
    def execute_restoration_plan(
        self,
        plan: RestorationPlan,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        执行恢复计划
        
        Args:
            plan: 恢复计划
            output_path: 输出路径
            
        Returns:
            执行结果
        """
        results = {
            "plan_id": plan.plan_id,
            "status": "executing",
            "steps_results": [],
        }
        
        plan.status = "executing"
        plan.started_at = datetime.now()
        
        for step in plan.steps:
            step_result = {
                "step": step["step"],
                "action": step["action"],
                "success": False,
            }
            
            try:
                if step["action"] == "validate_current_state":
                    # 验证当前状态
                    validation = self._validate_current_state(plan.entity_id)
                    step_result["result"] = validation
                    step_result["success"] = True
                    plan.pre_validation = validation
                
                elif step["action"] == "create_pre_backup":
                    # 创建恢复前备份
                    latest_version = self.version_manager.get_latest_version(plan.entity_id)
                    if latest_version:
                        snapshot = self.snapshot_manager.create_full_snapshot(
                            plan.entity_id,
                            latest_version.file_path,
                            name=f"pre_restoration_{plan.plan_id}",
                            description=f"恢复计划 {plan.plan_id} 的前置备份",
                        )
                        step_result["result"] = {"snapshot_id": snapshot.snapshot_id}
                        step_result["success"] = True
                
                elif step["action"] == "execute_restoration":
                    # 执行恢复
                    if plan.target_snapshot_id:
                        success = self.restore_to_snapshot(
                            plan.entity_id,
                            plan.target_snapshot_id,
                            output_path,
                        )
                        step_result["success"] = success
                    elif plan.target_version:
                        restored_path = self.restore_to_version(
                            plan.entity_id,
                            plan.target_version,
                            output_path,
                        )
                        step_result["success"] = restored_path is not None
                        step_result["result"] = {"restored_path": str(restored_path) if restored_path else None}
                
                elif step["action"] == "validate_restoration":
                    # 验证恢复结果
                    validation = self._validate_restoration_result(plan.entity_id, plan.target_version)
                    step_result["result"] = validation
                    step_result["success"] = validation.get("success", False)
                    plan.post_validation = validation
                
                elif step["action"] == "update_version_index":
                    # 更新版本索引
                    self.version_manager._save_version_index()
                    step_result["success"] = True
                
                step_result["completed_at"] = datetime.now()
                
            except Exception as e:
                step_result["error"] = str(e)
                step_result["completed_at"] = datetime.now()
                results["error"] = str(e)
                plan.status = "failed"
                break
            
            results["steps_results"].append(step_result)
            plan.current_step = step["step"]
        
        if plan.status != "failed":
            plan.status = "completed"
            plan.completed_at = datetime.now()
            results["status"] = "completed"
        
        plan.result = results
        
        return results
    
    def get_iteration(self, iteration_id: str) -> Optional[IterationInfo]:
        """
        获取迭代信息
        
        Args:
            iteration_id: 迭代ID
            
        Returns:
            迭代信息
        """
        # 先从活跃迭代查找
        if iteration_id in self.active_iterations:
            return self.active_iterations[iteration_id]
        
        # 从历史查找
        return self._get_iteration_from_history(iteration_id)
    
    def get_iteration_history(self, entity_id: str) -> Optional[IterationHistory]:
        """
        获取迭代历史
        
        Args:
            entity_id: 实体ID
            
        Returns:
            迭代历史
        """
        return self.iteration_histories.get(entity_id)
    
    def list_iterations(
        self,
        entity_id: str,
        state: Optional[IterationState] = None,
        iteration_type: Optional[IterationType] = None,
    ) -> List[IterationInfo]:
        """
        列出迭代
        
        Args:
            entity_id: 实体ID
            state: 迭代状态筛选
            iteration_type: 迭代类型筛选
            
        Returns:
            迭代列表
        """
        history = self.iteration_histories.get(entity_id)
        if not history:
            return []
        
        iterations = history.iterations
        
        # 筛选
        if state:
            iterations = [i for i in iterations if i.state == state]
        if iteration_type:
            iterations = [i for i in iterations if i.iteration_type == iteration_type]
        
        return iterations
    
    def get_iteration_statistics(self, entity_id: str) -> Dict[str, Any]:
        """
        获取迭代统计信息
        
        Args:
            entity_id: 实体ID
            
        Returns:
            统计信息
        """
        history = self.iteration_histories.get(entity_id)
        if not history:
            return {
                "entity_id": entity_id,
                "total_iterations": 0,
                "successful_iterations": 0,
                "failed_iterations": 0,
                "active_iterations": 0,
            }
        
        active_count = len([i for i in history.iterations if i.state == IterationState.IN_PROGRESS])
        
        avg_duration = 0
        completed_iterations = [i for i in history.iterations if i.state == IterationState.COMPLETED and i.actual_duration]
        if completed_iterations:
            avg_duration = sum(i.actual_duration for i in completed_iterations) / len(completed_iterations)
        
        return {
            "entity_id": entity_id,
            "total_iterations": history.total_iterations,
            "successful_iterations": history.successful_iterations,
            "failed_iterations": history.failed_iterations,
            "active_iterations": active_count,
            "average_duration_seconds": avg_duration,
        }
    
    # 内部辅助方法
    
    def _generate_iteration_id(self, entity_id: str) -> str:
        """生成迭代ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(f"{entity_id}_{timestamp}".encode()).hexdigest()[:8]
        return f"iter_{timestamp}_{hash_part}"
    
    def _generate_checkpoint_id(self, iteration_id: str) -> str:
        """生成检查点ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        hash_part = hashlib.md5(f"{iteration_id}_{timestamp}".encode()).hexdigest()[:8]
        return f"ckpt_{hash_part}"
    
    def _generate_plan_id(self, entity_id: str) -> str:
        """生成计划ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(f"{entity_id}_{timestamp}".encode()).hexdigest()[:8]
        return f"plan_{timestamp}_{hash_part}"
    
    def _add_iteration_to_history(self, entity_id: str, iteration: IterationInfo) -> None:
        """添加迭代到历史"""
        if entity_id not in self.iteration_histories:
            self.iteration_histories[entity_id] = IterationHistory(entity_id=entity_id)
        
        history = self.iteration_histories[entity_id]
        history.iterations.append(iteration)
        history.total_iterations += 1
        history.updated_at = datetime.now()
        
        self._save_iteration_histories()
    
    def _update_iteration_in_history(
        self,
        entity_id: str,
        iteration_id: str,
        updates: Dict[str, Any],
    ) -> None:
        """更新历史中的迭代"""
        history = self.iteration_histories.get(entity_id)
        if history:
            for i, iteration in enumerate(history.iterations):
                if iteration.iteration_id == iteration_id:
                    for key, value in updates.items():
                        if hasattr(history.iterations[i], key):
                            setattr(history.iterations[i], key, value)
                    break
        self._save_iteration_histories()
    
    def _get_iteration_from_history(self, iteration_id: str) -> Optional[IterationInfo]:
        """从历史获取迭代"""
        for history in self.iteration_histories.values():
            for iteration in history.iterations:
                if iteration.iteration_id == iteration_id:
                    return iteration
        return None
    
    def _get_checkpoint(
        self,
        iteration: IterationInfo,
        checkpoint_id: str,
    ) -> Optional[IterationCheckpoint]:
        """获取检查点"""
        for checkpoint in iteration.checkpoints:
            if checkpoint.checkpoint_id == checkpoint_id:
                return checkpoint
        return None
    
    def _execute_default_operation(
        self,
        iteration: IterationInfo,
        operation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行默认操作"""
        op_type = operation.get("type", "unknown")
        
        result = {"operation_type": op_type}
        
        if op_type == "create_version":
            # 创建新版本
            source_path = operation.get("source_path")
            if source_path:
                version_info = self.version_manager.create_version(
                    iteration.entity_id,
                    Path(source_path),
                    operation.get("version_type", VersionType.MINOR),
                    operation.get("description", ""),
                    operation.get("changes", []),
                    operation.get("created_by", "system"),
                )
                result["new_version"] = version_info.version
        
        elif op_type == "update_metadata":
            # 更新元数据
            version = operation.get("version", iteration.current_version)
            updates = operation.get("updates", {})
            self.version_manager.update_version(iteration.entity_id, version, updates)
        
        elif op_type == "create_snapshot":
            # 创建快照
            version = operation.get("version", iteration.current_version)
            version_info = self.version_manager.get_version(iteration.entity_id, version)
            if version_info:
                snapshot = self.snapshot_manager.create_full_snapshot(
                    iteration.entity_id,
                    version_info.file_path,
                    name=operation.get("snapshot_name", ""),
                    description=operation.get("snapshot_description", ""),
                )
                result["snapshot_id"] = snapshot.snapshot_id
        
        elif op_type == "apply_changes":
            # 应用变更
            changes = operation.get("changes", [])
            # 这里可以根据具体需求实现变更应用逻辑
            result["changes_applied"] = len(changes)
        
        return result
    
    def _validate_checkpoint(
        self,
        entity_id: str,
        checkpoint: IterationCheckpoint,
    ) -> Dict[str, Any]:
        """验证检查点"""
        validation_result = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "is_valid": True,
            "checks": [],
        }
        
        # 检查快照
        if checkpoint.snapshot_id:
            snapshot_valid = self.snapshot_manager.verify_snapshot(
                entity_id, checkpoint.snapshot_id
            )
            validation_result["checks"].append({
                "check": "snapshot_validity",
                "result": snapshot_valid,
            })
            if not snapshot_valid:
                validation_result["is_valid"] = False
        
        # 检查版本一致性
        if checkpoint.version_before:
            version_exists = self.version_manager.get_version(
                entity_id, checkpoint.version_before
            ) is not None
            validation_result["checks"].append({
                "check": "version_exists",
                "result": version_exists,
            })
            if not version_exists:
                validation_result["is_valid"] = False
        
        return validation_result
    
    def _validate_iteration(self, iteration: IterationInfo) -> Dict[str, Any]:
        """验证迭代"""
        validation_result = {
            "iteration_id": iteration.iteration_id,
            "is_valid": True,
            "checks": [],
        }
        
        # 检查版本一致性
        if iteration.final_version:
            version_info = self.version_manager.get_version(
                iteration.entity_id, iteration.final_version
            )
            validation_result["checks"].append({
                "check": "final_version_exists",
                "result": version_info is not None,
            })
        
        # 检查快照
        if iteration.final_snapshot_id:
            snapshot_valid = self.snapshot_manager.verify_snapshot(
                iteration.entity_id, iteration.final_snapshot_id
            )
            validation_result["checks"].append({
                "check": "final_snapshot_valid",
                "result": snapshot_valid,
            })
        
        # 检查操作完成度
        all_ops_executed = len(iteration.executed_operations) >= iteration.total_steps
        validation_result["checks"].append({
            "check": "operations_completed",
            "result": all_ops_executed,
        })
        
        return validation_result
    
    def _validate_current_state(self, entity_id: str) -> Dict[str, Any]:
        """验证当前状态"""
        validation_result = {
            "entity_id": entity_id,
            "is_valid": True,
            "checks": [],
        }
        
        # 检查版本
        latest_version = self.version_manager.get_latest_version(entity_id)
        validation_result["checks"].append({
            "check": "has_active_version",
            "result": latest_version is not None,
        })
        
        # 检查快照
        latest_snapshot = self.snapshot_manager.get_latest_snapshot(entity_id)
        validation_result["checks"].append({
            "check": "has_snapshot",
            "result": latest_snapshot is not None,
        })
        
        return validation_result
    
    def _validate_restoration_result(
        self,
        entity_id: str,
        target_version: str,
    ) -> Dict[str, Any]:
        """验证恢复结果"""
        validation_result = {
            "entity_id": entity_id,
            "target_version": target_version,
            "success": True,
            "checks": [],
        }
        
        # 检查恢复后的版本
        version_info = self.version_manager.get_version(entity_id, target_version)
        validation_result["checks"].append({
            "check": "version_restored",
            "result": version_info is not None,
        })
        
        if version_info:
            # 检查文件存在
            file_exists = version_info.file_path.exists()
            validation_result["checks"].append({
                "check": "file_exists",
                "result": file_exists,
            })
            
            # 检查校验和
            if version_info.checksum:
                current_checksum = self.version_manager.storage_backend.calculate_checksum(
                    version_info.file_path
                )
                checksum_match = current_checksum == version_info.checksum
                validation_result["checks"].append({
                    "check": "checksum_valid",
                    "result": checksum_match,
                })
        
        # 确定总体结果
        all_passed = all(c["result"] for c in validation_result["checks"])
        validation_result["success"] = all_passed
        
        return validation_result


# 导出所有类
__all__ = [
    "IterationState",
    "IterationType",
    "CheckpointType",
    "IterationCheckpoint",
    "IterationInfo",
    "IterationHistory",
    "RestorationPlan",
    "IterationController",
]