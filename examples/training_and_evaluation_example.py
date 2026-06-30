#!/usr/bin/env python3
"""
训练集成与评估模块使用示例
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)

from src.generator import (
    AgentTrainingIntegration,
    TrainingConfig,
    TrainingFramework,
    DatasetLoader,
    AgentEvaluator,
    BenchmarkSuite,
)
from config.config import settings


def example_dataset_loading():
    """示例 1: 加载数据集"""
    print("\n" + "=" * 60)
    print("示例 1: 加载数据集")
    print("=" * 60)
    
    loader = DatasetLoader()
    
    latest_dataset = loader.find_latest_dataset()
    if latest_dataset:
        print(f"找到最新数据集: {latest_dataset}")
        
        dataset_dict = loader.load_from_dir(latest_dataset)
        print(f"数据集加载成功!")
        for split_name, split_data in dataset_dict.items():
            print(f"  {split_name}: {len(split_data)} 个样本")
            
        return dataset_dict
    else:
        print("未找到数据集")
        return None


def example_training_preparation():
    """示例 2: 准备训练数据"""
    print("\n" + "=" * 60)
    print("示例 2: 准备训练数据")
    print("=" * 60)
    
    config = TrainingConfig(
        framework=TrainingFramework.HUGGINGFACE,
        batch_size=16,
        learning_rate=3e-5,
        num_epochs=3,
    )
    
    trainer = AgentTrainingIntegration(config=config)
    
    dataset_dict = trainer.prepare_dataset(
        format_type="chat",
        system_prompt="你是一个有用的助手。",
        min_quality_score=0.0,
        verified_only=False,
    )
    
    print(f"训练数据准备完成!")
    for split_name, split_data in dataset_dict.items():
        print(f"  {split_name}: {len(split_data)} 个样本")
        if len(split_data) > 0:
            print(f"  示例: {split_data[0]}")
            
    return trainer


def example_evaluation():
    """示例 3: 评估智能体"""
    print("\n" + "=" * 60)
    print("示例 3: 评估智能体")
    print("=" * 60)
    
    def dummy_agent(user_input: str) -> str:
        """模拟一个简单的智能体"""
        responses = {
            "你好": "你好！有什么我可以帮你的吗？",
            "谢谢": "不客气！",
            "太短了": "好的，我会提供更长的回答。",
        }
        return responses.get(user_input, f"收到: {user_input}")
    
    evaluator = AgentEvaluator(model_name="dummy_agent_v1")
    
    benchmark_result = evaluator.evaluate(
        agent_fn=dummy_agent,
        metrics=["exact_match"],
        benchmark_name="basic_test",
    )
    
    print(f"\n评估结果:")
    for metric in benchmark_result.metrics:
        print(f"  {metric.metric_name}: {metric.value:.4f}")
        
    save_path = evaluator.save_results(benchmark_result)
    print(f"\n结果已保存到: {save_path}")
    
    return benchmark_result


def example_benchmark_suite():
    """示例 4: 基准测试套件"""
    print("\n" + "=" * 60)
    print("示例 4: 基准测试套件")
    print("=" * 60)
    
    def simple_agent(user_input: str) -> str:
        return f"简单回答: {user_input}"
    
    def fancy_agent(user_input: str) -> str:
        return f"精彩回答: {user_input} - 这是一个更详细的回复"
    
    suite = BenchmarkSuite()
    
    def benchmark_1(evaluator, agent_fn):
        return evaluator.evaluate(
            agent_fn=agent_fn,
            metrics=["exact_match"],
            benchmark_name="quick_test",
        )
    
    suite.add_benchmark("quick_test", benchmark_1)
    
    evaluator_simple = AgentEvaluator(model_name="simple_agent")
    evaluator_fancy = AgentEvaluator(model_name="fancy_agent")
    
    results_simple = suite.run_all(evaluator_simple, simple_agent)
    results_fancy = suite.run_all(evaluator_fancy, fancy_agent)
    
    all_results = results_simple + results_fancy
    comparison = suite.compare_models(all_results)
    
    print(f"\n模型对比:")
    for metric_name, model_scores in comparison.items():
        print(f"\n  {metric_name}:")
        for model_name, score in model_scores.items():
            print(f"    {model_name}: {score:.4f}")


def main():
    print("训练集成与评估模块使用示例")
    print("=" * 60)
    
    dataset_dict = example_dataset_loading()
    
    if dataset_dict:
        example_training_preparation()
        
        example_evaluation()
        
        example_benchmark_suite()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
