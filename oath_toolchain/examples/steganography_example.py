#!/usr/bin/env python3
"""隐写术示例。

展示多种隐写技术的使用，包括XOR隐写、文本隐写（Unicode零宽字符）、
证书隐写以及安全性分析。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK


def main():
    print("=" * 60)
    print("隐写术示例")
    print("=" * 60)

    # 初始化 SDK
    sdk = OathSDK()

    # 1. XOR 隐写
    print("\n[1/4] XOR 隐写...")

    secret_data = "这是隐藏的秘密消息".encode('utf-8')
    carrier_data = os.urandom(512)  # 随机载体数据

    print(f"秘密数据: {secret_data.decode('utf-8')}")
    print(f"秘密数据长度: {len(secret_data)} 字节")
    print(f"载体数据长度: {len(carrier_data)} 字节")

    # 嵌入数据
    stego_data = sdk.stego.embed_xor(secret_data, carrier_data)
    print(f"隐写后数据长度: {len(stego_data)} 字节")

    # 提取数据
    extracted = sdk.stego.extract_xor(stego_data)
    print(f"提取的数据: {extracted.decode('utf-8')}")
    print(f"提取验证: {'✓ 成功' if extracted == secret_data else '✗ 失败'}")

    # 使用密钥的 XOR 隐写
    print("\n使用加密密钥的XOR隐写:")
    key = sdk.keys.generate_aes_key(128)
    stego_data_encrypted = sdk.stego.embed_xor(secret_data, carrier_data, key)
    extracted_encrypted = sdk.stego.extract_xor(stego_data_encrypted, key=key)
    print(f"带密钥提取验证: {'✓ 成功' if extracted_encrypted == secret_data else '✗ 失败'}")

    # 2. 文本隐写 (Unicode 零宽字符)
    print("\n[2/4] 文本隐写 (Unicode 零宽字符)...")

    cover_text = "这是一段看起来很普通的文本，里面藏着秘密。"
    secret_text = "隐藏在文本中的秘密消息".encode('utf-8')

    print(f"载体文本: {cover_text}")
    print(f"秘密消息: {secret_text.decode('utf-8')}")

    # 使用 Unicode 零宽字符嵌入
    stego_text = sdk.stego.embed_text_unicode(secret_text, cover_text)
    print(f"隐写后文本长度: {len(stego_text)} 字符")
    print(f"隐写后文本 (前30字符): {stego_text[:30]}...")

    # 提取
    extracted_text = sdk.stego.extract_text_unicode(stego_text)
    print(f"提取的秘密: {extracted_text.decode('utf-8')}")
    print(f"提取验证: {'✓ 成功' if extracted_text == secret_text else '✗ 失败'}")

    # 使用空格隐写
    print("\n使用空格编码隐写:")
    cover_text_whitespace = "Hello World This is a test message for steganography"
    stego_whitespace = sdk.stego.embed_text_whitespace(secret_text, cover_text_whitespace)
    extracted_whitespace = sdk.stego.extract_text_whitespace(stego_whitespace)
    print(f"空格隐写提取验证: {'✓ 成功' if extracted_whitespace == secret_text else '✗ 失败'}")

    # 3. 证书隐写
    print("\n[3/4] 证书隐写...")

    # 先创建一个证书
    cert_result = sdk.ca.issue_certificate(
        subject="stego.oathtoolchain.dev",
        cert_type="end_entity",
        issuer="root",
    )

    if cert_result.get('success'):
        cert_pem = cert_result.get('certificate')
        if isinstance(cert_pem, str):
            cert_bytes = cert_pem.encode('utf-8')
        else:
            cert_bytes = cert_pem

        secret_in_cert = "隐藏在证书中的秘密数据".encode('utf-8')
        print(f"原始证书长度: {len(cert_bytes)} 字节")
        print(f"秘密数据: {secret_in_cert.decode('utf-8')}")

        # 嵌入到证书
        stego_cert = sdk.stego.embed_in_cert(secret_in_cert, cert_bytes)
        print(f"隐写后证书长度: {len(stego_cert)} 字节")

        # 提取
        extracted_cert_secret = sdk.stego.extract_from_cert(stego_cert)
        print(f"提取的秘密: {extracted_cert_secret.decode('utf-8')}")
        print(f"提取验证: {'✓ 成功' if extracted_cert_secret == secret_in_cert else '✗ 失败'}")

    # 4. 安全性分析
    print("\n[4/4] 隐写安全性分析...")

    # 分析载体容量
    capacity_result = sdk.stego.analyze_carrier(carrier_data, "binary")
    print(f"载体容量分析:")
    if isinstance(capacity_result, dict):
        for key, value in list(capacity_result.items())[:5]:
            print(f"  {key}: {value}")

    # 评估隐写安全性
    security_result = sdk.stego.estimate_security(carrier_data, stego_data)
    print(f"\n隐写安全性评估:")
    if isinstance(security_result, dict):
        for key, value in list(security_result.items())[:5]:
            print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("隐写术示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
