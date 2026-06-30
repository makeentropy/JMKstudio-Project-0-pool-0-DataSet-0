#!/usr/bin/env python3
"""奇点验证示例。

展示奇点验证器的使用，包括密钥奇点验证、数据奇点验证和质量评估。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK
from oath_toolchain.tools.singularity.verifier import SingularityVerifier


def main():
    print("=" * 60)
    print("奇点验证示例")
    print("=" * 60)

    # 初始化奇点验证器
    verifier = SingularityVerifier()

    # 1. 密钥奇点验证
    print("\n[1/3] 密钥奇点验证...")

    # 生成不同类型的密钥进行测试
    sdk = OathSDK()

    test_keys = [
        ("弱密钥 (全零)", b"\x00" * 32),
        ("弱密钥 (重复模式)", b"\x01\x02\x03\x04" * 8),
        ("随机密钥 (128位)", sdk.keys.generate_aes_key(128)),
        ("随机密钥 (256位)", sdk.keys.generate_aes_key(256)),
        ("NLP生成密钥", sdk.keys.generate_nlp_key(
            "这是一段用于生成密钥的自然语言文本", mode='hybrid', key_length=32
        )),
    ]

    for name, key in test_keys:
        result = verifier.execute({
            'action': 'verify',
            'key': key,
            'mode': 'fast',
            'sensitivity': 0.8,
        })
        print(f"\n  {name}:")
        print(f"    密钥长度: {len(key)} 字节")
        print(f"    验证结果: {'✓ 通过' if result.get('valid') else '✗ 未通过'}")
        print(f"    评分: {result.get('score', 'N/A')}")
        if result.get('report') and isinstance(result['report'], dict):
            report = result['report']
            for k, v in list(report.items())[:3]:
                print(f"    {k}: {v}")

    # 2. 数据奇点验证
    print("\n[2/3] 数据奇点验证...")

    test_data_list = [
        ("全零数据", b"\x00" * 256),
        ("重复模式数据", b"ABCD" * 64),
        ("随机数据", os.urandom(256)),
        ("文本数据", b"Hello, World! " * 20),
        ("结构化JSON数据", b'{"name": "test", "value": 123, "data": [1,2,3,4,5]}' * 10),
    ]

    for name, data in test_data_list:
        result = verifier.execute({
            'action': 'verify',
            'data': data,
            'mode': 'fast',
            'sensitivity': 0.8,
        })
        print(f"\n  {name}:")
        print(f"    数据长度: {len(data)} 字节")
        print(f"    验证结果: {'✓ 通过' if result.get('valid') else '✗ 未通过'}")
        print(f"    评分: {result.get('score', 'N/A')}")
        if result.get('report') and isinstance(result['report'], dict):
            report = result['report']
            for k, v in list(report.items())[:3]:
                print(f"    {k}: {v}")

    # 3. 质量评估对比
    print("\n[3/3] 质量评估对比...")

    # 使用不同灵敏度进行测试
    sensitivities = [0.5, 0.7, 0.9]
    test_data = os.urandom(128)

    print(f"测试数据: {len(test_data)} 字节随机数据")
    print("\n不同灵敏度下的验证结果:")

    for sens in sensitivities:
        result = verifier.execute({
            'action': 'verify',
            'data': test_data,
            'mode': 'full',
            'sensitivity': sens,
        })
        print(f"  灵敏度 {sens}:")
        print(f"    结果: {'✓ 通过' if result.get('valid') else '✗ 未通过'}")
        print(f"    评分: {result.get('score', 'N/A')}")

    # 特征提取演示
    print("\n密钥特征提取:")
    key = sdk.keys.generate_aes_key(256)
    features_result = verifier.execute({
        'action': 'features',
        'key': key,
    })
    if features_result.get('features') and isinstance(features_result['features'], dict):
        features = features_result['features']
        for k, v in list(features.items())[:5]:
            print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("奇点验证示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
