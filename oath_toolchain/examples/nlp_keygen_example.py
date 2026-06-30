#!/usr/bin/env python3
"""NLP 密钥生成示例。

展示从自然语言文本生成密钥的三种模式：语义模式、熵值模式和混合模式，
以及密钥强度评估功能。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK


def main():
    print("=" * 60)
    print("NLP 密钥生成示例")
    print("=" * 60)

    # 初始化 SDK
    sdk = OathSDK()

    # 测试文本
    test_texts = [
        "The quick brown fox jumps over the lazy dog",
        "床前明月光，疑是地上霜。举头望明月，低头思故乡。",
        "密码学是研究编制密码和破译密码的技术科学",
        "Hello World 12345 !@#$%",
    ]

    # 1. 语义模式密钥生成
    print("\n[1/4] 语义模式密钥生成...")
    print("基于文本的语义特征生成密钥")

    for i, text in enumerate(test_texts, 1):
        key = sdk.keys.generate_nlp_key(
            text=text,
            mode='semantic',
            key_length=32,
        )
        print(f"\n  文本 {i}: {text[:40]}..." if len(text) > 40 else f"\n  文本 {i}: {text}")
        print(f"  密钥 (hex): {key.hex()}")
        print(f"  密钥长度: {len(key)} 字节")

    # 2. 熵值模式密钥生成
    print("\n[2/4] 熵值模式密钥生成...")
    print("基于文本的熵值特征生成密钥")

    for i, text in enumerate(test_texts, 1):
        key = sdk.keys.generate_nlp_key(
            text=text,
            mode='entropy',
            key_length=32,
        )
        print(f"\n  文本 {i}: {text[:40]}..." if len(text) > 40 else f"\n  文本 {i}: {text}")
        print(f"  密钥 (hex): {key.hex()}")
        print(f"  密钥长度: {len(key)} 字节")

    # 3. 混合模式密钥生成
    print("\n[3/4] 混合模式密钥生成...")
    print("结合语义和熵值特征生成密钥")

    for i, text in enumerate(test_texts, 1):
        key = sdk.keys.generate_nlp_key(
            text=text,
            mode='hybrid',
            key_length=32,
        )
        print(f"\n  文本 {i}: {text[:40]}..." if len(text) > 40 else f"\n  文本 {i}: {text}")
        print(f"  密钥 (hex): {key.hex()}")
        print(f"  密钥长度: {len(key)} 字节")

    # 4. 密钥强度评估
    print("\n[4/4] 密钥强度评估...")

    # 测试不同强度的密钥
    test_keys = [
        ("弱密钥 (简单重复)", b"\x00" * 16),
        ("中等密钥 (随机)", sdk.keys.generate_aes_key(128)),
        ("强密钥 (随机)", sdk.keys.generate_aes_key(256)),
        ("NLP生成密钥", sdk.keys.generate_nlp_key(
            "复杂的自然语言文本用于生成密钥", mode='hybrid', key_length=32
        )),
    ]

    for name, key in test_keys:
        result = sdk.keys.assess_key_strength(key)
        print(f"\n  {name}:")
        print(f"    长度: {result['length']} 字节 ({result['length'] * 8} 位)")
        print(f"    分数: {result['score']}/100")
        print(f"    强度等级: {result['strength']}")
        print(f"    熵值: {result['entropy']:.2f} 位")

    print("\n" + "=" * 60)
    print("NLP 密钥生成示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
