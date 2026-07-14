"""
向量存储模块

提供向量嵌入、索引构建和检索功能，基于FAISS实现
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import pickle

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)

# 尝试导入FAISS
try:
    import numpy as np
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS未安装，向量检索功能将使用简化实现")


class VectorConfig(BaseModel):
    """向量配置"""
    
    dimension: int = Field(
        default=768,
        description="向量维度"
    )
    index_type: str = Field(
        default="Flat",
        description="索引类型 (Flat, IVF, HNSW)"
    )
    nlist: int = Field(
        default=100,
        description="聚类中心数量 (IVF索引)"
    )
    metric: str = Field(
        default="cosine",
        description="距离度量 (cosine, l2, ip)"
    )


@dataclass
class VectorEmbedding:
    """向量嵌入"""
    
    id: str
    vector: List[float]
    content: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vector": self.vector,
            "content": self.content,
            "metadata": self.metadata,
        }


class VectorIndex:
    """
    向量索引基类
    """
    
    def __init__(self, config: Optional[VectorConfig] = None):
        self.config = config or VectorConfig()
        self.embeddings: List[VectorEmbedding] = []
        
    def add(self, embedding: VectorEmbedding) -> None:
        """添加向量嵌入"""
        self.embeddings.append(embedding)
    
    def add_batch(self, embeddings: List[VectorEmbedding]) -> None:
        """批量添加向量嵌入"""
        self.embeddings.extend(embeddings)
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 6
    ) -> List[Tuple[VectorEmbedding, float]]:
        """
        搜索最相似的向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回数量
            
        Returns:
            (embedding, score) 列表
        """
        # 简化实现: 使用numpy计算余弦相似度
        if not FAISS_AVAILABLE:
            return self._numpy_search(query_vector, top_k)
        
        return self._faiss_search(query_vector, top_k)
    
    def _numpy_search(
        self,
        query_vector: List[float],
        top_k: int
    ) -> List[Tuple[VectorEmbedding, float]]:
        """使用numpy计算相似度"""
        import numpy as np
        
        query = np.array(query_vector)
        results = []
        
        for emb in self.embeddings:
            vec = np.array(emb.vector)
            
            # 余弦相似度
            if self.config.metric == "cosine":
                norm_query = np.linalg.norm(query)
                norm_vec = np.linalg.norm(vec)
                
                if norm_query == 0 or norm_vec == 0:
                    score = 0.0
                else:
                    score = np.dot(query, vec) / (norm_query * norm_vec)
            
            # L2距离
            elif self.config.metric == "l2":
                score = -np.linalg.norm(query - vec)  # 负数，因为越大越好
            
            # 内积
            else:  # ip
                score = np.dot(query, vec)
            
            results.append((emb, float(score)))
        
        # 排序并返回top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def _faiss_search(
        self,
        query_vector: List[float],
        top_k: int
    ) -> List[Tuple[VectorEmbedding, float]]:
        """使用FAISS搜索"""
        import numpy as np
        
        # 构建FAISS索引
        vectors = np.array([e.vector for e in self.embeddings], dtype=np.float32)
        
        if self.config.metric == "cosine":
            # 归一化
            faiss.normalize_L2(vectors)
            index = faiss.IndexFlatIP(self.config.dimension)
        elif self.config.metric == "l2":
            index = faiss.IndexFlatL2(self.config.dimension)
        else:  # ip
            index = faiss.IndexFlatIP(self.config.dimension)
        
        index.add(vectors)
        
        # 搜索
        query = np.array([query_vector], dtype=np.float32)
        if self.config.metric == "cosine":
            faiss.normalize_L2(query)
        
        scores, indices = index.search(query, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.embeddings):
                emb = self.embeddings[idx]
                score = float(scores[0][i])
                results.append((emb, score))
        
        return results
    
    def save(self, path: Path) -> None:
        """保存索引"""
        data = {
            "config": self.config.dict(),
            "embeddings": [e.to_dict() for e in self.embeddings],
        }
        
        with open(path, "wb") as f:
            pickle.dump(data, f)
        
        logger.info(f"向量索引已保存: {path}")
    
    def load(self, path: Path) -> None:
        """加载索引"""
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        self.config = VectorConfig(**data["config"])
        self.embeddings = [
            VectorEmbedding(**e) for e in data["embeddings"]
        ]
        
        logger.info(f"向量索引已加载: {path}, {len(self.embeddings)} 个向量")


class VectorStore:
    """
    向量存储
    
    管理多个向量索引，支持多领域检索
    """
    
    def __init__(self, config: Optional[VectorConfig] = None):
        self.config = config or VectorConfig()
        self.indices: Dict[str, VectorIndex] = {}
        self.default_index = VectorIndex(self.config)
    
    def create_index(
        self,
        name: str,
        config: Optional[VectorConfig] = None
    ) -> VectorIndex:
        """创建新索引"""
        idx_config = config or self.config
        index = VectorIndex(idx_config)
        self.indices[name] = index
        return index
    
    def get_index(self, name: str) -> Optional[VectorIndex]:
        """获取索引"""
        return self.indices.get(name)
    
    def add_to_index(
        self,
        embedding: VectorEmbedding,
        index_name: Optional[str] = None
    ) -> None:
        """添加向量到索引"""
        if index_name:
            if index_name not in self.indices:
                self.create_index(index_name)
            self.indices[index_name].add(embedding)
        else:
            self.default_index.add(embedding)
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 6,
        index_names: Optional[List[str]] = None
    ) -> Dict[str, List[Tuple[VectorEmbedding, float]]]:
        """
        搜索向量
        
        Args:
            query_vector: 查询向量
            top_k: 每个索引返回数量
            index_names: 搜索的索引名称列表，None表示使用默认索引
            
        Returns:
            按索引名称分组的搜索结果
        """
        results = {}
        
        if index_names:
            for name in index_names:
                index = self.indices.get(name)
                if index:
                    results[name] = index.search(query_vector, top_k)
        else:
            results["default"] = self.default_index.search(query_vector, top_k)
        
        return results
    
    def save_all(self, base_path: Path) -> None:
        """保存所有索引"""
        base_path.mkdir(parents=True, exist_ok=True)
        
        # 保存默认索引
        self.default_index.save(base_path / "default.index")
        
        # 保存其他索引
        for name, index in self.indices.items():
            index.save(base_path / f"{name}.index")
        
        logger.info(f"所有索引已保存到: {base_path}")
    
    def load_all(self, base_path: Path) -> None:
        """加载所有索引"""
        if not base_path.exists():
            logger.warning(f"索引目录不存在: {base_path}")
            return
        
        for file_path in base_path.glob("*.index"):
            name = file_path.stem
            if name == "default":
                self.default_index.load(file_path)
            else:
                index = VectorIndex(self.config)
                index.load(file_path)
                self.indices[name] = index


class FAISSVectorStore(VectorStore):
    """
    FAISS向量存储
    
    提供优化的FAISS索引管理
    """
    
    def __init__(self, config: Optional[VectorConfig] = None):
        super().__init__(config)
        
        if not FAISS_AVAILABLE:
            logger.warning("FAISS未安装，将使用基础实现")
    
    def build_ivf_index(
        self,
        embeddings: List[VectorEmbedding],
        nlist: Optional[int] = None
    ) -> None:
        """
        构建IVF索引
        
        Args:
            embeddings: 向量嵌入列表
            nlist: 聚类中心数量
        """
        if not FAISS_AVAILABLE:
            logger.warning("FAISS未安装，无法构建IVF索引")
            return
        
        import numpy as np
        
        nlist = nlist or self.config.nlist
        vectors = np.array([e.vector for e in embeddings], dtype=np.float32)
        
        # 创建IVF索引
        quantizer = faiss.IndexFlatL2(self.config.dimension)
        index = faiss.IndexIVFFlat(
            quantizer,
            self.config.dimension,
            nlist
        )
        
        # 训练索引
        index.train(vectors)
        index.add(vectors)
        logger.info(f"IVF索引构建完成: {len(embeddings)} 个向量, {nlist} 个聚类中心")