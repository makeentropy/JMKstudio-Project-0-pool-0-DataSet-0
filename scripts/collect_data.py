#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collector import WebScraper, DataSaver


def main():
    print("=== 数据收集工具 ===\n")
    
    urls = [
        'https://www.doubao.com/thread/a675c7aea46f3'
    ]
    
    scraper = WebScraper()
    saver = DataSaver()
    
    print(f"开始收集数据，共 {len(urls)} 个URL...")
    
    results = scraper.batch_scrape(urls)
    
    if results:
        print(f"\n成功收集 {len(results)} 条数据")
        
        filepath = saver.save_batch_json(results, 'doubao_data.json')
        print(f"数据已保存到: {filepath}")
        
        for i, data in enumerate(results, 1):
            print(f"\n--- 数据 {i}:")
            print(f"  标题: {data.get('title', '')}")
            print(f"  URL: {data.get('url', '')}")
            print(f"  内容长度: {len(data.get('content', ''))} 字符")
    else:
        print("\n未收集到数据")
    
    print("\n=== 完成！")


if __name__ == '__main__':
    main()
