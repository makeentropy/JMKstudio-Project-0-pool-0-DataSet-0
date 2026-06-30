"""证书链管理单元测试。"""
import pytest

from cryptography import x509
from cryptography.x509.oid import NameOID

from oath_toolchain.tools.ca_system.certificate_chain import CertificateChain
from oath_toolchain.tools.ca_system.jmk_ca import JMKStudioCA
from oath_toolchain.tools.ca_system.certificate_types import CertificateType


class TestCertificateChain:
    """测试CertificateChain类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.ca = JMKStudioCA(ca_name="Test Root CA")
        self.root_cert_pem, _ = self.ca.initialize_root(key_size=2048, validity_days=3650)
        self.intermediate_cert_pem, _ = self.ca.create_intermediate_ca(
            ca_name="Test Intermediate CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
            validity_days=1825,
        )
        self.end_cert_pem, _ = self.ca.issue_certificate(
            subject="test.example.com",
            cert_type=CertificateType.END_ENTITY,
            issuer_ca="Test Intermediate CA",
            validity_days=365,
            key_size=2048,
        )

    def test_initialization(self):
        """测试初始化。"""
        chain_mgr = CertificateChain()
        assert len(chain_mgr._trusted_roots) == 0

    def test_initialization_with_trusted_roots(self):
        """测试使用受信任根证书初始化。"""
        chain_mgr = CertificateChain(trusted_roots=[self.root_cert_pem])
        assert len(chain_mgr._trusted_roots) == 1

    def test_add_trusted_root(self):
        """测试添加受信任根证书。"""
        chain_mgr = CertificateChain()
        chain_mgr.add_trusted_root(self.root_cert_pem)
        assert len(chain_mgr._trusted_roots) == 1

    def test_build_chain(self):
        """测试构建证书链。"""
        chain_mgr = CertificateChain()

        chain = chain_mgr.build_chain(
            self.end_cert_pem,
            intermediate_certs=[self.intermediate_cert_pem, self.root_cert_pem],
        )

        assert len(chain) == 3  # end -> intermediate -> root

    def test_build_chain_without_intermediates(self):
        """测试不提供中间证书构建链。"""
        chain_mgr = CertificateChain()

        chain = chain_mgr.build_chain(self.end_cert_pem)

        assert len(chain) >= 1

    def test_verify_chain_valid(self):
        """测试验证有效证书链。"""
        chain_mgr = CertificateChain(trusted_roots=[self.root_cert_pem])

        chain = chain_mgr.build_chain(
            self.end_cert_pem,
            intermediate_certs=[self.intermediate_cert_pem],
        )

        valid, message = chain_mgr.verify_chain(chain)
        assert valid is True
        assert "验证通过" in message

    def test_verify_chain_empty(self):
        """测试验证空证书链。"""
        chain_mgr = CertificateChain()
        valid, message = chain_mgr.verify_chain([])
        assert valid is False
        assert "为空" in message

    def test_get_chain_depth(self):
        """测试获取证书链深度。"""
        chain_mgr = CertificateChain()

        chain = chain_mgr.build_chain(
            self.end_cert_pem,
            intermediate_certs=[self.intermediate_cert_pem, self.root_cert_pem],
        )

        depth = chain_mgr.get_chain_depth(chain)
        assert depth == 3

    def test_get_chain_info(self):
        """测试获取证书链信息。"""
        chain_mgr = CertificateChain()

        chain = chain_mgr.build_chain(
            self.end_cert_pem,
            intermediate_certs=[self.intermediate_cert_pem, self.root_cert_pem],
        )

        info_list = chain_mgr.get_chain_info(chain)
        assert len(info_list) == 3

        first_info = info_list[0]
        assert first_info["index"] == 0
        assert first_info["subject"] == "test.example.com"
        assert first_info["is_ca"] is False

        last_info = info_list[-1]
        assert last_info["is_ca"] is True
        assert last_info["is_self_signed"] is True

    def test_chain_info_contains_cert_type(self):
        """测试证书链信息包含证书类型。"""
        chain_mgr = CertificateChain()

        chain = chain_mgr.build_chain(
            self.end_cert_pem,
            intermediate_certs=[self.intermediate_cert_pem, self.root_cert_pem],
        )

        info_list = chain_mgr.get_chain_info(chain)
        assert info_list[0]["cert_type"] == "end_entity"
        assert info_list[1]["cert_type"] == "intermediate_ca"
        assert info_list[2]["cert_type"] == "jmkstudio_root"

    def test_three_level_chain_verification(self):
        """测试三级证书链验证。"""
        chain_mgr = CertificateChain(trusted_roots=[self.root_cert_pem])

        chain = [
            self.end_cert_pem,
            self.intermediate_cert_pem,
            self.root_cert_pem,
        ]

        valid, message = chain_mgr.verify_chain(chain)
        assert valid is True
        assert "验证通过" in message

    def test_verify_chain_wrong_order(self):
        """测试验证顺序错误的证书链。"""
        chain_mgr = CertificateChain()

        chain = [
            self.root_cert_pem,
            self.intermediate_cert_pem,
            self.end_cert_pem,
        ]

        valid, _ = chain_mgr.verify_chain(chain)
        assert valid is False

    def test_build_chain_warship_cert(self):
        """测试战舰证书链构建。"""
        self.ca.create_intermediate_ca(
            ca_name="Naval CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
        )

        warship_cert_pem, _ = self.ca.issue_certificate(
            subject="USS Enterprise",
            cert_type=CertificateType.WARSHIP_CERT,
            issuer_ca="Naval CA",
            extensions={
                "ship_id": "WARSHIP-001",
                "clearance_level": "top_secret",
                "valid_sectors": ["alpha", "beta"],
                "weapon_system_auth": True,
            },
            key_size=2048,
        )

        naval_ca_pem = self.ca.get_ca_certificate("Naval CA")

        chain_mgr = CertificateChain()
        chain = chain_mgr.build_chain(
            warship_cert_pem,
            intermediate_certs=[naval_ca_pem, self.root_cert_pem],
        )

        assert len(chain) == 3
        info_list = chain_mgr.get_chain_info(chain)
        assert info_list[0]["cert_type"] == "warship_cert"

    def test_build_chain_science_cert(self):
        """测试科学证书链构建。"""
        self.ca.create_intermediate_ca(
            ca_name="Science CA",
            ca_type=CertificateType.INTERMEDIATE_CA,
        )

        science_cert_pem, _ = self.ca.issue_certificate(
            subject="Dr. Scientist",
            cert_type=CertificateType.SPACE_PHYSICS_CERT,
            issuer_ca="Science CA",
            extensions={
                "institution": "JMK Research Lab",
                "research_field": "space_physics",
                "clearance_level": "level-3",
                "project_ids": ["proj-001"],
            },
            key_size=2048,
        )

        science_ca_pem = self.ca.get_ca_certificate("Science CA")

        chain_mgr = CertificateChain()
        chain = chain_mgr.build_chain(
            science_cert_pem,
            intermediate_certs=[science_ca_pem, self.root_cert_pem],
        )

        info_list = chain_mgr.get_chain_info(chain)
        assert info_list[0]["cert_type"] == "space_physics_cert"

    def test_verify_chain_untrusted_root(self):
        """测试验证不受信任的根证书。"""
        other_ca = JMKStudioCA(ca_name="Other Root CA")
        other_root_pem, _ = other_ca.initialize_root(key_size=2048)

        chain_mgr = CertificateChain(trusted_roots=[other_root_pem])

        chain = [
            self.end_cert_pem,
            self.intermediate_cert_pem,
            self.root_cert_pem,
        ]

        valid, message = chain_mgr.verify_chain(chain)
        assert valid is False
        assert "不在信任列表" in message
