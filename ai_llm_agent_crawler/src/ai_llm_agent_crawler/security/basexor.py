"""
BaseXOR 探针模块

BaseXOR 探针是一个终端 CLI Agent，用于校验分布式区块链数据块（DataBlock）的 CA 签名，
并产出"合法合规矩阵"。

核心能力：
- 基于 CA（证书服务器）签发代码签名证书，对数据块进行签名；
- 使用 BaseXOR 编码（base64 + XOR）封装签名后的数据块清单（manifest）；
- 通过 CertificateVerifier 校验数据块签名与证书链，确认数据块由可信 CA 签发；
- 汇总校验结果生成"合法合规矩阵"（ComplianceMatrix）；
- 提供 APT 联络线（apt 源配置 + .deb 打包），用于向 Aliyun 云 Kali Linux 主机分发探针。

注意：BaseXOR 编码仅用于传输封装，不提供加密安全性；机密性由 AES/GPG 模块保证。
"""

import base64
import hashlib
import json
import secrets
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509

from ai_llm_agent_crawler.security.ca_system import (
    CertificateAuthority,
    CertificateType,
    CertificateVerifier,
)
from ai_llm_agent_crawler.security.datachain_compression import DataBlock
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# BaseXOR 编解码器
# ---------------------------------------------------------------------------


class BaseXORCodec:
    """
    BaseXOR 编解码器

    编码流程：XOR(data, key) -> base64
    解码流程：base64 -> XOR(data, key)

    XOR 密钥默认从 CA 证书指纹派生，保证同一 CA 签发的清单可被该 CA 的探针解码。
    这是一种传输封装编码，不是加密算法。
    """

    MAGIC = b"BX1"  # BaseXOR v1 魔数，用于识别封装格式

    def __init__(self, key: Union[str, bytes]):
        """
        初始化编解码器

        Args:
            key: XOR 密钥（字符串或字节）
        """
        if isinstance(key, str):
            key = key.encode("utf-8")
        if not key:
            raise ValueError("BaseXOR 密钥不能为空")
        self.key = key

    @classmethod
    def from_ca(cls, ca: CertificateAuthority) -> "BaseXORCodec":
        """
        从 CA 证书指纹派生 BaseXOR 密钥

        Args:
            ca: 已初始化的 CA

        Returns:
            BaseXOR 编解码器
        """
        cert = ca._certificate
        if cert is None:
            raise RuntimeError("CA 未初始化")
        fingerprint = hashlib.sha256(
            cert.public_bytes(serialization.Encoding.DER)
        ).hexdigest()
        # 取指纹前 32 字节作为密钥
        return cls(fingerprint[:32])

    @classmethod
    def from_fingerprint(cls, fingerprint: str) -> "BaseXORCodec":
        """从指纹字符串派生密钥"""
        if not fingerprint:
            raise ValueError("指纹不能为空")
        return cls(fingerprint[:32])

    def _xor(self, data: bytes) -> bytes:
        """对数据做 XOR"""
        key_len = len(self.key)
        result = bytearray(len(data))
        for i, b in enumerate(data):
            result[i] = b ^ self.key[i % key_len]
        return bytes(result)

    def encode(self, data: bytes) -> str:
        """
        BaseXOR 编码

        Args:
            data: 原始字节

        Returns:
            BaseXOR 编码字符串（base64 文本）
        """
        # 前缀：魔数 + 密钥指纹（用于校验密钥匹配）
        key_fingerprint = hashlib.sha256(self.key).digest()[:4]
        payload = self.MAGIC + key_fingerprint + self._xor(data)
        return base64.b64encode(payload).decode("ascii")

    def decode(self, encoded: str) -> bytes:
        """
        BaseXOR 解码

        Args:
            encoded: BaseXOR 编码字符串

        Returns:
            原始字节

        Raises:
            ValueError: 格式错误或密钥不匹配
        """
        try:
            payload = base64.b64decode(encoded.encode("ascii"))
        except Exception as exc:
            raise ValueError(f"Base64 解码失败: {exc}") from exc

        if len(payload) < len(self.MAGIC) + 4:
            raise ValueError("BaseXOR 数据过短")

        magic = payload[: len(self.MAGIC)]
        if magic != self.MAGIC:
            raise ValueError(f"BaseXOR 魔数不匹配: 期望 {self.MAGIC!r}, 实际 {magic!r}")

        key_fingerprint = payload[len(self.MAGIC): len(self.MAGIC) + 4]
        expected = hashlib.sha256(self.key).digest()[:4]
        if key_fingerprint != expected:
            raise ValueError("BaseXOR 密钥不匹配（密钥指纹校验失败）")

        xored = payload[len(self.MAGIC) + 4:]
        return self._xor(xored)

    def encode_json(self, obj: Any) -> str:
        """编码 JSON 可序列化对象"""
        return self.encode(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def decode_json(self, encoded: str) -> Any:
        """解码为 JSON 对象"""
        return json.loads(self.decode(encoded).decode("utf-8"))


# ---------------------------------------------------------------------------
# 数据块签名清单
# ---------------------------------------------------------------------------


@dataclass
class SignedBlockManifest:
    """
    已签名的数据块清单

    包含数据块的完整性校验信息与 CA 代码签名证书对该清单的签名。
    可被 BaseXOR 编码后传输。
    """

    block_id: str
    sequence_number: int
    checksum: str  # sha256(block_data)
    algorithm: str = "SHA256"
    signature: str = ""  # base64 编码的签名
    signer_cert_pem: str = ""  # 签名所用代码签名证书（PEM）
    ca_cert_pem: str = ""  # 签发该证书的 CA 证书（PEM），用于离线校验
    timestamp: float = field(default_factory=time.time)
    probe_id: str = ""

    def canonical_message(self) -> bytes:
        """
        计算用于签名/验签的规范化消息

        将 block_id、sequence_number、checksum 绑定，确保签名同时覆盖数据块身份与完整性。
        """
        return f"{self.block_id}:{self.sequence_number}:{self.checksum}".encode("utf-8")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "sequence_number": self.sequence_number,
            "checksum": self.checksum,
            "algorithm": self.algorithm,
            "signature": self.signature,
            "signer_cert_pem": self.signer_cert_pem,
            "ca_cert_pem": self.ca_cert_pem,
            "timestamp": self.timestamp,
            "probe_id": self.probe_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignedBlockManifest":
        return cls(
            block_id=data["block_id"],
            sequence_number=data["sequence_number"],
            checksum=data["checksum"],
            algorithm=data.get("algorithm", "SHA256"),
            signature=data.get("signature", ""),
            signer_cert_pem=data.get("signer_cert_pem", ""),
            ca_cert_pem=data.get("ca_cert_pem", ""),
            timestamp=data.get("timestamp", time.time()),
            probe_id=data.get("probe_id", ""),
        )


# ---------------------------------------------------------------------------
# 合法合规矩阵
# ---------------------------------------------------------------------------


class ComplianceVerdict(Enum):
    """合规判定结果"""

    COMPLIANT = "compliant"  # 合规
    NONCOMPLIANT = "noncompliant"  # 不合规
    UNKNOWN = "unknown"  # 未知/待核验

    @property
    def label_cn(self) -> str:
        return {
            ComplianceVerdict.COMPLIANT: "合规",
            ComplianceVerdict.NONCOMPLIANT: "不合规",
            ComplianceVerdict.UNKNOWN: "待核验",
        }[self]


class ComplianceCheck(str, Enum):
    """合规检查项"""

    BLOCK_CHECKSUM = "block_checksum"  # 数据块校验和完整
    CA_SIGNATURE = "ca_signature"  # CA 签名有效
    CERT_CHAIN = "cert_chain"  # 证书链可信
    CERT_NOT_EXPIRED = "cert_not_expired"  # 证书未过期
    CERT_NOT_REVOKED = "cert_not_revoked"  # 证书未被吊销
    MANIFEST_INTEGRITY = "manifest_integrity"  # 清单可解码且字段完整

    @property
    def label_cn(self) -> str:
        return {
            ComplianceCheck.BLOCK_CHECKSUM: "数据块校验和",
            ComplianceCheck.CA_SIGNATURE: "CA 签名",
            ComplianceCheck.CERT_CHAIN: "证书链",
            ComplianceCheck.CERT_NOT_EXPIRED: "证书有效期",
            ComplianceCheck.CERT_NOT_REVOKED: "证书吊销状态",
            ComplianceCheck.MANIFEST_INTEGRITY: "清单完整性",
        }[self]


@dataclass
class ComplianceItem:
    """矩阵单个条目：一个数据块在一项检查上的判定"""

    block_id: str
    check: ComplianceCheck
    verdict: ComplianceVerdict
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "check": self.check.value,
            "check_label": self.check.label_cn,
            "verdict": self.verdict.value,
            "verdict_label": self.verdict.label_cn,
            "detail": self.detail,
        }


@dataclass
class ComplianceMatrix:
    """
    合法合规矩阵

    每个数据块对应多个检查项，汇总得到整体合规判定。
    """

    generated_at: float = field(default_factory=time.time)
    ca_subject: str = ""
    probe_id: str = ""
    items: List[ComplianceItem] = field(default_factory=list)

    def add(self, item: ComplianceItem) -> None:
        self.items.append(item)

    def block_verdict(self, block_id: str) -> ComplianceVerdict:
        """聚合单个数据块的总体判定：任一不合规即为不合规"""
        block_items = [i for i in self.items if i.block_id == block_id]
        if not block_items:
            return ComplianceVerdict.UNKNOWN
        if any(i.verdict == ComplianceVerdict.NONCOMPLIANT for i in block_items):
            return ComplianceVerdict.NONCOMPLIANT
        if any(i.verdict == ComplianceVerdict.UNKNOWN for i in block_items):
            return ComplianceVerdict.UNKNOWN
        return ComplianceVerdict.COMPLIANT

    def overall_verdict(self) -> ComplianceVerdict:
        """整体判定"""
        block_ids = {i.block_id for i in self.items}
        verdicts = [self.block_verdict(b) for b in block_ids]
        if not verdicts:
            return ComplianceVerdict.UNKNOWN
        if any(v == ComplianceVerdict.NONCOMPLIANT for v in verdicts):
            return ComplianceVerdict.NONCOMPLIANT
        if any(v == ComplianceVerdict.UNKNOWN for v in verdicts):
            return ComplianceVerdict.UNKNOWN
        return ComplianceVerdict.COMPLIANT

    def to_dict(self) -> Dict[str, Any]:
        block_ids = sorted({i.block_id for i in self.items})
        return {
            "generated_at": datetime.utcfromtimestamp(self.generated_at).isoformat(),
            "ca_subject": self.ca_subject,
            "probe_id": self.probe_id,
            "overall_verdict": self.overall_verdict().value,
            "overall_verdict_label": self.overall_verdict().label_cn,
            "blocks": [
                {
                    "block_id": b,
                    "verdict": self.block_verdict(b).value,
                    "verdict_label": self.block_verdict(b).label_cn,
                    "checks": [i.to_dict() for i in self.items if i.block_id == b],
                }
                for b in block_ids
            ],
        }

    def to_table_rows(self) -> List[Dict[str, str]]:
        """渲染为表格行（供 rich Table / 文本输出使用）"""
        rows: List[Dict[str, str]] = []
        block_ids = sorted({i.block_id for i in self.items})
        for b in block_ids:
            block_items = {i.check: i for i in self.items if i.block_id == b}
            row: Dict[str, str] = {"block_id": b}
            for check in ComplianceCheck:
                item = block_items.get(check)
                if item:
                    row[check.value] = item.verdict.label_cn
                    row[f"{check.value}_detail"] = item.detail
                else:
                    row[check.value] = ComplianceVerdict.UNKNOWN.label_cn
                    row[f"{check.value}_detail"] = ""
            row["verdict"] = self.block_verdict(b).label_cn
            rows.append(row)
        return rows


# ---------------------------------------------------------------------------
# BaseXOR 探针
# ---------------------------------------------------------------------------


@dataclass
class CodeSigningCredential:
    """代码签名凭据：CA 签发的代码签名证书 + 对应私钥（PEM 文本）"""

    cert_pem: str
    private_key_pem: str
    ca_cert_pem: str

    @classmethod
    def issue(cls, ca: CertificateAuthority, common_name: str = "basexor-probe") -> "CodeSigningCredential":
        """由 CA 签发代码签名证书"""
        cert, private_key = ca.issue_certificate(
            subject_name=common_name,
            certificate_type=CertificateType.CODE_SIGNING,
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("ascii")
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        ca_cert_pem = ca.export_ca_certificate("PEM").decode("ascii")
        return cls(cert_pem=cert_pem, private_key_pem=private_key_pem, ca_cert_pem=ca_cert_pem)

    def load_private_key(self) -> rsa.RSAPrivateKey:
        return serialization.load_pem_private_key(
            self.private_key_pem.encode("ascii"),
            password=None,
            backend=default_backend(),
        )

    def load_certificate(self) -> x509.Certificate:
        return x509.load_pem_x509_certificate(
            self.cert_pem.encode("ascii"), default_backend()
        )

    @classmethod
    def load(cls, cert_pem: str, private_key_pem: str, ca_cert_pem: str) -> "CodeSigningCredential":
        return cls(cert_pem=cert_pem, private_key_pem=private_key_pem, ca_cert_pem=ca_cert_pem)

    def to_dict(self) -> Dict[str, str]:
        return {
            "cert_pem": self.cert_pem,
            "private_key_pem": self.private_key_pem,
            "ca_cert_pem": self.ca_cert_pem,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "CodeSigningCredential":
        return cls(
            cert_pem=data["cert_pem"],
            private_key_pem=data["private_key_pem"],
            ca_cert_pem=data["ca_cert_pem"],
        )


class BaseXORProbe:
    """
    BaseXOR 探针 Agent

    负责：
    1. 用 CA 代码签名证书对分布式区块链数据块签名，生成清单并 BaseXOR 编码；
    2. 校验数据块的 CA 签名 / 证书链 / 有效期 / 吊销状态，生成合法合规矩阵；
    3. 暴露 APT 联络线，用于向 Aliyun 云 Kali Linux 主机分发探针。
    """

    def __init__(
        self,
        ca: Optional[CertificateAuthority] = None,
        credential: Optional[CodeSigningCredential] = None,
        probe_id: Optional[str] = None,
    ):
        """
        初始化探针

        Args:
            ca: 已初始化的 CA（用于校验证书链与吊销状态）
            credential: 代码签名凭据（用于签名）。校验模式下可不提供。
            probe_id: 探针实例 ID，未提供则自动生成
        """
        self.ca = ca
        self.credential = credential
        self.probe_id = probe_id or f"bx-{secrets.token_hex(4)}"
        if ca is not None:
            self.codec = BaseXORCodec.from_ca(ca)
        elif credential is not None:
            # 没有 CA 实例时，从 CA 证书指纹派生编解码密钥
            ca_cert = x509.load_pem_x509_certificate(
                credential.ca_cert_pem.encode("ascii"), default_backend()
            )
            fp = hashlib.sha256(
                ca_cert.public_bytes(serialization.Encoding.DER)
            ).hexdigest()
            self.codec = BaseXORCodec.from_fingerprint(fp)
        else:
            # 兜底：随机密钥（仅用于无 CA 场景的编码自测）
            self.codec = BaseXORCodec(secrets.token_hex(16))

    # ---- 签名 ----

    def sign_block(self, block: DataBlock) -> SignedBlockManifest:
        """
        用代码签名证书对数据块签名

        Args:
            block: 待签名的分布式区块链数据块

        Returns:
            已签名的数据块清单
        """
        if self.credential is None:
            raise RuntimeError("探针未配置代码签名凭据，无法签名")

        checksum = hashlib.sha256(block.data).hexdigest()
        manifest = SignedBlockManifest(
            block_id=block.block_id,
            sequence_number=block.sequence_number,
            checksum=checksum,
            algorithm="SHA256",
            signer_cert_pem=self.credential.cert_pem,
            ca_cert_pem=self.credential.ca_cert_pem,
            probe_id=self.probe_id,
        )

        private_key = self.credential.load_private_key()
        signature = private_key.sign(
            manifest.canonical_message(),
            asym_padding.PKCS1v15(),
            hashes.SHA256(),
        )
        manifest.signature = base64.b64encode(signature).decode("ascii")
        logger.info(f"BaseXOR 探针签名数据块: {block.block_id} (seq={block.sequence_number})")
        return manifest

    def encode_manifest(self, manifest: SignedBlockManifest) -> str:
        """BaseXOR 编码已签名清单，用于传输"""
        return self.codec.encode_json(manifest.to_dict())

    def decode_manifest(self, encoded: str) -> SignedBlockManifest:
        """BaseXOR 解码清单"""
        data = self.codec.decode_json(encoded)
        return SignedBlockManifest.from_dict(data)

    # ---- 校验 ----

    def verify_manifest(
        self,
        manifest: SignedBlockManifest,
        block: Optional[DataBlock] = None,
        block_data: Optional[bytes] = None,
    ) -> List[ComplianceItem]:
        """
        校验单个数据块清单，返回若干合规检查项

        Args:
            manifest: 已签名清单
            block: 数据块对象（与 block_data 二选一）
            block_data: 原始数据块字节

        Returns:
            合规检查项列表
        """
        items: List[ComplianceItem] = []
        bid = manifest.block_id

        # 1. 清单完整性
        fields_ok = all(
            getattr(manifest, f, "") != "" or f in ("probe_id",)
            for f in ["block_id", "checksum", "signature", "signer_cert_pem", "ca_cert_pem"]
        )
        items.append(ComplianceItem(
            block_id=bid,
            check=ComplianceCheck.MANIFEST_INTEGRITY,
            verdict=ComplianceVerdict.COMPLIANT if fields_ok else ComplianceVerdict.NONCOMPLIANT,
            detail="清单字段完整" if fields_ok else "清单字段缺失",
        ))

        # 2. 数据块校验和
        if block is not None:
            block_data = block.data
        if block_data is not None:
            actual = hashlib.sha256(block_data).hexdigest()
            ok = actual == manifest.checksum
            items.append(ComplianceItem(
                block_id=bid,
                check=ComplianceCheck.BLOCK_CHECKSUM,
                verdict=ComplianceVerdict.COMPLIANT if ok else ComplianceVerdict.NONCOMPLIANT,
                detail=f"期望 {manifest.checksum[:12]}…, 实际 {actual[:12]}…",
            ))
        else:
            items.append(ComplianceItem(
                block_id=bid,
                check=ComplianceCheck.BLOCK_CHECKSUM,
                verdict=ComplianceVerdict.UNKNOWN,
                detail="未提供数据块，无法核验校验和",
            ))

        # 加载签名证书
        try:
            signer_cert = x509.load_pem_x509_certificate(
                manifest.signer_cert_pem.encode("ascii"), default_backend()
            )
            ca_cert = x509.load_pem_x509_certificate(
                manifest.ca_cert_pem.encode("ascii"), default_backend()
            )
        except Exception as exc:
            items.append(ComplianceItem(
                block_id=bid, check=ComplianceCheck.CERT_CHAIN,
                verdict=ComplianceVerdict.NONCOMPLIANT, detail=f"证书加载失败: {exc}",
            ))
            items.append(ComplianceItem(
                block_id=bid, check=ComplianceCheck.CA_SIGNATURE,
                verdict=ComplianceVerdict.NONCOMPLIANT, detail="证书不可用",
            ))
            items.append(ComplianceItem(
                block_id=bid, check=ComplianceCheck.CERT_NOT_EXPIRED,
                verdict=ComplianceVerdict.UNKNOWN, detail="证书不可用",
            ))
            items.append(ComplianceItem(
                block_id=bid, check=ComplianceCheck.CERT_NOT_REVOKED,
                verdict=ComplianceVerdict.UNKNOWN, detail="证书不可用",
            ))
            return items

        # 3. 证书链（签名证书由 CA 签发）
        verifier = CertificateVerifier([ca_cert])
        chain_ok, chain_reason = verifier.verify_chain(signer_cert)
        items.append(ComplianceItem(
            block_id=bid, check=ComplianceCheck.CERT_CHAIN,
            verdict=ComplianceVerdict.COMPLIANT if chain_ok else ComplianceVerdict.NONCOMPLIANT,
            detail=chain_reason,
        ))

        # 4. 证书有效期
        now = datetime.utcnow()
        not_before = signer_cert.not_valid_before_utc.replace(tzinfo=None)
        not_after = signer_cert.not_valid_after_utc.replace(tzinfo=None)
        if now < not_before:
            verdict = ComplianceVerdict.NONCOMPLIANT
            detail = "证书尚未生效"
        elif now > not_after:
            verdict = ComplianceVerdict.NONCOMPLIANT
            detail = "证书已过期"
        else:
            verdict = ComplianceVerdict.COMPLIANT
            detail = f"有效期至 {not_after.date().isoformat()}"
        items.append(ComplianceItem(
            block_id=bid, check=ComplianceCheck.CERT_NOT_EXPIRED,
            verdict=verdict, detail=detail,
        ))

        # 5. 证书吊销状态
        if self.ca is not None:
            serial = str(signer_cert.serial_number)
            revoked = serial in self.ca._revoked_certificates
            items.append(ComplianceItem(
                block_id=bid, check=ComplianceCheck.CERT_NOT_REVOKED,
                verdict=ComplianceVerdict.NONCOMPLIANT if revoked else ComplianceVerdict.COMPLIANT,
                detail="证书已被吊销" if revoked else "证书未被吊销",
            ))
        else:
            items.append(ComplianceItem(
                block_id=bid, check=ComplianceCheck.CERT_NOT_REVOKED,
                verdict=ComplianceVerdict.UNKNOWN,
                detail="未提供 CA 实例，无法核验吊销状态",
            ))

        # 6. CA 签名
        try:
            signature = base64.b64decode(manifest.signature.encode("ascii"))
            sig_ok = verifier.verify_signature(
                manifest.canonical_message(),
                signature,
                signer_cert,
                manifest.algorithm,
            )
        except Exception as exc:
            sig_ok = False
            detail = f"签名验证异常: {exc}"
        else:
            detail = "CA 签名有效" if sig_ok else "CA 签名无效"
        items.append(ComplianceItem(
            block_id=bid, check=ComplianceCheck.CA_SIGNATURE,
            verdict=ComplianceVerdict.COMPLIANT if sig_ok else ComplianceVerdict.NONCOMPLIANT,
            detail=detail,
        ))

        return items

    def verify_blocks(
        self,
        manifests: List[SignedBlockManifest],
        blocks: Optional[Dict[str, DataBlock]] = None,
    ) -> ComplianceMatrix:
        """
        批量校验数据块清单，生成合法合规矩阵

        Args:
            manifests: 已签名清单列表
            blocks: block_id -> DataBlock 映射，用于校验和核验

        Returns:
            合法合规矩阵
        """
        blocks = blocks or {}
        matrix = ComplianceMatrix(probe_id=self.probe_id)
        if self.ca is not None and self.ca._certificate is not None:
            matrix.ca_subject = self.ca._certificate.subject.rfc4514_string()
        elif manifests:
            try:
                ca_cert = x509.load_pem_x509_certificate(
                    manifests[0].ca_cert_pem.encode("ascii"), default_backend()
                )
                matrix.ca_subject = ca_cert.subject.rfc4514_string()
            except Exception:
                matrix.ca_subject = ""

        for manifest in manifests:
            items = self.verify_manifest(manifest, block=blocks.get(manifest.block_id))
            for item in items:
                matrix.add(item)

        logger.info(
            f"BaseXOR 探针生成合规矩阵: {len(manifests)} 个数据块, "
            f"整体判定={matrix.overall_verdict().label_cn}"
        )
        return matrix


# ---------------------------------------------------------------------------
# 清单信封：自描述的传输/落盘格式
# ---------------------------------------------------------------------------
# {
#   "format": "basexor-v1",
#   "ca_fingerprint": "<sha256(ca_cert_der) hex>",
#   "payload": "<base64(xor(json))>"
# }
# 信封内携带 ca_fingerprint，使接收方无需预共享密钥即可重建编解码器。

MANIFEST_FORMAT = "basexor-v1"


def ca_fingerprint_from_pem(ca_cert_pem: str) -> str:
    """计算 CA 证书指纹（sha256 of DER）"""
    cert = x509.load_pem_x509_certificate(ca_cert_pem.encode("ascii"), default_backend())
    return hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()


def encode_manifest_envelope(manifest: SignedBlockManifest) -> Dict[str, Any]:
    """
    将已签名清单封装为自描述信封（可 JSON 落盘/传输）

    使用 CA 证书指纹派生的 BaseXOR 密钥编码 payload，并将指纹放入信封头部，
    使接收方能独立重建编解码器。
    """
    fingerprint = ca_fingerprint_from_pem(manifest.ca_cert_pem)
    codec = BaseXORCodec.from_fingerprint(fingerprint)
    return {
        "format": MANIFEST_FORMAT,
        "ca_fingerprint": fingerprint,
        "payload": codec.encode_json(manifest.to_dict()),
    }


def decode_manifest_envelope(envelope: Dict[str, Any]) -> SignedBlockManifest:
    """
    从信封解码已签名清单

    Args:
        envelope: 信封字典（含 format / ca_fingerprint / payload）

    Raises:
        ValueError: 格式或指纹不匹配
    """
    fmt = envelope.get("format")
    if fmt != MANIFEST_FORMAT:
        raise ValueError(f"不支持的清单格式: {fmt!r}, 期望 {MANIFEST_FORMAT!r}")
    fingerprint = envelope.get("ca_fingerprint", "")
    if not fingerprint:
        raise ValueError("信封缺少 ca_fingerprint")
    payload = envelope.get("payload", "")
    if not payload:
        raise ValueError("信封缺少 payload")
    codec = BaseXORCodec.from_fingerprint(fingerprint)
    return SignedBlockManifest.from_dict(codec.decode_json(payload))


# ---------------------------------------------------------------------------
# APT 联络线
# ---------------------------------------------------------------------------


@dataclass
class APTContactLine:
    """
    APT 联络线

    描述探针通过 apt 渠道分发到 Aliyun 云 Kali Linux 主机的联络配置：
    - apt 源（sources.list.d）条目
    - 归档签名密钥（GPG keyring）路径
    - 分发组件/发行版

    本类只负责生成与渲染联络配置，不执行特权操作。
    """

    repo_url: str = "https://apt.basexor.example.com"
    distribution: str = "kali"
    component: str = "main"
    keyring_path: str = "/usr/share/keyrings/basexor-archive-keyring.gpg"
    sources_filename: str = "basexor.list"
    sources_dir: str = "/etc/apt/sources.list.d"

    def sources_entry(self) -> str:
        """生成 apt sources.list.d 条目"""
        return (
            f"deb [signed-by={self.keyring_path}] "
            f"{self.repo_url} {self.distribution} {self.component}\n"
        )

    def install_instructions(self) -> str:
        """生成在 Kali 主机上启用联络线的指令"""
        return (
            "# BaseXOR 探针 APT 联络线 - 在 Aliyun 云 Kali Linux 主机上执行\n"
            f"sudo install -d -m 0755 {self.sources_dir}\n"
            f"curl -fsSL {self.repo_url}/basexor-archive-keyring.asc "
            f"| sudo gpg --dearmor -o {self.keyring_path}\n"
            f"echo '{self.sources_entry().strip()}' | sudo tee {self.sources_dir}/{self.sources_filename}\n"
            "sudo apt update\n"
            "sudo apt install basexor-probe\n"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_url": self.repo_url,
            "distribution": self.distribution,
            "component": self.component,
            "keyring_path": self.keyring_path,
            "sources_filename": self.sources_filename,
            "sources_dir": self.sources_dir,
            "sources_entry": self.sources_entry().strip(),
        }


def build_deb_package(
    staging_dir: Union[str, Path],
    output_dir: Union[str, Path],
    package_name: str = "basexor-probe",
    version: str = "0.1.0",
    maintainer: str = "BaseXOR <basexor@example.com>",
    description: str = "BaseXOR 探针 - 分布式区块链数据块 CA 校验终端 CLI",
    entrypoint: str = "basexor",
    run_dpkg: bool = True,
) -> Optional[Path]:
    """
    将探针打包为 .deb 包（APT 联络线的产物）

    在 staging_dir 下构造 Debian 包目录布局，并尝试调用 dpkg-deb 构建。
    若环境中没有 dpkg-deb（非 Debian/Kali 主机），则仅暂存目录并返回 None。

    Args:
        staging_dir: 暂存根目录
        output_dir: .deb 输出目录
        package_name: 包名
        version: 版本
        maintainer: 维护者
        description: 描述
        entrypoint: 可执行入口名
        run_dpkg: 是否真正调用 dpkg-deb 构建

    Returns:
        .deb 文件路径；若未构建则为 None
    """
    staging = Path(staging_dir) / package_name
    if staging.exists():
        # 简单清理重建，避免脏数据
        import shutil
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    # Debian 控制文件
    control_dir = staging / "DEBIAN"
    control_dir.mkdir(parents=True)
    (control_dir / "control").write_text(
        f"Package: {package_name}\n"
        f"Version: {version}\n"
        f"Section: utils\n"
        f"Priority: optional\n"
        f"Architecture: all\n"
        f"Maintainer: {maintainer}\n"
        f"Depends: python3, python3-cryptography, python3-click, python3-rich\n"
        f"Description: {description}\n",
        encoding="utf-8",
    )

    # 入口包装脚本：调用 basexor CLI
    bin_dir = staging / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / entrypoint).write_text(
        "#!/bin/sh\n"
        f'exec python3 -m ai_llm_agent_crawler.cli basexor "$@"\n',
        encoding="utf-8",
    )
    (bin_dir / entrypoint).chmod(0o755)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if not run_dpkg:
        logger.info(f"已暂存 Debian 包目录（未调用 dpkg-deb）: {staging}")
        return None

    # 尝试调用 dpkg-deb 构建
    deb_path = out / f"{package_name}_{version}_all.deb"
    try:
        subprocess.run(
            ["dpkg-deb", "--build", str(staging), str(deb_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"已构建 .deb 包: {deb_path}")
        return deb_path
    except FileNotFoundError:
        logger.warning("未找到 dpkg-deb（非 Debian/Kali 主机），仅保留暂存目录")
        return None
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"dpkg-deb 构建失败: {exc.stderr or exc.stdout or exc}"
        ) from exc


__all__ = [
    "BaseXORCodec",
    "SignedBlockManifest",
    "ComplianceVerdict",
    "ComplianceCheck",
    "ComplianceItem",
    "ComplianceMatrix",
    "CodeSigningCredential",
    "BaseXORProbe",
    "APTContactLine",
    "build_deb_package",
    "MANIFEST_FORMAT",
    "ca_fingerprint_from_pem",
    "encode_manifest_envelope",
    "decode_manifest_envelope",
]
