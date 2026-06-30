#!/usr/bin/env python3
"""数据集池示例。

展示数据集的创建、Karma标签添加、版本控制和搜索检索功能。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK


def main():
    print("=" * 60)
    print("数据集池示例")
    print("=" * 60)

    # 初始化 SDK
    sdk = OathSDK()

    # 1. 创建数据集
    print("\n[1/4] 创建数据集...")

    # 创建第一个数据集
    dataset1_data = [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
        {"id": 3, "name": "Charlie", "role": "user"},
    ]

    result1 = sdk.datasets.create(
        name="用户数据集",
        data=dataset1_data,
        format="json",
    )
    print(f"数据集1创建: {'✓ 成功' if result1.get('success') else '✗ 失败'}")
    dataset1_id = result1.get('dataset_id', '')
    print(f"  ID: {dataset1_id}")
    print(f"  名称: {result1.get('dataset', {}).get('name', 'N/A') if isinstance(result1.get('dataset'), dict) else 'N/A'}")

    # 创建第二个数据集
    dataset2_data = {
        "title": "项目文档",
        "content": "这是一个示例数据集的内容",
        "tags": ["文档", "示例"],
    }

    result2 = sdk.datasets.create(
        name="文档数据集",
        data=dataset2_data,
        format="json",
    )
    print(f"数据集2创建: {'✓ 成功' if result2.get('success') else '✗ 失败'}")
    dataset2_id = result2.get('dataset_id', '')
    print(f"  ID: {dataset2_id}")

    # 列出所有数据集
    all_datasets = sdk.datasets.list_datasets()
    print(f"\n数据集总数: {len(all_datasets)}")
    for ds in all_datasets:
        print(f"  - {ds.get('name', 'N/A')} ({ds.get('dataset_id', 'N/A')})")

    # 2. 添加 Karma 标签
    print("\n[2/4] 添加 Karma 标签...")

    # 为数据集1添加标签
    tags_dataset1 = [
        {"tag_id": "tag_type", "name": "类型", "value": "用户数据", "weight": 0.8},
        {"tag_id": "tag_sensitivity", "name": "敏感度", "value": "中等", "weight": 0.6},
        {"tag_id": "tag_department", "name": "部门", "value": "研发部", "weight": 0.9},
    ]

    for tag in tags_dataset1:
        result = sdk.datasets.add_tag(dataset1_id, tag)
        print(f"添加标签 '{tag['name']}': {'✓ 成功' if result else '✗ 失败'}")

    # 为数据集2添加标签
    tags_dataset2 = [
        {"tag_id": "tag_type", "name": "类型", "value": "文档", "weight": 0.7},
        {"tag_id": "tag_sensitivity", "name": "敏感度", "value": "低", "weight": 0.3},
    ]

    for tag in tags_dataset2:
        result = sdk.datasets.add_tag(dataset2_id, tag)
        print(f"添加标签 '{tag['name']}': {'✓ 成功' if result else '✗ 失败'}")

    # 获取数据集信息
    ds1_info = sdk.datasets.get(dataset1_id)
    print(f"\n数据集1信息:")
    if isinstance(ds1_info, dict):
        for key, value in list(ds1_info.items())[:5]:
            print(f"  {key}: {value}")

    # 3. 版本控制
    print("\n[3/4] 版本控制...")

    # 提交第一个版本
    version1 = sdk.datasets.commit_version(
        dataset1_id,
        message="初始版本 - 用户数据集",
    )
    print(f"提交版本 v1: {version1}")

    # 修改数据
    updated_data = [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
        {"id": 3, "name": "Charlie", "role": "user"},
        {"id": 4, "name": "David", "role": "moderator"},
    ]
    sdk.datasets.update(dataset1_id, data=updated_data)
    print("更新数据: 添加了新用户 David")

    # 提交第二个版本
    version2 = sdk.datasets.commit_version(
        dataset1_id,
        message="添加新用户 David",
    )
    print(f"提交版本 v2: {version2}")

    # 列出所有版本
    versions = sdk.datasets.list_versions(dataset1_id)
    print(f"\n版本历史 ({len(versions)} 个版本):")
    for ver in versions:
        print(f"  - {ver.get('version', 'N/A')}: {ver.get('message', 'N/A')}")

    # 回滚到旧版本
    print(f"\n回滚到版本 v1...")
    reverted = sdk.datasets.revert_version(dataset1_id, version1)
    print(f"回滚结果: {'✓ 成功' if reverted.get('success') else '✗ 失败'}")

    # 4. 搜索与检索
    print("\n[4/4] 搜索与检索...")

    # 按标签搜索
    print("按标签搜索数据集:")

    # 搜索类型=用户数据的数据集
    search_result1 = sdk.datasets.search_by_tags({
        "name": "类型",
        "value": "用户数据",
    })
    print(f"  类型=用户数据: {len(search_result1)} 个结果")
    for ds in search_result1:
        print(f"    - {ds.get('name', 'N/A')}")

    # 搜索敏感度=低的数据集
    search_result2 = sdk.datasets.search_by_tags({
        "name": "敏感度",
        "value": "低",
    })
    print(f"  敏感度=低: {len(search_result2)} 个结果")
    for ds in search_result2:
        print(f"    - {ds.get('name', 'N/A')}")

    # 使用过滤器列出
    print("\n使用过滤器列出数据集:")
    filtered = sdk.datasets.list_datasets(filters={"format": "json"})
    print(f"  JSON 格式数据集: {len(filtered)} 个")

    # 更新元数据
    print("\n更新数据集元数据:")
    update_result = sdk.datasets.update(
        dataset1_id,
        metadata={
            "author": "Oath Toolchain Team",
            "created_at": "2024-01-01",
            "description": "用户信息数据集",
        },
    )
    print(f"  元数据更新: {'✓ 成功' if update_result.get('success') else '✗ 失败'}")

    print("\n" + "=" * 60)
    print("数据集池示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
