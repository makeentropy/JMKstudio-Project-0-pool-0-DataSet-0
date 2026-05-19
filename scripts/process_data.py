#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collector import DataSaver
from src.processor import DataCleaner, DataFormatter


def main():
    print("=== 数据处理工具 ===\n")
    
    saver = DataSaver()
    cleaner = DataCleaner()
    formatter = DataFormatter()
    
    raw_data_path = 'data/raw/doubao_data.json'
    
    if os.path.exists(raw_data_path):
        print(f"加载原始数据: {raw_data_path}")
        raw_data = saver.load_json(raw_data_path)
        
        if isinstance(raw_data, dict):
            raw_data = [raw_data]
        
        print(f"原始数据条数: {len(raw_data)}")
        
        cleaned_data = cleaner.clean_batch(raw_data)
        print(f"清洗后数据条数: {len(cleaned_data)}")
        
        unique_data = cleaner.remove_duplicates(cleaned_data)
        print(f"去重后数据条数: {len(unique_data)}")
        
        formatted_data = formatter.format_as_conversation(unique_data)
        print(f"格式化数据条数: {len(formatted_data)}")
        
        dataset = formatter.create_dataset(
            train_data=formatted_data,
            name='doubao_dataset'
        )
        
        output_path = formatter.save_formatted_data(dataset, 'processed_dataset.json')
        print(f"\n处理后数据已保存到: {output_path}")
        
    else:
        print(f"原始数据文件不存在: {raw_data_path}")
        print("请先运行 collect_data.py")
    
    print("\n=== 完成！")


if __name__ == '__main__':
    main()
