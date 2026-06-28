"""
CA认证系统测试
"""

import pytest
from ai_llm_agent_crawler.security.ca_system import (
    CertificateStatus,
    CertificateType,
    CertificateAuthority,
    CertificateStore,
    CertificateVerifier,
)


class TestCertificateAuthority:
    """测试证书颁发机构"""

    def test_initialize(self):
        """测试初始化CA"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        assert ca._private_key is not None
        assert ca._certificate is not None
        assert ca._certificate_info is not None
        assert ca._certificate_info.certificate_type == CertificateType.ROOT_CA

    def test_issue_certificate(self):
        """测试签发证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        certificate, private_key = ca.issue_certificate(
            subject_name="test.example.com",
            certificate_type=CertificateType.SERVER,
        )

        assert certificate is not None
        assert private_key is not None
        assert certificate.subject.rfc4514_string().contains("test.example.com")

    def test_issue_client_certificate(self):
        """测试签发客户端证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        certificate, private_key = ca.issue_certificate(
            subject_name="test_user",
            certificate_type=CertificateType.CLIENT,
        )

        assert certificate is not None
        assert private_key is not None

    def test_verify_certificate(self):
        """测试验证证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        certificate, _ = ca.issue_certificate(
            subject_name="test.example.com",
            certificate_type=CertificateType.SERVER,
        )

        is_valid, reason = ca.verify_certificate(certificate)

        assert is_valid
        assert reason == "证书有效"

    def test_revoke_certificate(self):
        """测试吊销证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        certificate, _ = ca.issue_certificate(
            subject_name="test.example.com",
            certificate_type=CertificateType.SERVER,
        )

        serial_number = str(certificate.serial_number)
        assert ca.revoke_certificate(serial_number, "test_revocation")

        # 验证吊销后的证书
        is_valid, reason = ca.verify_certificate(certificate)
        assert not is_valid
        assert "吊销" in reason

    def test_generate_crl(self):
        """测试生成CRL"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        # 签发并吊销证书
        cert1, _ = ca.issue_certificate("cert1", CertificateType.SERVER)
        cert2, _ = ca.issue_certificate("cert2", CertificateType.SERVER)

        ca.revoke_certificate(str(cert1.serial_number))
        ca.revoke_certificate(str(cert2.serial_number))

        crl = ca.generate_crl()

        assert len(crl.revoked_certificates) == 2

    def test_list_certificates(self):
        """测试列出证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        ca.issue_certificate("cert1", CertificateType.SERVER)
        ca.issue_certificate("cert2", CertificateType.CLIENT)

        certificates = ca.list_certificates()

        assert len(certificates) == 3  # 2 issued + 1 root

    def test_export_ca_certificate(self):
        """测试导出CA证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        pem_data = ca.export_ca_certificate("PEM")

        assert pem_data is not None
        assert b"CERTIFICATE" in pem_data

    def test_export_ca_private_key(self):
        """测试导出CA私钥"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        key_data = ca.export_ca_private_key(password=b"test123")

        assert key_data is not None
        assert b"ENCRYPTED" in key_data or b"PRIVATE KEY" in key_data


class TestCertificateStore:
    """测试证书存储"""

    def test_store_certificate(self):
        """测试存储证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        cert, key = ca.issue_certificate("test", CertificateType.SERVER)

        store = CertificateStore()
        store.store_certificate("test_cert", cert, key)

        assert "test_cert" in store.list_certificates()

    def test_get_certificate(self):
        """测试获取证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        cert, key = ca.issue_certificate("test", CertificateType.SERVER)

        store = CertificateStore()
        store.store_certificate("test_cert", cert, key)

        retrieved_cert = store.get_certificate("test_cert")

        assert retrieved_cert is not None
        assert retrieved_cert.subject.rfc4514_string() == cert.subject.rfc4514_string()

    def test_get_private_key(self):
        """测试获取私钥"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        cert, key = ca.issue_certificate("test", CertificateType.SERVER)

        store = CertificateStore()
        store.store_certificate("test_cert", cert, key)

        retrieved_key = store.get_private_key("test_cert")

        assert retrieved_key is not None

    def test_delete_certificate(self):
        """测试删除证书"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        cert, key = ca.issue_certificate("test", CertificateType.SERVER)

        store = CertificateStore()
        store.store_certificate("test_cert", cert, key)

        assert store.delete_certificate("test_cert")
        assert "test_cert" not in store.list_certificates()

    def test_export_import_store(self):
        """测试导出和导入存储"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        cert1, key1 = ca.issue_certificate("test1", CertificateType.SERVER)
        cert2, key2 = ca.issue_certificate("test2", CertificateType.CLIENT)

        store = CertificateStore()
        store.store_certificate("cert1", cert1, key1)
        store.store_certificate("cert2", cert2, key2)

        exported = store.export_store()

        new_store = CertificateStore()
        new_store.import_store(exported)

        assert len(new_store.list_certificates()) == 2


class TestCertificateVerifier:
    """测试证书验证器"""

    def test_verify_chain(self):
        """测试验证证书链"""
        ca = CertificateAuthority(name="Test CA")
        ca.initialize()

        cert, _ = ca.issue_certificate("test", CertificateType.SERVER)
        ca_cert = ca._certificate

        verifier = CertificateVerifier([ca_cert])

        is_valid, reason = verifier.verify_chain(cert)

        assert is_valid
        assert "成功" in reason

    def test_verify_chain_intermediate(self):
        """测试验证中间证书链"""
        # 创建根CA
        root_ca = CertificateAuthority(name="Root CA", validity_days=3650)
        root_ca.initialize()

        # 创建中间CA
        intermediate_ca = CertificateAuthority(name="Intermediate CA", validity_days=365)
        intermediate_ca.initialize()

        # 签发端实体证书
        end_cert, _ = root_ca.issue_certificate("test.example.com", CertificateType.SERVER)

        verifier = CertificateVerifier([root_ca._certificate])

        is_valid, reason = verifier.verify_chain(end_cert)

        assert is_valid