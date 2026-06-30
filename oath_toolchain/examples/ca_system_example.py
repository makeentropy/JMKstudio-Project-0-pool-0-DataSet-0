#!/usr/bin/env python3
"""CA 证书体系示例。

展示完整的CA证书体系操作，包括创建根CA、中间CA、签发证书、
证书验证和证书吊销。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK


def main():
    print("=" * 60)
    print("CA 证书体系示例")
    print("=" * 60)

    # 初始化 SDK
    sdk = OathSDK()

    # 1. 创建根 CA
    print("\n[1/5] 创建根 CA...")
    root_ca = sdk.ca.init_root_ca(name="神誓根证书颁发机构")
    print(f"根CA名称: {root_ca.get('ca_name', 'N/A')}")
    print(f"创建状态: {'✓ 成功' if root_ca.get('success') else '✗ 失败'}")
    if root_ca.get('certificate'):
        cert_len = len(root_ca['certificate'].encode() if isinstance(root_ca['certificate'], str) else root_ca['certificate'])
        print(f"根证书长度: {cert_len} 字节")

    # 2. 创建中间 CA
    print("\n[2/5] 创建中间 CA...")
    intermediate_ca = sdk.ca.create_intermediate_ca(
        name="神誓中间CA - 业务证书",
        ca_type="intermediate_ca",
    )
    print(f"中间CA名称: {intermediate_ca.get('ca_name', 'N/A')}")
    print(f"CA类型: {intermediate_ca.get('ca_type', 'N/A')}")
    print(f"创建状态: {'✓ 成功' if intermediate_ca.get('success') else '✗ 失败'}")

    # 3. 签发终端实体证书
    print("\n[3/5] 签发终端实体证书...")

    # 签发服务器证书
    server_cert = sdk.ca.issue_certificate(
        subject="www.oathtoolchain.dev",
        cert_type="end_entity",
        issuer="root",
    )
    print(f"\n服务器证书:")
    print(f"  主题: {server_cert.get('subject', 'N/A')}")
    print(f"  证书类型: {server_cert.get('cert_type', 'N/A')}")
    print(f"  签发CA: {server_cert.get('issuer_ca', 'N/A')}")
    print(f"  签发状态: {'✓ 成功' if server_cert.get('success') else '✗ 失败'}")

    # 签发客户端证书
    client_cert = sdk.ca.issue_certificate(
        subject="user@oathtoolchain.dev",
        cert_type="end_entity",
        issuer="root",
    )
    print(f"\n客户端证书:")
    print(f"  主题: {client_cert.get('subject', 'N/A')}")
    print(f"  证书类型: {client_cert.get('cert_type', 'N/A')}")
    print(f"  签发CA: {client_cert.get('issuer_ca', 'N/A')}")
    print(f"  签发状态: {'✓ 成功' if client_cert.get('success') else '✗ 失败'}")

    # 4. 证书验证
    print("\n[4/5] 证书验证...")

    server_cert_pem = server_cert.get('certificate')
    if server_cert_pem:
        if isinstance(server_cert_pem, str):
            server_cert_bytes = server_cert_pem.encode('utf-8')
        else:
            server_cert_bytes = server_cert_pem

        # 验证证书
        verify_result = sdk.ca.verify_certificate(server_cert_bytes)
        print(f"服务器证书验证:")
        print(f"  有效: {'✓ 是' if verify_result.get('valid') else '✗ 否'}")
        print(f"  消息: {verify_result.get('message', 'N/A')}")

        # 获取证书信息
        cert_info = sdk.ca.get_cert_info(server_cert_bytes)
        print(f"\n证书信息:")
        if cert_info:
            for key, value in list(cert_info.items())[:5]:
                print(f"  {key}: {value}")

    # 5. 证书吊销
    print("\n[5/5] 证书吊销...")

    # 列出所有证书
    certs = sdk.ca.list_certificates()
    print(f"当前证书数量: {len(certs)}")

    if certs:
        # 获取第一个证书的序列号并尝试吊销
        first_cert = certs[0]
        serial = first_cert.get('serial_number', '')
        if serial:
            revoked = sdk.ca.revoke_certificate(
                serial_number=str(serial),
                reason="key_compromise",
            )
            print(f"吊销证书 (序列号: {str(serial)[:20]}...): {'✓ 成功' if revoked else '✗ 失败'}")

        # 按状态列出证书
        valid_certs = sdk.ca.list_certificates(status="valid")
        revoked_certs = sdk.ca.list_certificates(status="revoked")
        print(f"有效证书: {len(valid_certs)} 个")
        print(f"已吊销证书: {len(revoked_certs)} 个")

    print("\n" + "=" * 60)
    print("CA 证书体系示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
