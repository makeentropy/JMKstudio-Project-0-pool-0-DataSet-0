"""
Dataset Collect 模块单元测试
"""

import pytest
from pathlib import Path
import tempfile
import json

from ai_llm_agent_crawler.dataset_collect import (
    DataSource,
    CollectionConfig,
    CollectedData,
    CherryTreeCollector,
    ESP32DataCollector,
    MultiSourceCollector,
    DoubleLayerPipeline,
    DistillConfig,
    CleanConfig,
    AuditConfig,
    IterationConfig,
    VectorConfig,
    VectorEmbedding,
    VectorStore,
    FAISSVectorStore,
    SFTGenerator,
    SFTSample,
    SFTBatchGenerator,
)


class TestCollector:
    """数据收集器测试"""
    
    def test_collected_data_creation(self):
        """测试收集数据创建"""
        data = CollectedData(
            source=DataSource.CHERRYTREE,
            content="测试内容",
            metadata={"key": "value"}
        )
        
        assert data.source == DataSource.CHERRYTREE
        assert data.content == "测试内容"
        assert data.metadata == {"key": "value"}
        assert len(data.data_id) == 16
    
    def test_collection_config(self):
        """测试收集配置"""
        config = CollectionConfig(
            source_type=DataSource.CHERRYTREE,
            batch_size=50,
            enable_cache=True
        )
        
        assert config.source_type == DataSource.CHERRYTREE
        assert config.batch_size == 50
        assert config.enable_cache is True
    
    def test_multi_source_collector(self):
        """测试多源收集器"""
        collector = MultiSourceCollector()
        
        config = CollectionConfig(source_type=DataSource.CHERRYTREE)
        ct_collector = CherryTreeCollector(config)
        
        collector.register(ct_collector)
        
        assert DataSource.CHERRYTREE in collector.collectors


class TestPipeline:
    """流水线测试"""
    
    def test_distill_layer(self):
        """测试蒸馏层"""
        from ai_llm_agent_crawler.dataset_collect.pipeline import DistillLayer
        
        config = DistillConfig(compression_ratio=0.35)
        layer = DistillLayer(config)
        
        raw_data = [
            {"content": "波函数系数 C_0=0.85, C_1=0.12", "source": "test"},
            {"content": "奇点畸变度 D=0.75", "source": "test"},
        ]
        
        entities = layer.process(raw_data)
        
        assert len(entities) > 0
        assert entities[0].entity_type in ["波函数系数C_n", "奇点畸变度D"]
    
    def test_clean_layer(self):
        """测试清洗层"""
        from ai_llm_agent_crawler.dataset_collect.pipeline import CleanLayer
        
        config = CleanConfig(dedup_threshold=0.95)
        layer = CleanLayer(config)
        
        entities = []
        raw_content = [
            "第一行内容\n第二行内容",
            "第一行内容\n第二行内容",  # 重复
            "另一条内容",
        ]
        
        records = layer.process(entities, raw_content)
        
        assert len(records) == 2  # 去重后
    
    def test_audit_layer(self):
        """测试清算层"""
        from ai_llm_agent_crawler.dataset_collect.pipeline import (
            AuditLayer, CleanedRecord, DistilledEntity
        )
        
        config = AuditConfig()
        layer = AuditLayer(config)
        
        entity = DistilledEntity(
            entity_type="测试实体",
            entity_value="测试值",
            source_doc="test"
        )
        
        record = CleanedRecord(
            content="实验测量数据验证",
            entities=[entity],
            doc_hash="abc123"
        )
        
        samples = layer.process([record])
        
        assert len(samples) == 1
        assert samples[0].is_verified is True
    
    def test_double_layer_pipeline(self):
        """测试双层迭代流水线"""
        config = IterationConfig(
            max_inner_iterations=5,
            max_outer_iterations=3
        )
        
        pipeline = DoubleLayerPipeline(iteration_config=config)
        
        raw_data = [
            {"content": "测试数据1 C_0=0.85", "source": "test"},
            {"content": "测试数据2 D=0.75", "source": "test"},
        ]
        
        result = pipeline.run(raw_data)
        
        assert result.iteration_count > 0
        assert len(result.samples) > 0


class TestVectorStore:
    """向量存储测试"""
    
    def test_vector_embedding(self):
        """测试向量嵌入"""
        embedding = VectorEmbedding(
            id="test_001",
            vector=[0.1, 0.2, 0.3],
            content="测试内容",
            metadata={"source": "test"}
        )
        
        assert embedding.id == "test_001"
        assert len(embedding.vector) == 3
    
    def test_vector_store_basic(self):
        """测试向量存储基础功能"""
        config = VectorConfig(dimension=128)
        store = VectorStore(config)
        
        # 添加向量
        embedding = VectorEmbedding(
            id="test_001",
            vector=[0.1] * 128,
            content="测试",
            metadata={}
        )
        
        store.add_to_index(embedding)
        
        assert len(store.default_index.embeddings) == 1
    
    def test_vector_search(self):
        """测试向量搜索"""
        config = VectorConfig(dimension=8, metric="cosine")
        store = VectorStore(config)
        
        # 添加多个向量
        for i in range(3):
            embedding = VectorEmbedding(
                id=f"doc_{i}",
                vector=[float(i) * 0.1] * 8,
                content=f"文档{i}",
                metadata={}
            )
            store.add_to_index(embedding)
        
        # 搜索
        query = [0.5] * 8
        results = store.search(query, top_k=2)
        
        assert "default" in results
        assert len(results["default"]) == 2


class TestSFTGenerator:
    """SFT生成器测试"""
    
    def test_sft_sample_creation(self):
        """测试SFT样本创建"""
        generator = SFTGenerator()
        
        sample = generator.generate_sample(
            instruction="测试指令",
            output="测试输出",
            source="test",
            labels=["test_label"]
        )
        
        assert sample.instruction == "测试指令"
        assert sample.output == "测试输出"
        assert "test_label" in sample.labels
    
    def test_sft_sample_to_jsonl(self):
        """测试JSONL格式转换"""
        sample = SFTSample(
            sample_id="test_001",
            instruction="测试指令",
            output="测试输出"
        )
        
        jsonl = sample.to_jsonl()
        
        assert isinstance(jsonl, str)
        data = json.loads(jsonl)
        assert data["sample_id"] == "test_001"
    
    def test_sft_sample_formats(self):
        """测试不同格式转换"""
        sample = SFTSample(
            sample_id="test_001",
            instruction="指令",
            input="输入",
            output="输出"
        )
        
        # Alpaca格式
        alpaca = sample.to_alpaca_format()
        assert "instruction" in alpaca
        assert "input" in alpaca
        
        # ShareGPT格式
        sharegpt = sample.to_sharegpt_format()
        assert "conversations" in sharegpt
    
    def test_sft_save_to_jsonl(self):
        """测试保存JSONL文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = SFTGenerator(output_dir=Path(tmpdir))
            
            samples = [
                generator.generate_sample(
                    instruction=f"指令{i}",
                    output=f"输出{i}"
                )
                for i in range(3)
            ]
            
            filepath = generator.save_to_jsonl(samples, "test.jsonl")
            
            assert filepath.exists()
            assert filepath.name == "test.jsonl"
            
            # 验证内容
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            assert len(lines) == 3


class TestSFTBatchGenerator:
    """批量SFT生成器测试"""
    
    def test_batch_generation(self):
        """测试批量生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = SFTGenerator(output_dir=Path(tmpdir))
            batch_gen = SFTBatchGenerator(generator=generator, batch_size=2)
            
            data_sources = [
                {"content": f"数据{i}", "source": "test"}
                for i in range(5)
            ]
            
            output_files = batch_gen.generate_batch(data_sources, "batch")
            
            assert len(output_files) == 3  # 5个数据，batch_size=2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])