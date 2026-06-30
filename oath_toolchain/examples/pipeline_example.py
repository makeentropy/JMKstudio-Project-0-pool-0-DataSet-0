#!/usr/bin/env python3
"""乾坤管道示例。

展示乾坤管道的使用，包括预置管道、自定义管道和工作流定义与执行。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK


def main():
    print("=" * 60)
    print("乾坤管道示例")
    print("=" * 60)

    # 初始化 SDK
    sdk = OathSDK()

    # 1. 列出预置管道
    print("\n[1/4] 列出预置管道...")

    pipelines = sdk.pipelines.list_pipelines()
    print(f"已注册管道数量: {len(pipelines)}")
    for pipe in pipelines:
        print(f"  - {pipe['name']}: {pipe['step_count']} 个步骤")
        if pipe.get('steps'):
            print(f"    步骤: {', '.join(pipe['steps'][:3])}...")

    # 2. 自定义管道
    print("\n[2/4] 创建自定义管道...")

    # 生成测试用密钥
    aes_key = sdk.keys.generate_aes_key(256)
    space_key = sdk.keys.generate_karmaca_key(dimensions=3)

    # 创建一个多层加密管道
    custom_pipeline = sdk.pipelines.create_pipeline(
        name="custom_encrypt_pipeline",
        steps=[
            {
                "name": "aes_encrypt",
                "tool": "crypto",
                "action": "encrypt_aes",
                "params": {"key": aes_key.hex()},
            },
            {
                "name": "hash_data",
                "tool": "crypto",
                "action": "hash",
                "params": {"algorithm": "sha256"},
            },
        ],
    )
    print(f"自定义管道创建: {'✓ 成功' if custom_pipeline else '✗ 失败'}")
    print(f"管道名称: {custom_pipeline.get('name', 'N/A')}")
    print(f"步骤数量: {custom_pipeline.get('step_count', 0)}")
    print(f"步骤: {custom_pipeline.get('steps', [])}")

    # 再次列出管道
    pipelines = sdk.pipelines.list_pipelines()
    print(f"\n创建后管道总数: {len(pipelines)}")

    # 3. 完整加密管道演示
    print("\n[3/4] 完整加密管道演示...")

    test_data = "这是需要通过管道处理的数据".encode('utf-8')
    print(f"输入数据: {test_data.decode('utf-8')}")
    print(f"数据长度: {len(test_data)} 字节")

    # 使用 crypto_api 的完整加密功能
    encrypt_config = {
        "aes_key": aes_key,
        "space_key": space_key,
        "karmaca_dimensions": 3,
        "use_geometric_proof": True,
    }

    print("\n执行多层加密...")
    encrypted_result = sdk.crypto.encrypt_full(test_data, encrypt_config)
    print(f"加密层数: {len(encrypted_result.get('layers', []))}")
    for layer in encrypted_result.get('layers', []):
        print(f"  - {layer.get('type', 'unknown')}")
    print(f"最终数据长度: {len(encrypted_result.get('final_data', b''))} 字节")

    # 解密
    print("\n执行多层解密...")
    decrypt_config = {
        "aes_key": aes_key,
        "space_key": space_key,
        "karmaca_dimensions": 3,
        "use_geometric_proof": True,
    }
    decrypted = sdk.crypto.decrypt_full(encrypted_result, decrypt_config)
    print(f"解密结果: {decrypted.decode('utf-8')}")
    print(f"解密验证: {'✓ 成功' if decrypted == test_data else '✗ 失败'}")

    # 4. 安全配置文件
    print("\n[4/4] 安全配置文件...")

    # 注册安全配置文件
    sdk.pipelines.register_profile(
        profile_name="high_security",
        config={
            "aes_key": aes_key,
            "space_key": space_key,
            "karmaca_dimensions": 4,
            "use_geometric_proof": True,
        },
    )

    sdk.pipelines.register_profile(
        profile_name="fast_encrypt",
        config={
            "aes_key": aes_key,
        },
    )

    print("已注册的安全配置文件:")
    print("  - high_security: 高安全级配置 (AES + KARMACA + 几何证明)")
    print("  - fast_encrypt: 快速加密配置 (仅 AES)")

    # 使用配置文件加密
    data_to_encrypt = "使用安全配置文件加密的数据".encode('utf-8')
    print(f"\n使用 high_security 配置加密...")
    try:
        result = sdk.pipelines.encrypt_with_profile("high_security", data_to_encrypt)
        print(f"  加密层数: {len(result.get('layers', []))}")
        print(f"  加密成功: ✓")
    except Exception as e:
        print(f"  加密失败: {e}")

    print(f"\n使用 fast_encrypt 配置加密...")
    try:
        result = sdk.pipelines.encrypt_with_profile("fast_encrypt", data_to_encrypt)
        print(f"  加密层数: {len(result.get('layers', []))}")
        print(f"  加密成功: ✓")
    except Exception as e:
        print(f"  加密失败: {e}")

    print("\n" + "=" * 60)
    print("乾坤管道示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
