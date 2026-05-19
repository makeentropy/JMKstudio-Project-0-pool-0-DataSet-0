#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collector import WebScraper, DataSaver
from src.processor import DataCleaner, DataFormatter
from src.trainer import AgentTrainer


def main():
    print("=== 完整数据处理与训练流程 ===\n")
    
    urls = [
        'https://www.doubao.com/thread/a675c7aea46f3'
    ]
    
    print("步骤 1: 数据收集")
    scraper = WebScraper()
    saver = DataSaver()
    
    raw_data = scraper.batch_scrape(urls)
    if raw_data:
        saver.save_batch_json(raw_data, 'pipeline_data.json')
        print(f"  收集到 {len(raw_data)} 条数据")
    else:
        print("  未收集到数据，使用示例数据")
        raw_data = [
            {
                'url': 'https://example.com',
                'title': '基础量子拓扑概念',
                'content': '量子拓扑学是数学和物理学的交叉领域，研究维度空间、量子波函数奇点等概念。',
                'timestamp': '2024-01-01T00:00:00'
            },
            {
                'url': 'https://example.com/finance',
                'title': '金融数据三大分支',
                'content': '金融数据学包括货币数据学、交易数据学、经济数据学三大分支。',
                'timestamp': '2024-01-01T00:00:00'
            }
        ]
    
    print("\n步骤 2: 数据处理")
    cleaner = DataCleaner()
    formatter = DataFormatter()
    
    cleaned = cleaner.clean_batch(raw_data)
    formatted = formatter.format_as_conversation(cleaned)
    dataset = formatter.create_dataset(formatted, name='full_pipeline_dataset')
    
    formatter.save_formatted_data(dataset, 'pipeline_dataset.json')
    print(f"  处理完成，共 {len(formatted)} 条训练数据")
    
    print("\n步骤 3: Agent 训练")
    trainer = AgentTrainer()
    
    model_config = {
        'model_type': 'agent_job',
        'epochs': 10,
        'learning_rate': 0.001
    }
    
    result = trainer.train(dataset, model_config, 'pipeline_model')
    
    print("\n=== 流程完成 ===")
    print(f"模型训练状态: {result['status']}")


if __name__ == '__main__':
    main()
