#!/usr/bin/env python3
"""
示例：使用 HTTP 客户端与 FastAPI 交互
"""

import requests
import json
from src.collector import AgentInteraction, ToolCall


BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查端点"""
    print("1. 测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")


def test_upload_single():
    """测试上传单个交互"""
    print("\n2. 测试上传单个交互...")
    interaction = AgentInteraction(
        user_input="你好，API 测试",
        agent_response="你好，测试成功！",
        tool_calls=[
            ToolCall(name="test_tool", arguments={"param": "value"}, result="ok")
        ],
        metadata={"test": "true"}
    )
    response = requests.post(
        f"{BASE_URL}/api/v1/interaction",
        json=json.loads(interaction.model_dump_json())
    )
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")


def test_upload_batch():
    """测试批量上传"""
    print("\n3. 测试批量上传...")
    interactions = [
        AgentInteraction(user_input=f"问题 {i}", agent_response=f"回答 {i}")
        for i in range(1, 4)
    ]
    request_data = {
        "interactions": [json.loads(i.model_dump_json()) for i in interactions],
        "source": "batch_test",
        "tags": ["test", "batch"]
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/interactions",
        json=request_data
    )
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")


def test_get_interactions():
    """测试获取交互"""
    print("\n4. 测试获取交互...")
    response = requests.get(f"{BASE_URL}/api/v1/interactions", params={"limit": 5})
    print(f"   状态码: {response.status_code}")
    print(f"   收到 {len(response.json())} 个交互")


def test_get_stats():
    """测试获取统计"""
    print("\n5. 测试获取统计...")
    response = requests.get(f"{BASE_URL}/api/v1/stats")
    print(f"   状态码: {response.status_code}")
    print(f"   统计: {response.json()}")


def main():
    print("=== FastAPI 客户端示例 ===\n")
    print("注意：请先运行 API 服务器: python -m src.collector.api\n")

    try:
        test_health()
        test_upload_single()
        test_upload_batch()
        test_get_interactions()
        test_get_stats()
        print("\n✅ 所有测试完成！")
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误：无法连接到 API 服务器")
        print("请确保服务器正在运行: python -m src.collector.api")


if __name__ == "__main__":
    main()
