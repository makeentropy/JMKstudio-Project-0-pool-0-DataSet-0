"""
SFT数据集生成器

生成标准化SFT训练数据集,支持jsonl格式输出
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class SFTSchema(BaseModel):
    """SFT数据集Schema配置"""
    
    # 基础字段
    sample_id: str = Field(description="样本唯一ID")
    instruction: str = Field(description="指令/问题")
    input: str = Field(default="", description="输入内容")
    output: str = Field(description="输出/答案")
    
    # 元数据字段
    source: str = Field(default="unknown", description="数据来源")
    labels: List[str] = Field(default_factory=list, description="标签")
    quality_score: float = Field(default=1.0, description="质量分数")
    
    # 扩展字段
    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="提取的实体"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="推理过程(Chain of Thought)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外元数据"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "sample_id": "phy_000001",
                "instruction": "计算质能转换过程中波函数系数C_0的值",
                "input": "给定奇点畸变度D=0.75，质能转换速率K=1.5e10",
                "output": "根据质能波函数方程...",
                "source": "cherrytree",
                "labels": ["verified_physics", "quantum"],
                "quality_score": 0.95,
                "entities": [
                    {
                        "entity_type": "波函数系数C_n",
                        "entity_value": "C_0=0.85",
                        "confidence": 0.92
                    }
                ],
                "reasoning": "首先应用FFT变换...",
                "metadata": {
                    "document_id": "doc_123",
                    "timestamp": "2025-01-15T10:30:00"
                }
            }
        }


@dataclass
class SFTSample:
    """SFT样本数据结构"""
    
    sample_id: str
    instruction: str
    output: str
    input: str = ""
    source: str = "unknown"
    labels: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: Optional[str] = None
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_jsonl(self) -> str:
        """转换为JSONL格式字符串"""
        data = {
            "sample_id": self.sample_id,
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
            "source": self.source,
            "labels": self.labels,
            "quality_score": self.quality_score,
            "entities": self.entities,
        }
        
        if self.reasoning:
            data["reasoning"] = self.reasoning
        
        if self.metadata:
            data["metadata"] = self.metadata
        
        return json.dumps(data, ensure_ascii=False)
    
    def to_alpaca_format(self) -> Dict[str, str]:
        """转换为Alpaca格式"""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
        }
    
    def to_sharegpt_format(self) -> Dict[str, Any]:
        """转换为ShareGPT格式"""
        conversations = [
            {"from": "human", "value": self.instruction}
        ]
        
        if self.input:
            conversations[0]["value"] += f"\n\n{self.input}"
        
        conversations.append({"from": "gpt", "value": self.output})
        
        return {"conversations": conversations}


class SFTGenerator:
    """
    SFT数据集生成器
    
    从收集的数据生成标准化训练样本
    """
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        schema_version: str = "1.0"
    ):
        self.output_dir = output_dir or Path("./sft_output")
        self.schema_version = schema_version
        self._sample_counter = 0
    
    def generate_sample(
        self,
        instruction: str,
        output: str,
        input: str = "",
        source: str = "unknown",
        labels: Optional[List[str]] = None,
        entities: Optional[List[Dict]] = None,
        reasoning: Optional[str] = None,
        metadata: Optional[Dict] = None,
        quality_score: float = 1.0,
    ) -> SFTSample:
        """
        生成单个SFT样本
        
        Args:
            instruction: 指令文本
            output: 输出答案
            input: 输入内容
            source: 数据来源
            labels: 标签列表
            entities: 实体列表
            reasoning: 推理过程
            metadata: 元数据
            quality_score: 质量分数
            
        Returns:
            生成的SFT样本
        """
        self._sample_counter += 1
        
        # 生成唯一ID
        sample_id = self._generate_sample_id(source)
        
        sample = SFTSample(
            sample_id=sample_id,
            instruction=instruction,
            output=output,
            input=input,
            source=source,
            labels=labels or [],
            entities=entities or [],
            reasoning=reasoning,
            quality_score=quality_score,
            metadata=metadata or {},
        )
        
        return sample
    
    def generate_from_collected_data(
        self,
        collected_data: List[Dict[str, Any]],
        template: Optional[str] = None
    ) -> List[SFTSample]:
        """
        从收集的数据批量生成SFT样本
        
        Args:
            collected_data: 收集的数据列表
            template: 指令模板
            
        Returns:
            生成的SFT样本列表
        """
        samples = []
        
        for data in collected_data:
            content = data.get("content", "")
            source = data.get("source", "unknown")
            metadata = data.get("metadata", {})
            
            # 自动生成指令和输出
            instruction, output = self._auto_generate_instruction_output(
                content, template
            )
            
            # 提取实体
            entities = self._extract_entities_from_content(content)
            
            sample = self.generate_sample(
                instruction=instruction,
                output=output,
                source=source,
                entities=entities,
                metadata=metadata,
            )
            
            samples.append(sample)
        
        logger.info(f"生成了 {len(samples)} 个SFT样本")
        return samples
    
    def generate_skill_samples(
        self,
        skill_id: str,
        skill_name: str,
        skill_description: str,
        examples: List[Dict[str, str]],
        num_samples: int = 10
    ) -> List[SFTSample]:
        """
        为特定Skill生成训练样本
        
        Args:
            skill_id: Skill ID
            skill_name: Skill名称
            skill_description: Skill描述
            examples: 示例列表
            num_samples: 生成数量
            
        Returns:
            生成的SFT样本列表
        """
        samples = []
        
        for i, example in enumerate(examples[:num_samples]):
            instruction = f"[{skill_name}] {example.get('input', '')}"
            output = example.get('output', '')
            
            sample = self.generate_sample(
                instruction=instruction,
                output=output,
                source=f"skill_{skill_id}",
                labels=["skill_training", skill_id],
                metadata={
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "skill_description": skill_description,
                    "example_index": i,
                }
            )
            
            samples.append(sample)
        
        return samples
    
    def _generate_sample_id(self, source: str) -> str:
        """生成样本ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{source[:3]}_{timestamp}_{self._sample_counter:06d}"
    
    def _auto_generate_instruction_output(
        self,
        content: str,
        template: Optional[str] = None
    ) -> tuple[str, str]:
        """
        自动生成指令和输出
        
        Args:
            content: 原始内容
            template: 指令模板
            
        Returns:
            (instruction, output) 元组
        """
        # 简化实现: 将内容分割为指令和输出
        lines = content.strip().split("\n")
        
        if len(lines) >= 2:
            instruction = lines[0]
            output = "\n".join(lines[1:])
        else:
            instruction = content[:100] if len(content) > 100 else content
            output = content
        
        # 应用模板
        if template:
            instruction = template.format(content=instruction)
        
        return instruction, output
    
    def _extract_entities_from_content(
        self,
        content: str
    ) -> List[Dict[str, Any]]:
        """从内容中提取实体"""
        import re
        
        entities = []
        
        # 波函数系数
        c_matches = re.findall(r'C[_\[]?(\d+)[_\]]?\s*[=:]\s*([\d.+-eE]+)', content)
        for idx, val in c_matches:
            entities.append({
                "entity_type": "波函数系数C_n",
                "entity_value": f"C_{idx}={val}",
                "confidence": 0.9
            })
        
        # 奇点畸变度
        d_matches = re.findall(r'D\s*[=:]\s*([\d.+-eE]+)', content)
        for val in d_matches:
            entities.append({
                "entity_type": "奇点畸变度D",
                "entity_value": f"D={val}",
                "confidence": 0.85
            })
        
        return entities
    
    def save_to_jsonl(
        self,
        samples: List[SFTSample],
        filename: str = "sft_dataset.jsonl"
    ) -> Path:
        """
        保存为JSONL格式
        
        Args:
            samples: SFT样本列表
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(sample.to_jsonl() + "\n")
        
        logger.info(f"保存了 {len(samples)} 个样本到: {filepath}")
        return filepath
    
    def save_to_alpaca(
        self,
        samples: List[SFTSample],
        filename: str = "alpaca_dataset.json"
    ) -> Path:
        """保存为Alpaca格式"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.output_dir / filename
        
        alpaca_data = [sample.to_alpaca_format() for sample in samples]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(alpaca_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存了 {len(samples)} 个样本(Alpaca格式)到: {filepath}")
        return filepath
    
    def save_to_sharegpt(
        self,
        samples: List[SFTSample],
        filename: str = "sharegpt_dataset.json"
    ) -> Path:
        """保存为ShareGPT格式"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.output_dir / filename
        
        sharegpt_data = [sample.to_sharegpt_format() for sample in samples]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(sharegpt_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存了 {len(samples)} 个样本(ShareGPT格式)到: {filepath}")
        return filepath


class SFTBatchGenerator:
    """
    批量SFT生成器
    
    用于大规模数据集生成
    """
    
    def __init__(
        self,
        generator: Optional[SFTGenerator] = None,
        batch_size: int = 100
    ):
        self.generator = generator or SFTGenerator()
        self.batch_size = batch_size
    
    def generate_batch(
        self,
        data_sources: List[Dict[str, Any]],
        output_prefix: str = "batch"
    ) -> List[Path]:
        """
        批量生成数据集
        
        Args:
            data_sources: 数据源列表
            output_prefix: 输出文件前缀
            
        Returns:
            生成的文件路径列表
        """
        output_files = []
        batch_index = 0
        
        for i in range(0, len(data_sources), self.batch_size):
            batch = data_sources[i:i + self.batch_size]
            
            samples = self.generator.generate_from_collected_data(batch)
            
            filename = f"{output_prefix}_{batch_index:04d}.jsonl"
            filepath = self.generator.save_to_jsonl(samples, filename)
            
            output_files.append(filepath)
            batch_index += 1
        
        logger.info(f"批量生成了 {len(output_files)} 个文件")
        return output_files
    
    def generate_skill_dataset(
        self,
        skills: List[Dict[str, Any]],
        samples_per_skill: int = 50
    ) -> Path:
        """
        为多个Skill生成训练数据集
        
        Args:
            skills: Skill配置列表
            samples_per_skill: 每个Skill的样本数量
            
        Returns:
            生成的数据集路径
        """
        all_samples = []
        
        for skill in skills:
            skill_id = skill.get("id", "unknown")
            skill_name = skill.get("name", "Unknown Skill")
            skill_description = skill.get("description", "")
            examples = skill.get("examples", [])
            
            samples = self.generator.generate_skill_samples(
                skill_id=skill_id,
                skill_name=skill_name,
                skill_description=skill_description,
                examples=examples,
                num_samples=samples_per_skill
            )
            
            all_samples.extend(samples)
        
        # 保存合并的数据集
        filepath = self.generator.save_to_jsonl(
            all_samples,
            f"skills_dataset_{len(skills)}_skills.jsonl"
        )
        
        return filepath