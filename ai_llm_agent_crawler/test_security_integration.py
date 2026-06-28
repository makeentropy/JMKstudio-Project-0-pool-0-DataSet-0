"""
安全模块功能验证脚本

快速验证各个安全模块的基本功能。
"""

import sys

def test_gpg_encryption():
    """测试GPG加密模块"""
    print("测试GPG加密模块...")
    from ai_llm_agent_crawler.security.gpg_encryption import (
        EncryptionMode, GPGKeyManager, GPGDictionaryEncryptor
    )
    
    # 创建密钥管理器并生成密钥对
    key_manager = GPGKeyManager()
    private_key, public_key = key_manager.generate_key_pair("test_key")
    
    # 创建加密器
    encryptor = GPGDictionaryEncryptor(key_manager)
    
    # 测试加密和解密
    test_data = {"name": "test", "value": 123}
    encrypted = encryptor.encrypt_dict(test_data, "test_key", EncryptionMode.HYBRID)
    decrypted = encryptor.decrypt_dict(encrypted, "test_key")
    
    assert decrypted == test_data, "GPG加密解密失败"
    print("✓ GPG加密模块测试通过")
    return True


def test_ca_system():
    """测试CA认证系统"""
    print("测试CA认证系统...")
    from ai_llm_agent_crawler.security.ca_system import (
        CertificateAuthority, CertificateType, CertificateStatus
    )
    
    # 创建并初始化CA
    ca = CertificateAuthority(name="Test CA")
    ca.initialize()
    
    # 签发证书
    cert, private_key = ca.issue_certificate(
        subject_name="test.example.com",
        certificate_type=CertificateType.SERVER
    )
    
    # 验证证书
    is_valid, reason = ca.verify_certificate(cert)
    assert is_valid, f"证书验证失败: {reason}"
    
    print("✓ CA认证系统测试通过")
    return True


def test_datachain_compression():
    """测试Datachain压缩算法"""
    print("测试Datachain压缩算法...")
    from ai_llm_agent_crawler.security.datachain_compression import (
        CompressionAlgorithm, CompressionLevel, DataChainCompressor, DataBlock
    )
    
    # 创建压缩器（使用ZLIB，因为ZSTD可能未安装）
    compressor = DataChainCompressor(
        algorithm=CompressionAlgorithm.ZLIB,
        level=5
    )
    
    # 测试压缩和解压
    test_data = b"Hello, this is a test data for compression. " * 100
    compressed, metadata = compressor.compress_data(test_data)
    decompressed = compressor.decompress_data(compressed, metadata)
    
    assert decompressed == test_data, "压缩解压数据不匹配"
    assert metadata.compressed_size < metadata.original_size, "压缩后大小应小于原始大小"
    
    # 测试数据链压缩
    blocks = [
        DataBlock(block_id="block1", data=b"Block 1 data " * 50, sequence_number=1),
        DataBlock(block_id="block2", data=b"Block 2 data " * 50, sequence_number=2),
    ]
    
    compressed_blocks, header = compressor.compress_chain(blocks)
    decompressed_blocks = compressor.decompress_chain(compressed_blocks, header)
    
    assert len(decompressed_blocks) == len(blocks), "解压块数量不匹配"
    
    print("✓ Datachain压缩算法测试通过")
    return True


def test_access_control():
    """测试访问控制模块"""
    print("测试访问控制模块...")
    from ai_llm_agent_crawler.security.access_control import (
        Permission, ResourceType, AccessDecision, AccessController
    )
    
    # 创建访问控制器
    controller = AccessController()
    
    # 创建用户
    user = controller.user_manager.create_user(
        username="test_user",
        email="test@example.com",
        password="password123",
        permissions=Permission.READ_WRITE
    )
    
    # 创建资源
    resource = controller.resource_manager.create_resource(
        resource_type=ResourceType.DATA,
        name="test_resource",
        description="Test resource",
        owner=user.user_id
    )
    
    # 检查访问权限（所有者应该可以访问）
    decision = controller.check_access(
        user.user_id,
        resource.resource_id,
        Permission.READ
    )
    
    assert decision == AccessDecision.ALLOWED, f"访问被拒绝: {decision}"
    
    # 测试认证
    session, auth_decision = controller.user_manager.authenticate(
        "test_user",
        "password123"
    )
    
    assert session is not None, "认证失败"
    assert auth_decision == AccessDecision.ALLOWED, "认证决策错误"
    
    print("✓ 访问控制模块测试通过")
    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("开始验证安全与加密系统功能")
    print("=" * 60)
    
    tests = [
        test_gpg_encryption,
        test_ca_system,
        test_datachain_compression,
        test_access_control,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            results.append(False)
    
    print("=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)