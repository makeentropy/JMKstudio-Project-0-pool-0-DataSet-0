#!/usr/bin/env python3
"""KARMACA 空间字典示例。

展示 KARMACA 空间加密、空间字典创建和维度空间映射的使用方法。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK


def main():
    print("=" * 60)
    print("KARMACA 空间字典示例")
    print("=" * 60)

    # 初始化 SDK
    sdk = OathSDK()

    # 1. 生成 KARMACA 空间密钥
    print("\n[1/4] 生成 KARMACA 空间密钥...")
    space_key = sdk.keys.generate_karmaca_key(dimensions=3)
    print(f"空间密钥: {space_key.hex()[:32]}...")
    print(f"密钥长度: {len(space_key)} 字节")

    # 2. 空间加密解密
    print("\n[2/4] 空间加密解密演示...")

    plaintext = "KARMACA 空间加密测试数据".encode('utf-8')
    print(f"原始数据: {plaintext.decode('utf-8')}")

    # 使用 3 维空间加密
    encrypted_3d = sdk.crypto.encrypt_karmaca(
        plaintext, space_key, dimensions=3
    )
    print(f"3维加密后长度: {len(encrypted_3d)} 字节")
    print(f"3维加密数据 (前32字节): {encrypted_3d[:32].hex()}...")

    # 解密
    decrypted_3d = sdk.crypto.decrypt_karmaca(
        encrypted_3d, space_key, dimensions=3
    )
    print(f"3维解密结果: {decrypted_3d.decode('utf-8')}")
    print(f"3维解密验证: {'✓ 成功' if decrypted_3d == plaintext else '✗ 失败'}")

    # 3. 不同维度空间加密
    print("\n[3/4] 不同维度空间加密对比...")

    dimensions_list = [2, 3, 4, 5]
    for dim in dimensions_list:
        try:
            space_key_dim = sdk.keys.generate_karmaca_key(dimensions=dim)
            encrypted = sdk.crypto.encrypt_karmaca(
                plaintext, space_key_dim, dimensions=dim
            )
            decrypted = sdk.crypto.decrypt_karmaca(
                encrypted, space_key_dim, dimensions=dim
            )
            status = "✓" if decrypted == plaintext else "✗"
            print(f"  {dim}维空间: 加密后 {len(encrypted)} 字节 {status}")
        except Exception as e:
            print(f"  {dim}维空间: 失败 - {e}")

    # 4. 错误密钥解密测试
    print("\n[4/4] 错误密钥解密测试...")

    wrong_key = sdk.keys.generate_karmaca_key(dimensions=3)
    try:
        sdk.crypto.decrypt_karmaca(encrypted_3d, wrong_key, dimensions=3)
        print("  错误密钥解密: 意外成功 (不安全!)")
    except Exception as e:
        print(f"  错误密钥解密: ✓ 正常失败 - {type(e).__name__}")

    print("\n" + "=" * 60)
    print("KARMACA 空间字典示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
