#!/usr/bin/env python3
"""
示例：使用 DataCollectorSDK 收集 Agent 交互数据
"""

from src.collector import DataCollectorSDK, ToolCall


def main():
    print("=== DataCollectorSDK 示例 ===\n")

    # 初始化 SDK
    sdk = DataCollectorSDK()
    print("1. SDK 初始化完成")

    # 示例 1：直接保存单个交互
    print("\n2. 保存单个交互...")
    interaction = sdk.save_now(
        user_input="你好，请帮我写一个 Python 函数",
        agent_response="好的，我来帮你写一个简单的 Python 函数。",
        metadata={"source": "test", "version": "1.0"}
    )
    print(f"   已保存交互: {interaction.id}")

    # 示例 2：收集多个交互后批量保存
    print("\n3. 收集多个交互...")
    sdk.collect_interaction(
        user_input="计算 2 + 2 等于多少？",
        agent_response="2 + 2 = 4"
    )

    # 带有工具调用的交互
    interaction_with_tools = sdk.collect_interaction(
        user_input="查询北京今天的天气",
        agent_response="让我查一下北京今天的天气。"
    )
    sdk.add_tool_call(
        interaction_with_tools,
        name="get_weather",
        arguments={"city": "北京", "date": "today"},
        result={"temperature": "25°C", "condition": "晴"}
    )

    sdk.collect_interaction(
        user_input="谢谢！",
        agent_response="不客气，很高兴能帮助到你！"
    )

    # 批量保存
    print("   批量保存到文件...")
    sdk.flush(filename="batch_example.jsonl")
    print("   批量保存完成")

    # 示例 3：使用 with 语句
    print("\n4. 使用 with 语句...")
    with DataCollectorSDK() as s:
        s.collect_interaction(
            user_input="Hello world!",
            agent_response="你好世界！",
            metadata={"language": "en"}
        )
    print("   退出 with 语句时自动保存")

    # 示例 4：加载已保存的交互
    print("\n5. 加载已保存的交互...")
    saved = sdk.get_saved_interactions()
    print(f"   共加载到 {len(saved)} 个交互")
    for i, inter in enumerate(saved[:3]):
        print(f"   {i+1}. {inter.user_input[:30]}...")


if __name__ == "__main__":
    main()
