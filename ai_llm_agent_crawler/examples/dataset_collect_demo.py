"""
数据集收集模块使用示例

演示如何使用 dataset_collect 模块进行数据收集、流水线处理和SFT生成
"""

import json
from pathlib import Path

from ai_llm_agent_crawler.dataset_collect import (
    # 数据收集
    DataSource,
    CollectionConfig,
    CherryTreeCollector,
    ESP32DataCollector,
    MultiSourceCollector,
    # 流水线
    DoubleLayerPipeline,
    DistillConfig,
    CleanConfig,
    AuditConfig,
    IterationConfig,
    # 向量存储
    VectorStore,
    VectorConfig,
    VectorEmbedding,
    # SFT生成
    SFTGenerator,
    SFTBatchGenerator,
)


def demo_data_collection():
    """演示数据收集"""
    print("=" * 60)
    print("1. 数据收集演示")
    print("=" * 60)
    
    # 创建多源收集器
    multi_collector = MultiSourceCollector()
    
    # 注册CherryTree收集器
    ct_config = CollectionConfig(
        source_type=DataSource.CHERRYTREE,
        batch_size=100,
        enable_cache=True,
    )
    ct_collector = CherryTreeCollector(
        config=ct_config,
        ctd_path=Path("/root/workspace/cherrytree/CT_QUANTUM.ctd")
    )
    multi_collector.register(ct_collector)
    
    # 注册ESP32收集器
    esp32_config = CollectionConfig(
        source_type=DataSource.ESP32_SENSOR,
        batch_size=50,
    )
    esp32_collector = ESP32DataCollector(
        config=esp32_config,
        data_type="raw_bin"
    )
    multi_collector.register(esp32_collector)
    
    # 模拟收集数据
    mock_data = [
        {
            "content": "质能转换波函数系数 C_0=0.85, C_1=0.12, 奇点畸变度D=0.75",
            "source": "cherrytree",
            "metadata": {"node_id": "node_001"}
        },
        {
            "content": "实验测量质能转换速率 K=1.5e10，验证公式正确性",
            "source": "cherrytree",
            "metadata": {"node_id": "node_002"}
        },
        {
            "content": "理论推演：量子奇点在D>0.5时呈现时空扭曲特征",
            "source": "cherrytree",
            "metadata": {"node_id": "node_003"}
        },
    ]
    
    print(f"模拟收集了 {len(mock_data)} 条数据")
    return mock_data


def demo_pipeline(raw_data):
    """演示流水线处理"""
    print("\n" + "=" * 60)
    print("2. 双层迭代流水线演示")
    print("=" * 60)
    
    # 配置流水线
    distill_config = DistillConfig(
        compression_ratio=0.35,
        entity_types=[
            "波函数系数C_n",
            "奇点畸变度D",
            "质能转换速率K",
        ],
        top_k=6,
    )
    
    clean_config = CleanConfig(
        dedup_threshold=0.95,
        normalize_units=True,
        format_code_blocks=True,
    )
    
    audit_config = AuditConfig(
        entity_id_prefix="entity",
        verified_label="verified_physics",
        theoretical_label="theo_simulation",
    )
    
    iteration_config = IterationConfig(
        max_inner_iterations=10,
        max_outer_iterations=5,
        inner_error_threshold=0.05,
        convergence_threshold=0.99,
    )
    
    # 创建流水线
    pipeline = DoubleLayerPipeline(
        distill_config=distill_config,
        clean_config=clean_config,
        audit_config=audit_config,
        iteration_config=iteration_config,
    )
    
    # 运行流水线
    result = pipeline.run(raw_data)
    
    print(f"迭代次数: {result.iteration_count}")
    print(f"收敛状态: {result.convergence_achieved}")
    print(f"压缩比: {result.compression_ratio:.2f}")
    print(f"提取实体数: {result.entities_extracted}")
    print(f"去除重复: {result.duplicates_removed}")
    print(f"检测矛盾: {result.conflicts_detected}")
    
    # 输出样本示例
    if result.samples:
        sample = result.samples[0]
        print(f"\n样本示例:")
        print(f"  ID: {sample.sample_id}")
        print(f"  标签: {sample.labels}")
        print(f"  实体数: {len(sample.entities)}")
    
    return result


def demo_vector_store():
    """演示向量存储"""
    print("\n" + "=" * 60)
    print("3. 向量存储演示")
    print("=" * 60)
    
    # 创建向量存储
    config = VectorConfig(
        dimension=768,
        index_type="Flat",
        metric="cosine",
    )
    
    vector_store = VectorStore(config)
    
    # 添加模拟向量
    import random
    
    embeddings = []
    for i in range(5):
        # 模拟768维向量
        mock_vector = [random.random() for _ in range(768)]
        
        embedding = VectorEmbedding(
            id=f"doc_{i:03d}",
            vector=mock_vector,
            content=f"文档{i}: 质能转换相关内容...",
            metadata={"source": "cherrytree", "index": i}
        )
        
        embeddings.append(embedding)
        vector_store.add_to_index(embedding)
    
    print(f"添加了 {len(embeddings)} 个向量嵌入")
    
    # 搜索示例
    query_vector = [random.random() for _ in range(768)]
    results = vector_store.search(query_vector, top_k=3)
    
    print(f"搜索结果 (Top 3):")
    for emb, score in results["default"]:
        print(f"  {emb.id}: 相似度 {score:.4f}")
    
    return vector_store


def demo_sft_generation(pipeline_result):
    """演示SFT数据集生成"""
    print("\n" + "=" * 60)
    print("4. SFT数据集生成演示")
    print("=" * 60)
    
    # 创建生成器
    generator = SFTGenerator(
        output_dir=Path("./sft_output"),
        schema_version="1.0"
    )
    
    # 从流水线结果生成SFT样本
    samples = []
    for sample in pipeline_result.samples:
        sft_sample = generator.generate_sample(
            instruction=f"分析以下质能转换数据",
            output=sample.content,
            source=sample.labels[0] if sample.labels else "unknown",
            labels=sample.labels,
            entities=[e.to_dict() for e in sample.entities],
            quality_score=0.95 if sample.is_verified else 0.85,
        )
        samples.append(sft_sample)
    
    print(f"生成了 {len(samples)} 个SFT样本")
    
    # 保存为JSONL格式
    output_path = generator.save_to_jsonl(samples, "demo_sft_dataset.jsonl")
    print(f"保存到: {output_path}")
    
    # 显示样本示例
    if samples:
        print(f"\n样本示例 (JSONL):")
        print(samples[0].to_jsonl())
    
    return samples


def demo_skills_loading():
    """演示加载Skills元数据"""
    print("\n" + "=" * 60)
    print("5. Skills元数据加载演示")
    print("=" * 60)
    
    skills_path = Path(__file__).parent.parent / \
        "src/ai_llm_agent_crawler/dataset_collect/skills_metadata.json"
    
    with open(skills_path, "r", encoding="utf-8") as f:
        skills_data = json.load(f)
    
    print(f"Skills版本: {skills_data['version']}")
    print(f"总技能数: {skills_data['total_skills']}")
    print(f"\n技能分组:")
    
    for group_id, group_data in skills_data["skill_groups"].items():
        print(f"\n  [{group_id}] {group_data['name']}")
        print(f"      描述: {group_data['description']}")
        print(f"      技能数: {len(group_data['skills'])}")
        
        for skill in group_data['skills'][:2]:  # 显示前2个
            print(f"        - {skill['id']}: {skill['name']}")


def main():
    """主函数"""
    print("=" * 60)
    print("Dataset Collect 模块使用示例")
    print("=" * 60)
    
    # 1. 数据收集
    raw_data = demo_data_collection()
    
    # 2. 流水线处理
    pipeline_result = demo_pipeline(raw_data)
    
    # 3. 向量存储
    vector_store = demo_vector_store()
    
    # 4. SFT生成
    sft_samples = demo_sft_generation(pipeline_result)
    
    # 5. Skills加载
    demo_skills_loading()
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()