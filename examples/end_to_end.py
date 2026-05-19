#!/usr/bin/env python3
"""
端到端完整示例

本示例展示了从数据收集、清洗、标注到数据集生成的完整流程。
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collector import (
    FileCollector,
    StorageManager,
    AgentInteraction,
    ToolCall
)
from src.cleaner import CleaningPipeline
from src.annotator import (
    SemiAutoAnnotator,
    AnnotationStorage,
    QualityChecker
)
from src.generator import (
    DatasetGenerationPipeline,
    ExportFormat
)


def create_sample_data_file(output_path: Path):
    """创建示例数据文件"""
    sample_data = {
        "interactions": [
            {
                "user_input": "你好，请问如何学习 Python？",
                "agent_response": "你好！学习 Python 可以从官方教程开始，然后多做练习。",
                "metadata": {"category": "tutorial", "source": "manual"}
            },
            {
                "user_input": "谢谢，你的回答很有帮助！",
                "agent_response": "不客气，很高兴能帮到你。",
                "metadata": {"category": "feedback", "source": "manual"}
            },
            {
                "user_input": "这个答案不对，你能重新回答吗？",
                "agent_response": "抱歉，让我重新解释一下。",
                "tool_calls": [
                    {
                        "name": "search_info",
                        "arguments": {"query": "Python 基础教程"},
                        "result": "找到相关教程"
                    }
                ],
                "metadata": {"category": "correction", "source": "manual"}
            },
            {
                "user_input": "请帮我找一下关于机器学习的资料",
                "agent_response": "好的，我来帮你搜索相关资料。",
                "metadata": {"category": "search", "source": "manual"}
            },
            {
                "user_input": "这个回答太棒了，完美解决了我的问题！",
                "agent_response": "非常感谢您的反馈，这对我们很重要。",
                "metadata": {"category": "positive_feedback", "source": "manual"}
            },
            {
                "user_input": "你好，请问如何学习 Python？",
                "agent_response": "你好！学习 Python 可以从官方教程开始，然后多做练习。",
                "metadata": {"category": "duplicate", "source": "manual"}
            },
            {
                "user_input": "Hello, my email is test@example.com, please help me",
                "agent_response": "Sure! Contact me at 123-456-7890",
                "metadata": {"category": "sensitive", "source": "manual"}
            }
        ]
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    return output_path


def step1_collect_data(sample_file: Path) -> list[AgentInteraction]:
    """步骤 1: 收集数据"""
    print("\n" + "="*80)
    print("步骤 1: 数据收集")
    print("="*80)
    
    # 使用 FileCollector 收集数据
    collector = FileCollector(str(sample_file), format_type="json")
    interactions = collector.collect()
    
    print(f"\n收集到 {len(interactions)} 条交互数据:")
    for i, interaction in enumerate(interactions, 1):
        print(f"\n  交互 {i}:")
        print(f"    用户: {interaction.user_input[:50]}...")
        print(f"    助手: {interaction.agent_response[:50]}...")
    
    # 保存原始数据
    storage = StorageManager()
    raw_path = storage.save(interactions, filename="raw_data.jsonl")
    print(f"\n原始数据已保存到: {raw_path}")
    
    return interactions


def step2_clean_data(interactions: list[AgentInteraction]) -> list[AgentInteraction]:
    """步骤 2: 清洗数据"""
    print("\n" + "="*80)
    print("步骤 2: 数据清洗")
    print("="*80)
    
    # 创建清洗流水线
    pipeline = CleaningPipeline(
        deduplication_method="content",
        min_text_length=3,
        sanitize_sensitive=True,
        normalize_text=True
    )
    
    # 清洗前评估
    print("\n清洗前质量评估:")
    metrics_before = pipeline.evaluate(interactions)
    print(f"  总数据量: {metrics_before.total_count}")
    print(f"  有效数据: {metrics_before.valid_count}")
    print(f"  整体质量: {metrics_before.overall_score:.2f}")
    
    # 执行清洗
    cleaned_data = pipeline.process(interactions)
    
    # 清洗后评估
    print("\n清洗后质量评估:")
    metrics_after = pipeline.evaluate(cleaned_data)
    print(f"  总数据量: {metrics_after.total_count}")
    print(f"  有效数据: {metrics_after.valid_count}")
    print(f"  整体质量: {metrics_after.overall_score:.2f}")
    print(f"  移除数据: {len(interactions) - len(cleaned_data)} 条")
    
    # 展示清洗效果
    print("\n清洗后数据预览:")
    for i, interaction in enumerate(cleaned_data, 1):
        print(f"\n  交互 {i}:")
        print(f"    用户: {interaction.user_input}")
        print(f"    助手: {interaction.agent_response}")
    
    return cleaned_data


def step3_annotate_data(cleaned_data: list[AgentInteraction]):
    """步骤 3: 标注数据"""
    print("\n" + "="*80)
    print("步骤 3: 数据标注")
    print("="*80)
    
    # 使用半自动标注器
    annotator = SemiAutoAnnotator()
    annotated_data_list = annotator.annotate_batch(cleaned_data)
    
    print(f"\n已标注 {len(annotated_data_list)} 条数据:")
    for i, data in enumerate(annotated_data_list, 1):
        print(f"\n  交互 {i}:")
        print(f"    用户: {data.original_interaction.user_input}")
        print(f"    标注:")
        for ann in data.annotations:
            print(f"      - {ann.label.value}: {ann.confidence:.2f}")
    
    # 质量检查
    print("\n标注质量检查:")
    checker = QualityChecker(low_confidence_threshold=0.5)
    quality_metrics = checker.assess_batch(annotated_data_list)
    print(f"  总标注数: {quality_metrics.total_annotations}")
    print(f"  平均置信度: {quality_metrics.average_confidence:.2f}")
    print(f"  低置信度数: {quality_metrics.low_confidence_count}")
    
    # 保存标注数据
    storage = AnnotationStorage()
    anno_path = storage.save_batch(annotated_data_list)
    print(f"\n标注数据已保存到: {anno_path}")
    
    return annotated_data_list


def step4_generate_dataset(annotated_data_list):
    """步骤 4: 生成数据集"""
    print("\n" + "="*80)
    print("步骤 4: 数据集生成")
    print("="*80)
    
    # 创建数据集生成流水线
    pipeline = DatasetGenerationPipeline(
        train_ratio=0.7,
        val_ratio=0.2,
        test_ratio=0.1,
        enable_augmentation=False,
        export_format=ExportFormat.JSONL
    )
    
    # 运行流水线
    try:
        result = pipeline.run()
        
        print("\n数据集生成成功!")
        print(f"\n输出目录: {result['output_dir']}")
        
        print("\n数据集划分信息:")
        for split_name, count in result['split_info'].items():
            print(f"  {split_name}: {count} 条")
        
        print("\n导出文件路径:")
        for split_name, path in result['export_paths'].items():
            print(f"  {split_name}: {path}")
        
        return result
    except Exception as e:
        print(f"\n数据集生成失败: {e}")
        return None


def main():
    """主函数"""
    print("\n" + "="*80)
    print("Agent History Dataset - 端到端完整示例")
    print("="*80)
    
    # 创建临时示例数据文件
    temp_dir = Path(__file__).parent.parent / "data" / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    sample_file = temp_dir / "sample_interactions.json"
    
    try:
        # 创建示例数据
        print("\n正在创建示例数据文件...")
        create_sample_data_file(sample_file)
        print(f"示例数据已创建: {sample_file}")
        
        # 执行完整流程
        interactions = step1_collect_data(sample_file)
        cleaned_data = step2_clean_data(interactions)
        annotated_data = step3_annotate_data(cleaned_data)
        dataset_result = step4_generate_dataset(annotated_data)
        
        # 完成
        print("\n" + "="*80)
        print("端到端流程执行完成!")
        print("="*80)
        
        if dataset_result:
            print(f"\n最终数据集保存在: {dataset_result['output_dir']}")
            print("\n你可以使用以下代码加载数据集:")
            print("  from datasets import load_dataset")
            print(f"  dataset = load_dataset('json', data_files='{dataset_result['export_paths']['train']}')")
        
    finally:
        # 清理临时文件
        if sample_file.exists():
            sample_file.unlink()
        if temp_dir.exists() and not list(temp_dir.iterdir()):
            temp_dir.rmdir()


if __name__ == "__main__":
    main()
