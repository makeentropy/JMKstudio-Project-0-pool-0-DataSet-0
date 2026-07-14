"""
数据集合成双层迭代流水线

实现蒸馏-清洗-清算双层迭代收敛机制:
- 蒸馏层(DISTILL): 向量关联提取核心实体
- 清洗层(CLEAN): 聚类去重、格式化、过滤
- 清算层(AUDIT): 实体ID统一、双标签分类、矛盾剔除
- 双层迭代: 内层自校验 + 外层全量收敛
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
from datetime import datetime

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class PipelineStage(str, Enum):
    """流水线阶段"""
    DISTILL = "distill"
    CLEAN = "clean"
    AUDIT = "audit"


class DistillConfig(BaseModel):
    """蒸馏配置"""
    
    compression_ratio: float = Field(
        default=0.35,
        description="压缩比例目标"
    )
    entity_types: List[str] = Field(
        default_factory=lambda: [
            "波函数系数C_n",
            "奇点畸变度D",
            "质能转换速率K",
            "熵耗散值",
            "ESP32采样参数",
            "黄金几何参数",
        ],
        description="提取的实体类型"
    )
    top_k: int = Field(
        default=6,
        description="向量召回TopK"
    )


class CleanConfig(BaseModel):
    """清洗配置"""
    
    dedup_threshold: float = Field(
        default=0.95,
        description="去重相似度阈值"
    )
    normalize_units: bool = Field(
        default=True,
        description="是否归一化物理单位"
    )
    format_code_blocks: bool = Field(
        default=True,
        description="是否格式化代码块"
    )
    filter_patterns: List[str] = Field(
        default_factory=lambda: [
            r"https?://[^\s]+",  # 过滤URL
            r"[\u4e00-\u9fa5]{0,2}水印",  # 过滤水印
        ],
        description="过滤模式"
    )


class AuditConfig(BaseModel):
    """清算配置"""
    
    entity_id_prefix: str = Field(
        default="entity",
        description="实体ID前缀"
    )
    verified_label: str = Field(
        default="verified_physics",
        description="已验证物理标签"
    )
    theoretical_label: str = Field(
        default="theo_simulation",
        description="理论推演标签"
    )
    conflict_threshold: float = Field(
        default=0.8,
        description="矛盾检测阈值"
    )


class IterationConfig(BaseModel):
    """迭代配置"""
    
    max_inner_iterations: int = Field(
        default=10,
        description="最大内层迭代次数"
    )
    max_outer_iterations: int = Field(
        default=5,
        description="最大外层迭代次数"
    )
    inner_error_threshold: float = Field(
        default=0.05,
        description="内层误差阈值"
    )
    convergence_threshold: float = Field(
        default=0.99,
        description="收敛一致性阈值"
    )


@dataclass
class DistilledEntity:
    """蒸馏提取的实体"""
    
    entity_type: str
    entity_value: str
    source_doc: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "source_doc": self.source_doc,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class CleanedRecord:
    """清洗后的记录"""
    
    content: str
    entities: List[DistilledEntity]
    doc_hash: str
    quality_score: float = 1.0
    duplicates_removed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "entities": [e.to_dict() for e in self.entities],
            "doc_hash": self.doc_hash,
            "quality_score": self.quality_score,
            "duplicates_removed": self.duplicates_removed,
        }


@dataclass
class AuditedSample:
    """清算后的样本"""
    
    sample_id: str
    content: str
    entities: List[DistilledEntity]
    labels: List[str]
    is_verified: bool
    conflicts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "content": self.content,
            "entities": [e.to_dict() for e in self.entities],
            "labels": self.labels,
            "is_verified": self.is_verified,
            "conflicts": self.conflicts,
        }


@dataclass
class PipelineResult:
    """流水线执行结果"""
    
    samples: List[AuditedSample]
    iteration_count: int
    convergence_achieved: bool
    compression_ratio: float
    entities_extracted: int
    duplicates_removed: int
    conflicts_detected: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "samples": [s.to_dict() for s in self.samples],
            "iteration_count": self.iteration_count,
            "convergence_achieved": self.convergence_achieved,
            "compression_ratio": self.compression_ratio,
            "entities_extracted": self.entities_extracted,
            "duplicates_removed": self.duplicates_removed,
            "conflicts_detected": self.conflicts_detected,
            "timestamp": self.timestamp.isoformat(),
        }


class DistillLayer:
    """
    蒸馏层
    
    从原始数据中提取核心实体和关键信息
    """
    
    def __init__(self, config: Optional[DistillConfig] = None):
        self.config = config or DistillConfig()
    
    def process(
        self,
        raw_data: List[Dict[str, Any]],
        vector_results: Optional[List[Dict]] = None
    ) -> List[DistilledEntity]:
        """
        处理原始数据，提取实体
        
        Args:
            raw_data: 原始数据列表
            vector_results: 向量检索结果
            
        Returns:
            提取的实体列表
        """
        entities = []
        
        for data in raw_data:
            content = data.get("content", "")
            source = data.get("source", "unknown")
            
            # 提取实体 (简化版，实际应用中使用NLP/LLM)
            extracted = self._extract_entities(content, source)
            entities.extend(extracted)
        
        logger.info(f"蒸馏层提取了 {len(entities)} 个实体")
        return entities
    
    def _extract_entities(
        self,
        content: str,
        source: str
    ) -> List[DistilledEntity]:
        """提取实体 (简化实现)"""
        import re
        
        entities = []
        
        # 波函数系数 C_n
        c_n_matches = re.findall(r'C[_\[]?(\d+)[_\]]?\s*[=:]\s*([\d.+-eE]+)', content)
        for match in c_n_matches:
            entities.append(DistilledEntity(
                entity_type="波函数系数C_n",
                entity_value=f"C_{match[0]}={match[1]}",
                source_doc=source,
            ))
        
        # 奇点畸变度 D
        d_matches = re.findall(r'D\s*[=:]\s*([\d.+-eE]+)', content)
        for match in d_matches:
            entities.append(DistilledEntity(
                entity_type="奇点畸变度D",
                entity_value=f"D={match}",
                source_doc=source,
            ))
        
        # 质能转换速率 K
        k_matches = re.findall(r'K\s*[=:]\s*([\d.+-eE]+)', content)
        for match in k_matches:
            entities.append(DistilledEntity(
                entity_type="质能转换速率K",
                entity_value=f"K={match}",
                source_doc=source,
            ))
        
        return entities


class CleanLayer:
    """
    清洗层
    
    去重、格式化、过滤无效内容
    """
    
    def __init__(self, config: Optional[CleanConfig] = None):
        self.config = config or CleanConfig()
    
    def process(
        self,
        entities: List[DistilledEntity],
        raw_content: List[str]
    ) -> List[CleanedRecord]:
        """
        清洗数据
        
        Args:
            entities: 蒸馏提取的实体
            raw_content: 原始内容列表
            
        Returns:
            清洗后的记录列表
        """
        cleaned_records = []
        seen_hashes = set()
        duplicates = 0
        
        for i, content in enumerate(raw_content):
            # 计算内容哈希
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # 去重检查
            if content_hash in seen_hashes:
                duplicates += 1
                continue
            
            seen_hashes.add(content_hash)
            
            # 格式化代码块
            if self.config.format_code_blocks:
                content = self._format_code_blocks(content)
            
            # 过滤无效内容
            content = self._filter_content(content)
            
            # 关联实体
            related_entities = [
                e for e in entities
                if e.source_doc in content
            ]
            
            # 计算质量分数
            quality_score = self._calculate_quality(content)
            
            record = CleanedRecord(
                content=content,
                entities=related_entities,
                doc_hash=content_hash,
                quality_score=quality_score,
                duplicates_removed=duplicates,
            )
            
            cleaned_records.append(record)
        
        logger.info(f"清洗层处理完成，去除 {duplicates} 个重复")
        return cleaned_records
    
    def _format_code_blocks(self, content: str) -> str:
        """格式化代码块"""
        import re
        # 标准化代码块格式
        content = re.sub(r'```(\w*)\n', r'```\1\n', content)
        return content
    
    def _filter_content(self, content: str) -> str:
        """过滤无效内容"""
        import re
        for pattern in self.config.filter_patterns:
            content = re.sub(pattern, "", content)
        return content.strip()
    
    def _calculate_quality(self, content: str) -> float:
        """计算质量分数"""
        score = 1.0
        
        # 检查长度
        if len(content) < 50:
            score *= 0.5
        
        # 检查是否有实际内容
        if not any(c.isalpha() for c in content):
            score *= 0.3
        
        return score


class AuditLayer:
    """
    清算层
    
    实体ID统一、双标签分类、矛盾检测
    """
    
    def __init__(self, config: Optional[AuditConfig] = None):
        self.config = config or AuditConfig()
        self._entity_id_counter = 0
    
    def process(
        self,
        cleaned_records: List[CleanedRecord]
    ) -> List[AuditedSample]:
        """
        清算数据
        
        Args:
            cleaned_records: 清洗后的记录
            
        Returns:
            清算后的样本列表
        """
        audited_samples = []
        conflicts_detected = 0
        
        for record in cleaned_records:
            # 统一实体ID
            entities_with_ids = self._unify_entity_ids(record.entities)
            
            # 双标签分类
            labels = self._classify_labels(record.content)
            
            # 检测矛盾
            conflicts = self._detect_conflicts(entities_with_ids)
            if conflicts:
                conflicts_detected += len(conflicts)
            
            # 生成样本ID
            self._entity_id_counter += 1
            sample_id = f"{self.config.entity_id_prefix}_{self._entity_id_counter:06d}"
            
            sample = AuditedSample(
                sample_id=sample_id,
                content=record.content,
                entities=entities_with_ids,
                labels=labels,
                is_verified=self.config.verified_label in labels,
                conflicts=conflicts,
            )
            
            audited_samples.append(sample)
        
        logger.info(f"清算层完成，检测到 {conflicts_detected} 个矛盾")
        return audited_samples
    
    def _unify_entity_ids(
        self,
        entities: List[DistilledEntity]
    ) -> List[DistilledEntity]:
        """统一实体ID"""
        # 为每个实体添加唯一ID
        for entity in entities:
            entity.metadata["entity_id"] = hashlib.md5(
                f"{entity.entity_type}_{entity.entity_value}".encode()
            ).hexdigest()[:12]
        return entities
    
    def _classify_labels(self, content: str) -> List[str]:
        """分类标签"""
        labels = []
        
        # 简单关键词判断
        verified_keywords = ["实验", "测量", "验证", "公式", "标准"]
        theoretical_keywords = ["推测", "假设", "理论", "模型", "仿真"]
        
        if any(kw in content for kw in verified_keywords):
            labels.append(self.config.verified_label)
        
        if any(kw in content for kw in theoretical_keywords):
            labels.append(self.config.theoretical_label)
        
        return labels
    
    def _detect_conflicts(
        self,
        entities: List[DistilledEntity]
    ) -> List[str]:
        """检测实体冲突"""
        conflicts = []
        
        # 检查相同类型实体的值是否冲突
        entity_values: Dict[str, List[str]] = {}
        
        for entity in entities:
            if entity.entity_type not in entity_values:
                entity_values[entity.entity_type] = []
            entity_values[entity.entity_type].append(entity.entity_value)
        
        # 简化冲突检测
        for entity_type, values in entity_values.items():
            if len(values) > 1 and len(set(values)) > 1:
                conflicts.append(f"{entity_type}: 多个不同值 {values}")
        
        return conflicts


class DoubleLayerPipeline:
    """
    双层迭代流水线
    
    整合蒸馏、清洗、清算三层，实现双层迭代收敛
    """
    
    def __init__(
        self,
        distill_config: Optional[DistillConfig] = None,
        clean_config: Optional[CleanConfig] = None,
        audit_config: Optional[AuditConfig] = None,
        iteration_config: Optional[IterationConfig] = None,
    ):
        self.distill_layer = DistillLayer(distill_config)
        self.clean_layer = CleanLayer(clean_config)
        self.audit_layer = AuditLayer(audit_config)
        self.iteration_config = iteration_config or IterationConfig()
        
        self._previous_hash: Optional[str] = None
    
    def run(
        self,
        raw_data: List[Dict[str, Any]],
        vector_results: Optional[List[Dict]] = None
    ) -> PipelineResult:
        """
        运行双层迭代流水线
        
        Args:
            raw_data: 原始数据
            vector_results: 向量检索结果
            
        Returns:
            流水线执行结果
        """
        iteration_count = 0
        convergence_achieved = False
        all_samples: List[AuditedSample] = []
        
        # 外层迭代
        for outer_iter in range(self.iteration_config.max_outer_iterations):
            iteration_count += 1
            logger.info(f"开始外层迭代 {outer_iter + 1}")
            
            # 执行三层流水线
            entities = self.distill_layer.process(raw_data, vector_results)
            
            raw_content = [d.get("content", "") for d in raw_data]
            cleaned_records = self.clean_layer.process(entities, raw_content)
            
            samples = self.audit_layer.process(cleaned_records)
            
            # 内层自校验
            samples = self._inner_iteration(samples)
            
            # 检查收敛
            current_hash = self._compute_hash(samples)
            
            if self._previous_hash and current_hash == self._previous_hash:
                convergence_achieved = True
                logger.info("双层迭代收敛完成")
                break
            
            self._previous_hash = current_hash
            all_samples = samples
        
        # 计算统计信息
        compression_ratio = self._calculate_compression(raw_data, all_samples)
        entities_extracted = sum(len(s.entities) for s in all_samples)
        duplicates_removed = getattr(self.clean_layer, '_duplicates', 0)
        conflicts_detected = sum(len(s.conflicts) for s in all_samples)
        
        result = PipelineResult(
            samples=all_samples,
            iteration_count=iteration_count,
            convergence_achieved=convergence_achieved,
            compression_ratio=compression_ratio,
            entities_extracted=entities_extracted,
            duplicates_removed=duplicates_removed,
            conflicts_detected=conflicts_detected,
        )
        
        return result
    
    def _inner_iteration(
        self,
        samples: List[AuditedSample]
    ) -> List[AuditedSample]:
        """
        内层迭代自校验
        
        Args:
            samples: 待校验样本
            
        Returns:
            校验后的样本
        """
        validated_samples = []
        
        for sample in samples:
            # 内层迭代
            for inner_iter in range(self.iteration_config.max_inner_iterations):
                # 自校验
                error = self._self_validate(sample)
                
                if error < self.iteration_config.inner_error_threshold:
                    validated_samples.append(sample)
                    break
                
                # 尝试修正 (简化版)
                sample = self._auto_correct(sample)
            
            else:
                # 达到最大迭代次数，接受当前样本
                validated_samples.append(sample)
        
        return validated_samples
    
    def _self_validate(self, sample: AuditedSample) -> float:
        """自校验"""
        error = 0.0
        
        # 检查实体一致性
        if sample.conflicts:
            error += 0.1 * len(sample.conflicts)
        
        # 检查标签
        if not sample.labels:
            error += 0.05
        
        return error
    
    def _auto_correct(self, sample: AuditedSample) -> AuditedSample:
        """自动修正"""
        # 简化实现: 移除冲突实体
        if sample.conflicts:
            sample.entities = [
                e for e in sample.entities
                if not any(c in str(e.entity_value) for c in sample.conflicts)
            ]
            sample.conflicts = []
        
        return sample
    
    def _compute_hash(self, samples: List[AuditedSample]) -> str:
        """计算样本哈希"""
        content = json.dumps([s.sample_id for s in samples], sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _calculate_compression(
        self,
        raw_data: List[Dict],
        samples: List[AuditedSample]
    ) -> float:
        """计算压缩比"""
        if not raw_data:
            return 0.0
        
        raw_size = sum(len(str(d)) for d in raw_data)
        processed_size = sum(len(s.content) for s in samples)
        
        if raw_size == 0:
            return 0.0
        
        return processed_size / raw_size