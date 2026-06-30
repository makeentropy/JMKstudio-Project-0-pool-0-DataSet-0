"""证书类型单元测试。"""
import pytest

from oath_toolchain.tools.ca_system.certificate_types import (
    CertificateType,
    CertificateStatus,
    RevocationReason,
    JMKStudioExtension,
    WarshipCertExtension,
    ScienceCertExtension,
)


class TestCertificateType:
    """测试CertificateType枚举。"""

    def test_certificate_type_values(self):
        """测试证书类型值。"""
        assert CertificateType.ROOT_CA.value == "root_ca"
        assert CertificateType.INTERMEDIATE_CA.value == "intermediate_ca"
        assert CertificateType.JMKSTUDIO_ROOT.value == "jmkstudio_root"
        assert CertificateType.FBI_CA.value == "fbi_ca"
        assert CertificateType.CIA_CA.value == "cia_ca"
        assert CertificateType.WARSHIP_CERT.value == "warship_cert"
        assert CertificateType.SCIENCE_CERT.value == "science_cert"
        assert CertificateType.SPACE_PHYSICS_CERT.value == "space_physics_cert"
        assert CertificateType.END_ENTITY.value == "end_entity"

    def test_is_ca_type(self):
        """测试is_ca_type方法。"""
        assert CertificateType.is_ca_type(CertificateType.ROOT_CA) is True
        assert CertificateType.is_ca_type(CertificateType.INTERMEDIATE_CA) is True
        assert CertificateType.is_ca_type(CertificateType.JMKSTUDIO_ROOT) is True
        assert CertificateType.is_ca_type(CertificateType.FBI_CA) is True
        assert CertificateType.is_ca_type(CertificateType.CIA_CA) is True
        assert CertificateType.is_ca_type(CertificateType.WARSHIP_CERT) is False
        assert CertificateType.is_ca_type(CertificateType.END_ENTITY) is False

    def test_from_string(self):
        """测试from_string方法。"""
        assert CertificateType.from_string("root_ca") == CertificateType.ROOT_CA
        assert CertificateType.from_string("end_entity") == CertificateType.END_ENTITY
        assert CertificateType.from_string("warship_cert") == CertificateType.WARSHIP_CERT

    def test_from_string_invalid(self):
        """测试from_string方法（无效类型）。"""
        with pytest.raises(ValueError):
            CertificateType.from_string("invalid_type")


class TestJMKStudioExtension:
    """测试JMKStudioExtension数据类。"""

    def test_creation(self):
        """测试创建扩展。"""
        ext = JMKStudioExtension(
            studio_id="studio-001",
            authorization_level="admin",
            geometric_proof_hash=b"test_hash",
            karma_level=100,
        )
        assert ext.studio_id == "studio-001"
        assert ext.authorization_level == "admin"
        assert ext.geometric_proof_hash == b"test_hash"
        assert ext.karma_level == 100

    def test_to_dict(self):
        """测试to_dict方法。"""
        ext = JMKStudioExtension(
            studio_id="studio-001",
            authorization_level="admin",
            geometric_proof_hash=b"\x01\x02\x03",
            karma_level=100,
        )
        data = ext.to_dict()
        assert data["studio_id"] == "studio-001"
        assert data["authorization_level"] == "admin"
        assert data["geometric_proof_hash"] == "010203"
        assert data["karma_level"] == 100

    def test_from_dict(self):
        """测试from_dict方法。"""
        data = {
            "studio_id": "studio-001",
            "authorization_level": "admin",
            "geometric_proof_hash": "010203",
            "karma_level": 100,
        }
        ext = JMKStudioExtension.from_dict(data)
        assert ext.studio_id == "studio-001"
        assert ext.authorization_level == "admin"
        assert ext.geometric_proof_hash == b"\x01\x02\x03"
        assert ext.karma_level == 100

    def test_roundtrip(self):
        """测试往返转换。"""
        original = JMKStudioExtension(
            studio_id="studio-001",
            authorization_level="admin",
            geometric_proof_hash=b"\x01\x02\x03\x04",
            karma_level=100,
        )
        data = original.to_dict()
        restored = JMKStudioExtension.from_dict(data)
        assert restored.studio_id == original.studio_id
        assert restored.authorization_level == original.authorization_level
        assert restored.geometric_proof_hash == original.geometric_proof_hash
        assert restored.karma_level == original.karma_level


class TestWarshipCertExtension:
    """测试WarshipCertExtension数据类。"""

    def test_creation(self):
        """测试创建扩展。"""
        ext = WarshipCertExtension(
            ship_id="warship-001",
            clearance_level="top_secret",
            valid_sectors=["sector-1", "sector-2"],
            weapon_system_auth=True,
        )
        assert ext.ship_id == "warship-001"
        assert ext.clearance_level == "top_secret"
        assert ext.valid_sectors == ["sector-1", "sector-2"]
        assert ext.weapon_system_auth is True

    def test_default_values(self):
        """测试默认值。"""
        ext = WarshipCertExtension(
            ship_id="warship-001",
            clearance_level="secret",
        )
        assert ext.valid_sectors == []
        assert ext.weapon_system_auth is False

    def test_to_dict(self):
        """测试to_dict方法。"""
        ext = WarshipCertExtension(
            ship_id="warship-001",
            clearance_level="top_secret",
            valid_sectors=["sector-1", "sector-2"],
            weapon_system_auth=True,
        )
        data = ext.to_dict()
        assert data["ship_id"] == "warship-001"
        assert data["clearance_level"] == "top_secret"
        assert data["valid_sectors"] == ["sector-1", "sector-2"]
        assert data["weapon_system_auth"] is True

    def test_from_dict(self):
        """测试from_dict方法。"""
        data = {
            "ship_id": "warship-001",
            "clearance_level": "top_secret",
            "valid_sectors": ["sector-1", "sector-2"],
            "weapon_system_auth": True,
        }
        ext = WarshipCertExtension.from_dict(data)
        assert ext.ship_id == "warship-001"
        assert ext.clearance_level == "top_secret"
        assert ext.valid_sectors == ["sector-1", "sector-2"]
        assert ext.weapon_system_auth is True

    def test_roundtrip(self):
        """测试往返转换。"""
        original = WarshipCertExtension(
            ship_id="warship-001",
            clearance_level="top_secret",
            valid_sectors=["sector-1", "sector-2", "sector-3"],
            weapon_system_auth=True,
        )
        data = original.to_dict()
        restored = WarshipCertExtension.from_dict(data)
        assert restored.ship_id == original.ship_id
        assert restored.clearance_level == original.clearance_level
        assert restored.valid_sectors == original.valid_sectors
        assert restored.weapon_system_auth == original.weapon_system_auth


class TestScienceCertExtension:
    """测试ScienceCertExtension数据类。"""

    def test_creation(self):
        """测试创建扩展。"""
        ext = ScienceCertExtension(
            institution="JMK Research Lab",
            research_field="space_physics",
            clearance_level="level-3",
            project_ids=["proj-1", "proj-2"],
        )
        assert ext.institution == "JMK Research Lab"
        assert ext.research_field == "space_physics"
        assert ext.clearance_level == "level-3"
        assert ext.project_ids == ["proj-1", "proj-2"]

    def test_to_dict_and_back(self):
        """测试to_dict和from_dict往返。"""
        original = ScienceCertExtension(
            institution="Test Lab",
            research_field="quantum",
            clearance_level="level-1",
            project_ids=["p1", "p2"],
        )
        data = original.to_dict()
        restored = ScienceCertExtension.from_dict(data)
        assert restored.institution == original.institution
        assert restored.research_field == original.research_field
        assert restored.clearance_level == original.clearance_level
        assert restored.project_ids == original.project_ids


class TestCertificateStatus:
    """测试CertificateStatus枚举。"""

    def test_status_values(self):
        """测试状态值。"""
        assert CertificateStatus.VALID.value == "valid"
        assert CertificateStatus.REVOKED.value == "revoked"
        assert CertificateStatus.EXPIRED.value == "expired"
        assert CertificateStatus.NOT_YET_VALID.value == "not_yet_valid"


class TestRevocationReason:
    """测试RevocationReason枚举。"""

    def test_reason_values(self):
        """测试吊销原因值。"""
        assert RevocationReason.UNSPECIFIED.value == "unspecified"
        assert RevocationReason.KEY_COMPROMISE.value == "key_compromise"
        assert RevocationReason.CA_COMPROMISE.value == "ca_compromise"
        assert RevocationReason.AFFILIATION_CHANGED.value == "affiliation_changed"
        assert RevocationReason.SUPERSEDED.value == "superseded"
        assert RevocationReason.CESSATION_OF_OPERATION.value == "cessation_of_operation"
        assert RevocationReason.PRIVILEGE_WITHDRAWN.value == "privilege_withdrawn"
