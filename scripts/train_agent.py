#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.processor import DataFormatter
from src.trainer import AgentTrainer, ModelManager


def main():
    print("=== Agent 训练工具 ===\n")
    
    formatter = DataFormatter()
    trainer = AgentTrainer()
    
    processed_path = 'data/processed/processed_dataset.json'
    
    if os.path.exists(processed_path):
        print(f"加载处理后的数据: {processed_path}")
        
        with open(processed_path, 'r', encoding='utf-8') as f:
            import json
            dataset = json.load(f)
        
        model_config = {
            'model_type': 'agent_job',
            'epochs': 10,
            'learning_rate': 0.001,
            'batch_size': 32
        }
        
        model_name = 'agent_job_model_v1'
        
        print(f"\n开始训练模型: {model_name}")
        result = trainer.train(dataset, model_config, model_name)
        
        print(f"\n训练结果:")
        print(f"  状态: {result.get('status')}")
        print(f"  训练集数量: {result['dataset_info']['train_count']}")
        print(f"  准确率: {result['metrics']['accuracy']}")
        
    else:
        print(f"处理后数据文件不存在: {processed_path}")
        print("请先运行 process_data.py")
    
    print("\n=== 完成！")


if __name__ == '__main__':
    main()
