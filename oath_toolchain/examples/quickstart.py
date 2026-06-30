#!/usr/bin/env python3
"""快速入门示例。

展示神誓工具链SDK的基本使用方法，包括初始化、密钥生成、
AES加解密和签名验证。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK


def main():
    print("=" * 60)
    print("神誓工具链 - 快速入门示例")
    print("=" * 60)

    # 1. 初始化SDK
    print("\n[1/4] 初始化 SDK...")
    sdk = OathSDK()
    print(f"SDK 版本: {sdk.version()}")
    print("SDK 初始化成功")

    # 2. 生成密钥
    print("\n[2/4] 生成密钥...")

    # 生成 AES 密钥
    aes_key = sdk.keys.generate_aes_key(256)
    print(f"AES 密钥 (256位): {aes_key.hex()[:32]}...")
    print(f"密钥长度: {len(aes_key)} 字节 ({len(aes_key) * 8} 位)")

    # 生成 RSA 密钥对
    print("\n生成 RSA 密钥对 (2048位)...")
    rsa_private_key, rsa_public_key = sdk.keys.generate_rsa_key(2048)
    print(f"私钥长度: {len(rsa_private_key)} 字节")
    print(f"公钥长度: {len(rsa_public_key)} 字节")

    # 3. AES 加解密
    print("\n[3/4] AES 加解密演示...")

    plaintext = "Hello, Oath Toolchain! 欢迎使用神誓工具链！".encode('utf-8')
    print(f"原始数据: {plaintext.decode('utf-8')}")

    # 加密
    encrypted = sdk.crypto.encrypt_aes(plaintext, aes_key)
    print(f"加密后 (前32字节): {encrypted[:32].hex()}...")
    print(f"加密数据长度: {len(encrypted)} 字节")

    # 解密
    decrypted = sdk.crypto.decrypt_aes(encrypted, aes_key)
    print(f"解密后: {decrypted.decode('utf-8')}")
    print(f"解密验证: {'✓ 成功' if decrypted == plaintext else '✗ 失败'}")

    # 4. 签名验证
    print("\n[4/4] 签名验证演示...")

    data_to_sign = "这是需要签名的重要数据".encode('utf-8')
    print(f"待签名数据: {data_to_sign.decode('utf-8')}")

    # 签名
    signature = sdk.crypto.sign(data_to_sign, rsa_private_key, method='rsa')
    print(f"签名生成成功，签名长度: {len(signature)} 字节")

    # 验证
    is_valid = sdk.crypto.verify(
        data_to_sign, signature, rsa_public_key, method='rsa'
    )
    print(f"签名验证: {'✓ 有效' if is_valid else '✗ 无效'}")

    # 验证被篡改的数据
    tampered_data = "这是被篡改的数据".encode('utf-8')
    is_valid_tampered = sdk.crypto.verify(
        tampered_data, signature, rsa_public_key, method='rsa'
    )
    print(f"篡改数据验证: {'✓ 有效 (异常!)' if is_valid_tampered else '✗ 无效 (正常)'}")

    print("\n" + "=" * 60)
    print("快速入门示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
