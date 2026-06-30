#!/usr/bin/env python3
"""
示例：使用 FileCollector 和 StorageManager
"""

import json
from pathlib import Path
from src.collector import FileCollector, StorageManager, AgentInteraction


def create_sample_json_file():
    """创建一个示例 JSON 文件"""
    sample_data = {
        "interactions": [
            {
                "user_input": "什么是机器学习？",
                "agent_response": "机器学习是人工智能的一个分支...",
                "metadata": {"category": "AI"}
            },
            {
                "user_input": "Python 和 Java 有什么区别？",
                "agent_response": "Python 是解释型语言，Java 是编译型语言...",
                "tool_calls": [
                    {
                        "name": "search_info",
                        "arguments": {"query": "Python vs Java"},
                        "result": "Comparison data"
                    }
                ],
                "metadata": {"category": "programming"}
            }
        ]
    }
    
    file_path = Path.cwd() / "examples" / "sample_data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    return file_path


def create_sample_csv_file():
    """创建一个示例 CSV 文件"""
    csv_content = """user_input,agent_response,source,category
推荐一本好书,《人类简史》是一本很好的书,manual,recommendation
如何学习编程,从 Python 开始学习吧,manual,tutorial
"""
    file_path = Path.cwd() / "examples" / "sample_data.csv"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(csv_content)
    return file_path


def main():
    print("=== FileCollector 和 StorageManager 示例 ===\n")

    # 创建示例数据文件
    print("1. 创建示例数据文件...")
    json_file = create_sample_json_file()
    csv_file = create_sample_csv_file()
    print(f"   JSON 文件: {json_file}")
    print(f"   CSV 文件: {csv_file}")

    # 使用 FileCollector 收集 JSON 数据
    print("\n2. 使用 FileCollector 收集 JSON 数据...")
    json_collector = FileCollector(str(json_file), format_type="json")
    json_interactions = json_collector.collect()
    print(f"   收集到 {len(json_interactions)} 个交互")
    for inter in json_interactions:
        print(f"   - {inter.user_input}")

    # 使用 FileCollector 收集 CSV 数据
    print("\n3. 使用 FileCollector 收集 CSV 数据...")
    csv_collector = FileCollector(str(csv_file), format_type="csv")
    csv_interactions = csv_collector.collect()
    print(f"   收集到 {len(csv_interactions)} 个交互")
    for inter in csv_interactions:
        print(f"   - {inter.user_input}")

    # 使用 StorageManager 保存数据
    print("\n4. 使用 StorageManager 保存数据...")
    storage = StorageManager()
    all_interactions = json_interactions + csv_interactions
    saved_path = storage.save(all_interactions, filename="collected_data.jsonl")
    print(f"   已保存到: {saved_path}")

    # 加载已保存的数据
    print("\n5. 加载已保存的数据...")
    loaded = storage.load_all()
    print(f"   加载到 {len(loaded)} 个交互")

    # 清理示例文件
    print("\n6. 清理示例文件...")
    json_file.unlink()
    csv_file.unlink()
    print("   清理完成")


if __name__ == "__main__":
    main()
