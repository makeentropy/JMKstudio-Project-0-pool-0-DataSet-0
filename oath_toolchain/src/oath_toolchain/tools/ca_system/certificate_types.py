"""证书类型定义模块。

定义JMKstudio CA证书体系中的证书类型枚举和扩展字段数据类，
支持多种特殊证书类型（战舰证书、科学证书等）及其扩展字段。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class CertificateType(Enum):
    """证书类型枚举。

    定义JMKstudio CA体系中所有支持的证书类型。

    Attributes:
        ROOT_CA: 根CA证书
        INTERMEDIATE_CA: 中间CA证书
        JMKSTUDIO_ROOT: JMKstudio根CA证书
        FBI_CA: FBI中间CA证书
        CIA_CA: CIA中间CA证书
        WARSHIP_CERT: 战舰证书
        SCIENCE_CERT: 科学证书
        SPACE_PHYSICS_CERT: 空间物理证书
        END_ENTITY: 终端实体证书
    """

    ROOT_CA = "root_ca"
    INTERMEDIATE_CA = "intermediate_ca"
    JMKSTUDIO_ROOT = "jmkstudio_root"
    FBI_CA = "fbi_ca"
    CIA_CA = "cia_ca"
    WARSHIP_CERT = "warship_cert"
    SCIENCE_CERT = "science_cert"
    SPACE_PHYSICS_CERT = "space_physics_cert"
    END_ENTITY = "end_entity"

    @classmethod
    def is_ca_type(cls, cert_type: "CertificateType") -> bool:
        """判断证书类型是否为CA类型。

        Args:
            cert_type: 证书类型

        Returns:
            如果是CA类型返回True，否则返回False
        """
        ca_types = {
            cls.ROOT_CA,
            cls.INTERMEDIATE_CA,
            cls.JMKSTUDIO_ROOT,
            cls.FBI_CA,
            cls.CIA_CA,
        }
        return cert_type in ca_types

    @classmethod
    def from_string(cls, type_str: str) -> "CertificateType":
        """从字符串获取证书类型。

        Args:
            type_str: 证书类型字符串

        Returns:
            对应的CertificateType枚举值

        Raises:
            ValueError: 当字符串不匹配任何证书类型时
        """
        for cert_type in cls:
            if cert_type.value == type_str:
                return cert_type
        raise ValueError(f"未知的证书类型: {type_str}")


@dataclass
class JMKStudioExtension:
    """JMKStudio证书扩展字段。

    包含JMKstudio特有的证书扩展信息，包括工作室ID、授权级别、
    几何证据哈希和业力等级。

    Attributes:
        studio_id: 工作室ID
        authorization_level: 授权级别
        geometric_proof_hash: 几何证据哈希值
        karma_level: 业力等级
    """

    studio_id: str
    authorization_level: str
    geometric_proof_hash: bytes
    karma_level: int

    def to_dict(self) -> dict:
        """转换为字典。

        Returns:
            包含扩展字段的字典
        """
        return {
            "studio_id": self.studio_id,
            "authorization_level": self.authorization_level,
            "geometric_proof_hash": self.geometric_proof_hash.hex(),
            "karma_level": self.karma_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JMKStudioExtension":
        """从字典创建扩展对象。

        Args:
            data: 包含扩展字段的字典

        Returns:
            JMKStudioExtension实例
        """
        return cls(
            studio_id=data["studio_id"],
            authorization_level=data["authorization_level"],
            geometric_proof_hash=bytes.fromhex(data["geometric_proof_hash"]),
            karma_level=data["karma_level"],
        )


@dataclass
class WarshipCertExtension:
    """战舰证书扩展字段。

    包含战舰证书特有的扩展信息，包括舰船ID、安全级别、
    有效扇区和武器系统授权。

    Attributes:
        ship_id: 舰船ID
        clearance_level: 安全级别
        valid_sectors: 有效扇区列表
        weapon_system_auth: 武器系统授权标志
    """

    ship_id: str
    clearance_level: str
    valid_sectors: List[str] = field(default_factory=list)
    weapon_system_auth: bool = False

    def to_dict(self) -> dict:
        """转换为字典。

        Returns:
            包含扩展字段的字典
        """
        return {
            "ship_id": self.ship_id,
            "clearance_level": self.clearance_level,
            "valid_sectors": list(self.valid_sectors),
            "weapon_system_auth": self.weapon_system_auth,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WarshipCertExtension":
        """从字典创建扩展对象。

        Args:
            data: 包含扩展字段的字典

        Returns:
            WarshipCertExtension实例
        """
        return cls(
            ship_id=data["ship_id"],
            clearance_level=data["clearance_level"],
            valid_sectors=data.get("valid_sectors", []),
            weapon_system_auth=data.get("weapon_system_auth", False),
        )


@dataclass
class ScienceCertExtension:
    """科学证书扩展字段。

    包含科学证书特有的扩展信息。

    Attributes:
        institution: 研究机构
        research_field: 研究领域
        clearance_level: 访问级别
        project_ids: 授权项目ID列表
    """

    institution: str
    research_field: str
    clearance_level: str
    project_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典。

        Returns:
            包含扩展字段的字典
        """
        return {
            "institution": self.institution,
            "research_field": self.research_field,
            "clearance_level": self.clearance_level,
            "project_ids": list(self.project_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScienceCertExtension":
        """从字典创建扩展对象。

        Args:
            data: 包含扩展字段的字典

        Returns:
            ScienceCertExtension实例
        """
        return cls(
            institution=data["institution"],
            research_field=data["research_field"],
            clearance_level=data["clearance_level"],
            project_ids=data.get("project_ids", []),
        )


class CertificateStatus(Enum):
    """证书状态枚举。

    Attributes:
        VALID: 有效
        REVOKED: 已吊销
        EXPIRED: 已过期
        NOT_YET_VALID: 尚未生效
    """

    VALID = "valid"
    REVOKED = "revoked"
    EXPIRED = "expired"
    NOT_YET_VALID = "not_yet_valid"


class RevocationReason(Enum):
    """吊销原因枚举。

    Attributes:
        UNSPECIFIED: 未指定
        KEY_COMPROMISE: 密钥泄露
        CA_COMPROMISE: CA泄露
        AFFILIATION_CHANGED: 从属关系变更
        SUPERSEDED: 被取代
        CESSATION_OF_OPERATION: 停止运营
        CERTIFICATE_HOLD: 证书挂起
        REMOVE_FROM_CRL: 从CRL移除
        PRIVILEGE_WITHDRAWN: 权限撤销
        AA_COMPROMISE: AA泄露
    """

    UNSPECIFIED = "unspecified"
    KEY_COMPROMISE = "key_compromise"
    CA_COMPROMISE = "ca_compromise"
    AFFILIATION_CHANGED = "affiliation_changed"
    SUPERSEDED = "superseded"
    CESSATION_OF_OPERATION = "cessation_of_operation"
    CERTIFICATE_HOLD = "certificate_hold"
    REMOVE_FROM_CRL = "remove_from_crl"
    PRIVILEGE_WITHDRAWN = "privilege_withdrawn"
    AA_COMPROMISE = "aa_compromise"
