"""JMKstudio CA管理器单元测试。"""
import pytest

from cryptography import x509
from cryptography.x509.oid import NameOID

from oath_toolchain.tools.ca_system.jmk_ca import JMKStudioCA
from oath_toolchain.tools.ca_system.certificate_types import (
    CertificateType,
    CertificateStatus,
    WarshipCertExtension,
    ScienceCertExtension,
)


class TestJMKStudioCA:
    """测试JMKStudioCA类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.ca = JMKStudioCA(ca_name="Test Root CA")

    def test_initialization(self):
        """测试初始化。"""
        assert self.ca.ca_name == "Test Root CA"
        assert self.ca._root_cert is None
        assert self.ca._root_key is None

    def test_initialize_root(self):
        """测试初始化根CA。"""
        cert_pem, key_pem = self.ca.initialize_root(key_size=2048, validity_days=365)

        assert cert_pem is not None
        assert key_pem is not None
        assert b"BEGIN CERTIFICATE" in cert_pem
        assert b"BEGIN PRIVATE KEY" in key_pem

        cert = x509.load_pem_x509_certificate(cert_pem)
        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert subject_cn[0].value == "Test Root CA"

        assert self.ca._root_cert is not None
        assert self.ca._root_key is not None

    def test_initialize_root_self_signed(self):
        """测试根CA自签名。"""
        cert_pem, _ = self.ca.initialize_root(key_size=2048)
        cert = x509.load_pem_x509_certificate(cert_pem)

        assert cert.subject == cert.issuer

        from cryptography.hazmat.primitives.asymmetric import padding
        public_key = cert.public_key()
        public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )

    def test_create_intermediate_ca(self):
        """测试创建中间CA。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, key_pem = self.ca.create_intermediate_ca(
            ca_name="Test Intermediate CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
            validity_days=365,
        )

        assert cert_pem is not None
        assert key_pem is not None

        cert = x509.load_pem_x509_certificate(cert_pem)
        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert subject_cn[0].value == "Test Intermediate CA"

        issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert issuer_cn[0].value == "Test Root CA"

    def test_create_intermediate_ca_fbi(self):
        """测试创建FBI中间CA。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, _ = self.ca.create_intermediate_ca(
            ca_name="FBI CA",
            ca_type=CertificateType.FBI_CA,
        )

        assert cert_pem is not None
        assert "FBI CA" in self.ca._intermediate_cas

    def test_create_intermediate_ca_without_root(self):
        """测试未初始化根CA时创建中间CA。"""
        with pytest.raises(ValueError, match="根CA未初始化"):
            self.ca.create_intermediate_ca(
                ca_name="Test CA",
                ca_type=CertificateType.INTERMEDIATE_CA,
            )

    def test_create_intermediate_ca_invalid_type(self):
        """测试使用非CA类型创建中间CA。"""
        self.ca.initialize_root(key_size=2048)

        with pytest.raises(ValueError, match="不是有效的CA类型"):
            self.ca.create_intermediate_ca(
                ca_name="Test CA",
                ca_type=CertificateType.END_ENTITY,
            )

    def test_issue_certificate_from_root(self):
        """测试从根CA签发证书。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, key_pem = self.ca.issue_certificate(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="root",
            validity_days=365,
            key_size=2048,
        )

        assert cert_pem is not None
        assert key_pem is not None

        cert = x509.load_pem_x509_certificate(cert_pem)
        subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert subject_cn[0].value == "test.example.com"

    def test_issue_certificate_from_intermediate(self):
        """测试从中间CA签发证书。"""
        self.ca.initialize_root(key_size=2048)
        self.ca.create_intermediate_ca(
            ca_name="Intermediate CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
        )

        cert_pem, key_pem = self.ca.issue_certificate(
            subject="user@example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="Intermediate CA",
            key_size=2048,
        )

        assert cert_pem is not None
        assert key_pem is not None

        cert = x509.load_pem_x509_certificate(cert_pem)
        issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert issuer_cn[0].value == "Intermediate CA"

    def test_issue_warship_certificate(self):
        """测试签发战舰证书。"""
        self.ca.initialize_root(key_size=2048)

        extensions = {
            "ship_id": "WARSHIP-001",
            "clearance_level": "top_secret",
            "valid_sectors": ["alpha", "beta", "gamma"],
            "weapon_system_auth": True,
        }

        cert_pem, _ = self.ca.issue_certificate(
            subject="USS Enterprise",
            cert_type=CertificateType.WARSHIP_CERT,
            issuer_ca="root",
            extensions=extensions,
            key_size=2048,
        )

        assert cert_pem is not None
        cert = x509.load_pem_x509_certificate(cert_pem)
        assert cert is not None

    def test_issue_science_certificate(self):
        """测试签发科学证书。"""
        self.ca.initialize_root(key_size=2048)

        extensions = {
            "institution": "JMK Research Lab",
            "research_field": "space_physics",
            "clearance_level": "level-3",
            "project_ids": ["proj-001", "proj-002"],
        }

        cert_pem, _ = self.ca.issue_certificate(
            subject="Dr. Scientist",
            cert_type=CertificateType.SCIENCE_CERT,
            issuer_ca="root",
            extensions=extensions,
            key_size=2048,
        )

        assert cert_pem is not None

    def test_verify_valid_certificate(self):
        """测试验证有效证书。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, _ = self.ca.issue_certificate(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )

        valid, message = self.ca.verify_certificate(cert_pem)
        assert valid is True
        assert "验证通过" in message

    def test_verify_revoked_certificate(self):
        """测试验证已吊销证书。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, _ = self.ca.issue_certificate(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)

        self.ca.revoke_certificate(serial_number, reason="key_compromise")

        valid, message = self.ca.verify_certificate(cert_pem)
        assert valid is False
        assert "吊销" in message

    def test_get_ca_certificate_root(self):
        """测试获取根CA证书。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem = self.ca.get_ca_certificate("root")
        assert cert_pem is not None
        assert b"BEGIN CERTIFICATE" in cert_pem

    def test_get_ca_certificate_intermediate(self):
        """测试获取中间CA证书。"""
        self.ca.initialize_root(key_size=2048)
        self.ca.create_intermediate_ca(
            ca_name="Test CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
        )

        cert_pem = self.ca.get_ca_certificate("Test CA")
        assert cert_pem is not None

    def test_get_ca_certificate_not_found(self):
        """测试获取不存在的CA证书。"""
        self.ca.initialize_root(key_size=2048)

        with pytest.raises(ValueError, match="CA不存在"):
            self.ca.get_ca_certificate("NonExistent CA")

    def test_revoke_certificate(self):
        """测试吊销证书。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, _ = self.ca.issue_certificate(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)

        result = self.ca.revoke_certificate(serial_number, reason="key_compromise")
        assert result is True

        assert serial_number in self.ca._revoked_certificates
        assert self.ca._revoked_certificates[serial_number]["reason"] == "key_compromise"

    def test_revoke_nonexistent_certificate(self):
        """测试吊销不存在的证书。"""
        self.ca.initialize_root(key_size=2048)

        result = self.ca.revoke_certificate("999999999999", reason="unspecified")
        assert result is False

    def test_list_certificates(self):
        """测试列出证书。"""
        self.ca.initialize_root(key_size=2048)
        self.ca.issue_certificate(
            subject="cert1.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )
        self.ca.issue_certificate(
            subject="cert2.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )

        certs = self.ca.list_certificates()
        assert len(certs) >= 3  # root + 2 issued

    def test_list_certificates_by_status(self):
        """测试按状态列出证书。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, _ = self.ca.issue_certificate(
            subject="to-revoke.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )

        cert = x509.load_pem_x509_certificate(cert_pem)
        serial_number = str(cert.serial_number)
        self.ca.revoke_certificate(serial_number, reason="key_compromise")

        valid_certs = self.ca.list_certificates(status="valid")
        revoked_certs = self.ca.list_certificates(status="revoked")

        assert len(valid_certs) >= 1
        assert len(revoked_certs) == 1

    def test_get_certificate_info(self):
        """测试获取证书信息。"""
        self.ca.initialize_root(key_size=2048)

        cert_pem, _ = self.ca.issue_certificate(
            subject="info-test.example.com",
            cert_type=CertificateType.END_ENTITY,
            key_size=2048,
        )

        info = self.ca.get_certificate_info(cert_pem)
        assert info["subject"] == "info-test.example.com"
        assert info["cert_type"] == "end_entity"
        assert "serial_number" in info
        assert "not_valid_before" in info
        assert "not_valid_after" in info

    def test_preset_ca_hierarchy_fbi(self):
        """测试FBI CA层级。"""
        self.ca.initialize_root(key_size=2048)
        self.ca.create_intermediate_ca(
            ca_name="FBI Intermediate CA",
            ca_type=CertificateType.FBI_CA,
        )

        cert_pem, _ = self.ca.issue_certificate(
            subject="Agent Smith",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="FBI Intermediate CA",
            key_size=2048,
        )

        valid, _ = self.ca.verify_certificate(cert_pem)
        assert valid is True

    def test_preset_ca_hierarchy_cia(self):
        """测试CIA CA层级。"""
        self.ca.initialize_root(key_size=2048)
        self.ca.create_intermediate_ca(
            ca_name="CIA Intermediate CA",
            ca_type=CertificateType.CIA_CA,
        )

        cert_pem, _ = self.ca.issue_certificate(
            subject="Operative Bond",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="CIA Intermediate CA",
            key_size=2048,
        )

        valid, _ = self.ca.verify_certificate(cert_pem)
        assert valid is True
