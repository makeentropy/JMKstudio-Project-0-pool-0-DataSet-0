"""证书工作流集成测试。"""
from __future__ import annotations

import pytest

from oath_toolchain.tools.ca_system.jmk_ca import JMKStudioCA
from oath_toolchain.tools.ca_system.certificate_types import (
    CertificateType,
    CertificateStatus,
)


pytestmark = [pytest.mark.integration, pytest.mark.certificate]


class TestCertificateChain:
    """完整证书链创建与验证测试。"""

    def test_root_to_leaf_chain(self):
        """测试从根CA到终端实体的完整证书链。"""
        ca = JMKStudioCA(ca_name="Test Root CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        ca.create_intermediate_ca(
            ca_name="Intermediate CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
            validity_days=180,
        )

        cert_pem, key_pem = ca.issue_certificate(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="Intermediate CA",
            validity_days=90,
        )

        assert cert_pem is not None
        assert key_pem is not None
        assert b"BEGIN CERTIFICATE" in cert_pem
        assert b"BEGIN PRIVATE KEY" in key_pem

        valid, msg = ca.verify_certificate(cert_pem)
        assert valid, f"证书验证失败: {msg}"

    def test_multi_level_chain(self):
        """测试多级证书链。"""
        ca = JMKStudioCA(ca_name="Root CA")
        ca.initialize_root(key_size=2048, validity_days=3650)

        ca.create_intermediate_ca(
            ca_name="Policy CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
            validity_days=1825,
        )

        cert_pem, _ = ca.issue_certificate(
            subject="leaf.example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="Policy CA",
            validity_days=365,
        )

        valid, msg = ca.verify_certificate(cert_pem)
        assert valid, f"证书验证失败: {msg}"

    def test_root_ca_self_signed(self):
        """测试根CA自签名证书验证。"""
        ca = JMKStudioCA(ca_name="Test Root")
        root_cert_pem, _ = ca.initialize_root(key_size=2048, validity_days=365)

        valid, msg = ca.verify_certificate(root_cert_pem)
        assert valid, f"根证书验证失败: {msg}"


class TestCertificateSignVerify:
    """证书签名与验证流程测试。"""

    def test_certificate_signature_verification(self):
        """测试证书签名验证。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        cert_pem, _ = ca.issue_certificate(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            validity_days=90,
        )

        valid, msg = ca.verify_certificate(cert_pem)
        assert valid, f"证书验证失败: {msg}"

    def test_multiple_certificates(self):
        """测试多个证书的签发和验证。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        subjects = [
            "server1.example.com",
            "server2.example.com",
            "client1.example.com",
            "client2.example.com",
        ]

        certs = []
        for subject in subjects:
            cert_pem, _ = ca.issue_certificate(
                subject=subject,
                cert_type=CertificateType.END_ENTITY,
                validity_days=90,
            )
            certs.append(cert_pem)

        assert len(certs) == 4

        for cert_pem in certs:
            valid, msg = ca.verify_certificate(cert_pem)
            assert valid, f"证书验证失败: {msg}"

    def test_fbi_ca_type(self):
        """测试FBI CA类型。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        ca.create_intermediate_ca(
            ca_name="FBI CA",
            ca_type=CertificateType.FBI_CA,
        )

        cert_pem, _ = ca.issue_certificate(
            subject="agent@fbi.example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="FBI CA",
        )

        valid, msg = ca.verify_certificate(cert_pem)
        assert valid, f"证书验证失败: {msg}"

    def test_cia_ca_type(self):
        """测试CIA CA类型。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        ca.create_intermediate_ca(
            ca_name="CIA CA",
            ca_type=CertificateType.CIA_CA,
        )

        cert_pem, _ = ca.issue_certificate(
            subject="agent@cia.example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="CIA CA",
        )

        valid, msg = ca.verify_certificate(cert_pem)
        assert valid, f"证书验证失败: {msg}"


class TestCertificateRevocation:
    """证书吊销流程测试。"""

    def test_revoke_certificate(self):
        """测试证书吊销流程。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        cert_pem, _ = ca.issue_certificate(
            subject="revoked.example.com",
            cert_type=CertificateType.END_ENTITY,
            validity_days=90,
        )

        valid_before, _ = ca.verify_certificate(cert_pem)
        assert valid_before

        from cryptography import x509
        cert = x509.load_pem_x509_certificate(cert_pem)
        serial = str(cert.serial_number)

        revoked = ca.revoke_certificate(serial, reason="key_compromise")
        assert revoked

        valid_after, msg = ca.verify_certificate(cert_pem)
        assert not valid_after
        assert "吊销" in msg or "revoked" in msg.lower()

    def test_revoke_nonexistent_certificate(self):
        """测试吊销不存在的证书。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        result = ca.revoke_certificate("nonexistent_serial")
        assert not result

    def test_revoked_certificate_in_chain(self):
        """测试证书链中吊销的证书。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        ca.create_intermediate_ca(
            ca_name="Int CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
        )

        cert_pem, _ = ca.issue_certificate(
            subject="leaf.example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="Int CA",
        )

        from cryptography import x509
        cert = x509.load_pem_x509_certificate(cert_pem)
        serial = str(cert.serial_number)

        ca.revoke_certificate(serial, reason="cessation")

        valid, msg = ca.verify_certificate(cert_pem)
        assert not valid


class TestCertificateTypes:
    """不同类型证书测试。"""

    def test_end_entity_certificate(self):
        """测试终端实体证书。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        cert_pem, _ = ca.issue_certificate(
            subject="server.example.com",
            cert_type=CertificateType.END_ENTITY,
        )
        valid, _ = ca.verify_certificate(cert_pem)
        assert valid

    def test_warship_certificate(self):
        """测试战舰证书。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        cert_pem, _ = ca.issue_certificate(
            subject="ship@navy.example.com",
            cert_type=CertificateType.WARSHIP_CERT,
        )
        valid, _ = ca.verify_certificate(cert_pem)
        assert valid

    def test_science_certificate(self):
        """测试科学证书。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        cert_pem, _ = ca.issue_certificate(
            subject="scientist@example.com",
            cert_type=CertificateType.SCIENCE_CERT,
        )
        valid, _ = ca.verify_certificate(cert_pem)
        assert valid

    def test_space_physics_certificate(self):
        """测试空间物理证书。"""
        ca = JMKStudioCA(ca_name="Test CA")
        ca.initialize_root(key_size=2048, validity_days=365)

        cert_pem, _ = ca.issue_certificate(
            subject="physicist@space.example.com",
            cert_type=CertificateType.SPACE_PHYSICS_CERT,
        )
        valid, _ = ca.verify_certificate(cert_pem)
        assert valid
