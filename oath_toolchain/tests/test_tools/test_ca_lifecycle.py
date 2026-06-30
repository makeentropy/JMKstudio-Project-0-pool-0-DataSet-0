"""证书生命周期管理单元测试。"""
import pytest

from cryptography import x509
from cryptography.x509.oid import NameOID

from oath_toolchain.tools.ca_system.certificate_lifecycle import CertificateLifecycleManager
from oath_toolchain.tools.ca_system.certificate_types import (
    CertificateType,
    CertificateStatus,
    RevocationReason,
)
from oath_toolchain.tools.ca_system.jmk_ca import JMKStudioCA


class TestCertificateLifecycleManager:
    """测试CertificateLifecycleManager类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.ca = JMKStudioCA(ca_name="Test Root CA")
        self.root_cert_pem, self.root_key_pem = self.ca.initialize_root(key_size=2048)
        self.lifecycle = CertificateLifecycleManager(
            ca_cert_pem=self.root_cert_pem,
            ca_key_pem=self.root_key_pem,
        )

    def test_initialization_without_ca(self):
        """测试无CA初始化。"""
        lifecycle = CertificateLifecycleManager()
        assert lifecycle._ca_cert is None
        assert lifecycle._ca_key is None

    def test_initialization_with_ca(self):
        """测试有CA初始化。"""
        assert self.lifecycle._ca_cert is not None
        assert self.lifecycle._ca_key is not None

    def test_set_ca(self):
        """测试设置CA。"""
        lifecycle = CertificateLifecycleManager()
        lifecycle.set_ca(self.root_cert_pem, self.root_key_pem)
        assert lifecycle._ca_cert is not None
        assert lifecycle._ca_key is not None

    def test_issue_cert(self):
        """测试签发证书。"""
        cert_pem, key_pem = self.lifecycle.issue_cert(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            validity_days=365,
            key_size=2048,
        )

        assert cert_pem is not None
        assert key_pem is not None
        assert b"BEGIN CERTIFICATE" in cert_pem
        assert b"BEGIN PRIVATE KEY" in key_pem

        cert = x509.load_pem_x509_certificate(cert_pem)
        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert subject_cn[0].value == "test.example.com"

    def test_issue_cert_without_ca(self):
        """测试未设置CA时签发证书。"""
        lifecycle = CertificateLifecycleManager()
        with pytest.raises(ValueError, match="CA证书和私钥未设置"):
            lifecycle.issue_cert(subject="test.example.com")

    def test_renew_cert(self):
        """测试续期证书。"""
        cert_pem, key_pem = self.lifecycle.issue_cert(
            subject="renew-test.example.com",
            validity_days=30,
            key_size=2048,
        )

        new_cert_pem, new_key_pem = self.lifecycle.renew_cert(
            cert_pem,
            key_pem,
            new_validity_days=365,
        )

        assert new_cert_pem is not None
        assert new_key_pem is not None

        old_cert = x509.load_pem_x509_certificate(cert_pem)
        new_cert = x509.load_pem_x509_certificate(new_cert_pem)

        assert new_cert.serial_number != old_cert.serial_number
        assert new_cert.not_valid_after_utc > old_cert.not_valid_after_utc

    def test_renew_revoked_cert(self):
        """测试续期已吊销的证书。"""
        cert_pem, key_pem = self.lifecycle.issue_cert(
            subject="revoked-test.example.com",
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)

        self.lifecycle.revoke_cert(serial_number, reason="key_compromise")

        with pytest.raises(ValueError, match="已被吊销"):
            self.lifecycle.renew_cert(cert_pem, key_pem)

    def test_revoke_cert(self):
        """测试吊销证书。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="revoke-test.example.com",
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)

        result = self.lifecycle.revoke_cert(serial_number, reason="key_compromise")
        assert result is True

        assert serial_number in self.lifecycle._revoked_certificates
        assert self.lifecycle._revoked_certificates[serial_number]["reason"] == "key_compromise"

    def test_revoke_nonexistent_cert(self):
        """测试吊销不存在的证书。"""
        result = self.lifecycle.revoke_cert("999999999999", reason="unspecified")
        assert result is False

    def test_generate_crl(self):
        """测试生成CRL。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="crl-test.example.com",
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)
        self.lifecycle.revoke_cert(serial_number, reason="key_compromise")

        crl_pem = self.lifecycle.generate_crl(next_update_days=30)

        assert crl_pem is not None
        assert b"BEGIN X509 CRL" in crl_pem

        crl = x509.load_pem_x509_crl(crl_pem)
        revoked_certs = list(crl)
        assert len(revoked_certs) >= 1

    def test_generate_crl_without_ca(self):
        """测试未设置CA时生成CRL。"""
        lifecycle = CertificateLifecycleManager()
        with pytest.raises(ValueError, match="CA证书和私钥未设置"):
            lifecycle.generate_crl()

    def test_check_status_valid(self):
        """测试检查有效证书状态。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="status-test.example.com",
            key_size=2048,
        )

        status = self.lifecycle.check_status(cert_pem)
        assert status == CertificateStatus.VALID.value

    def test_check_status_revoked(self):
        """测试检查已吊销证书状态。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="revoked-status.example.com",
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)
        self.lifecycle.revoke_cert(serial_number, reason="key_compromise")

        status = self.lifecycle.check_status(cert_pem)
        assert status == CertificateStatus.REVOKED.value

    def test_export_cert_info(self):
        """测试导出证书信息。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="export-test.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )

        info = self.lifecycle.export_cert_info(cert_pem)

        assert info["subject"] == "export-test.example.com"
        assert info["cert_type"] == "end_entity"
        assert info["is_ca"] is False
        assert info["status"] == "valid"
        assert "serial_number" in info
        assert "not_valid_before" in info
        assert "not_valid_after" in info
        assert "signature_algorithm" in info
        assert "extensions" in info

    def test_list_certificates(self):
        """测试列出证书。"""
        self.lifecycle.issue_cert(subject="cert1.example.com", key_size=2048)
        self.lifecycle.issue_cert(subject="cert2.example.com", key_size=2048)

        certs = self.lifecycle.list_certificates()
        assert len(certs) >= 2

    def test_list_certificates_by_status(self):
        """测试按状态列出证书。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="to-revoke.example.com",
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)
        self.lifecycle.revoke_cert(serial_number, reason="key_compromise")

        valid_certs = self.lifecycle.list_certificates(status="valid")
        revoked_certs = self.lifecycle.list_certificates(status="revoked")

        assert len(valid_certs) >= 0
        assert len(revoked_certs) == 1

    def test_get_revoked_certificates(self):
        """测试获取已吊销证书列表。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="revoked-list.example.com",
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)
        self.lifecycle.revoke_cert(serial_number, reason="key_compromise")

        revoked_list = self.lifecycle.get_revoked_certificates()
        assert len(revoked_list) == 1
        assert revoked_list[0]["serial_number"] == serial_number
        assert revoked_list[0]["reason"] == "key_compromise"
        assert "revocation_date" in revoked_list[0]

    def test_issue_warship_cert(self):
        """测试签发战舰证书。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="USS Enterprise",
            cert_type=CertificateType.WARSHIP_CERT,
            key_size=2048,
        )

        info = self.lifecycle.export_cert_info(cert_pem)
        assert info["cert_type"] == "warship_cert"

    def test_issue_science_cert(self):
        """测试签发科学证书。"""
        cert_pem, _ = self.lifecycle.issue_cert(
            subject="Dr. Scientist",
            cert_type=CertificateType.SCIENCE_CERT,
            key_size=2048,
        )

        info = self.lifecycle.export_cert_info(cert_pem)
        assert info["cert_type"] == "science_cert"

    def test_renew_cert_default_validity(self):
        """测试续期证书（使用默认有效期）。"""
        cert_pem, key_pem = self.lifecycle.issue_cert(
            subject="default-renew.example.com",
            validity_days=60,
            key_size=2048,
        )

        new_cert_pem, _ = self.lifecycle.renew_cert(cert_pem, key_pem)

        old_cert = x509.load_pem_x509_certificate(cert_pem)
        new_cert = x509.load_pem_x509_certificate(new_cert_pem)

        old_validity = old_cert.not_valid_after_utc - old_cert.not_valid_before_utc
        new_validity = new_cert.not_valid_after_utc - new_cert.not_valid_before_utc

        assert abs(new_validity.days - old_validity.days) <= 1
