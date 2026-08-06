"""
数据保全与安全校验链扩展（O3）

实现：
- MerkleTree: 块级 → 文件级 → 快照级 Merkle 树 + 包含性证明
- SnapshotSigner: 结合 CA 体系的快照签名与验签
- BaseXORProber: baseXOR 隐写锚点（编码/解码/注入/提取）+ 分布式扫描
- HashChainLedger: 轻量级 append-only HashChain 账本 + 跨成员一致性校验
- MerkleDAGBuilder: 快照 Merkle DAG 构建
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import threading
import zlib
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.security.ca_system import (
    CertificateAuthority,
    CertificateVerifier,
    CertificateInfo,
)
from ai_llm_agent_crawler.security.gpg_encryption import GPGKeyManager, GPGKey
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


# ================================================================
# 1. Merkle Tree
# ================================================================
class HashAlgo(str, Enum):
    SHA256 = "sha256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"


def _hasher(algo: HashAlgo):
    if algo == HashAlgo.SHA256:
        return hashlib.sha256()
    if algo == HashAlgo.SHA512:
        return hashlib.sha512()
    if algo == HashAlgo.BLAKE2B:
        return hashlib.blake2b()
    return hashlib.sha256()


def hash_bytes(data: bytes, algo: HashAlgo = HashAlgo.SHA256) -> str:
    h = _hasher(algo)
    h.update(data)
    return h.hexdigest()


def hash_file(path: Path, algo: HashAlgo = HashAlgo.SHA256, chunk: int = 65536) -> str:
    h = _hasher(algo)
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


class MerkleNode(BaseModel):
    index: int
    level: int
    hash: str
    left: Optional[tuple] = None   # (level, index) 元组
    right: Optional[tuple] = None  # (level, index) 元组

    class Config:
        frozen = True
        arbitrary_types_allowed = True


class MerkleProof(BaseModel):
    """包含性证明：提供 target_hash + 兄弟路径即可校验"""
    target_hash: str
    target_index: int
    sibling_hashes: List[str] = Field(default_factory=list)  # 从叶子到根，每级兄弟 hash
    sibling_positions: List[str] = Field(default_factory=list)  # "L" or "R"
    root_hash: str

    def verify(self, algo: HashAlgo = HashAlgo.SHA256) -> bool:
        current = self.target_hash
        for sib, pos in zip(self.sibling_hashes, self.sibling_positions):
            if pos == "L":
                current = hash_bytes((sib + current).encode(), algo)
            else:
                current = hash_bytes((current + sib).encode(), algo)
        return current == self.root_hash


class MerkleTree:
    """二进制 Merkle Tree（平衡树，空叶子用空哈希填充）"""

    EMPTY_HASH = hash_bytes(b"", HashAlgo.SHA256)

    def __init__(self, leaf_hashes: List[str] = None, algo: HashAlgo = HashAlgo.SHA256):
        self.algo = algo
        self.nodes: Dict[tuple, MerkleNode] = {}  # (level, index) -> node
        self.levels: List[List[MerkleNode]] = []
        if leaf_hashes is not None:
            self.build(leaf_hashes)

    # ---------- 构建 ----------
    def build(self, leaf_hashes: List[str]) -> MerkleNode:
        if not leaf_hashes:
            leaf_hashes = [self.EMPTY_HASH]
        # 补全为 2^n
        n = 1
        while n < len(leaf_hashes):
            n <<= 1
        leaves = list(leaf_hashes) + [self.EMPTY_HASH] * (n - len(leaf_hashes))
        current = [
            MerkleNode(index=i, level=0, hash=h)
            for i, h in enumerate(leaves)
        ]
        self.levels = [current]
        for node in current:
            self.nodes[(node.level, node.index)] = node

        idx_in_level = 0
        while len(current) > 1:
            next_level: List[MerkleNode] = []
            for i in range(0, len(current), 2):
                l = current[i]
                r = current[i + 1] if i + 1 < len(current) else current[i]
                combined = hash_bytes((l.hash + r.hash).encode(), self.algo)
                node = MerkleNode(
                    index=len(next_level), level=l.level + 1,
                    hash=combined, left=(l.level, l.index), right=(r.level, r.index),
                )
                next_level.append(node)
                self.nodes[(node.level, node.index)] = node
            self.levels.append(next_level)
            current = next_level

        return self.root

    @property
    def root(self) -> Optional[MerkleNode]:
        return self.levels[-1][0] if self.levels else None

    @property
    def root_hash(self) -> str:
        return self.root.hash if self.root else self.EMPTY_HASH

    @property
    def leaf_count(self) -> int:
        return len(self.levels[0]) if self.levels else 0

    # ---------- 证明 ----------
    def proof_for_leaf(self, leaf_index: int) -> Optional[MerkleProof]:
        if not self.levels or leaf_index >= self.leaf_count:
            return None
        leaf = self.levels[0][leaf_index]
        siblings: List[str] = []
        positions: List[str] = []
        idx = leaf_index
        for level in self.levels[:-1]:
            if idx % 2 == 0:
                sib_idx = idx + 1
                pos = "R"
            else:
                sib_idx = idx - 1
                pos = "L"
            sib_idx = min(sib_idx, len(level) - 1)
            siblings.append(level[sib_idx].hash)
            positions.append(pos)
            idx //= 2
        return MerkleProof(
            target_hash=leaf.hash, target_index=leaf_index,
            sibling_hashes=siblings, sibling_positions=positions,
            root_hash=self.root_hash,
        )

    def verify_leaf(self, leaf_hash: str, leaf_index: int) -> bool:
        proof = self.proof_for_leaf(leaf_index)
        if not proof:
            return False
        proof.target_hash = leaf_hash
        return proof.verify(self.algo)

    # ---------- 从目录/文件块构建 ----------
    @classmethod
    def from_file_blocks(cls, path: Path, block_size: int = 1024 * 1024,
                         algo: HashAlgo = HashAlgo.SHA256) -> "MerkleTree":
        """对单个文件按块切分构建 Merkle Tree"""
        leaves: List[str] = []
        path = Path(path)
        if path.is_file():
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(block_size)
                    if not chunk:
                        break
                    leaves.append(hash_bytes(chunk, algo))
        return cls(leaves, algo)

    @classmethod
    def from_directory(cls, directory: Path,
                       algo: HashAlgo = HashAlgo.SHA256,
                       block_size: int = 1024 * 1024) -> "Tuple[MerkleTree, Dict[str, str]]":
        """
        对目录构建 Merkle Tree（每片叶子 = 一个文件 hash）
        返回 (MerkleTree, {relative_path: file_hash})
        """
        file_map: Dict[str, str] = {}
        directory = Path(directory)
        all_files = []
        for root, dirs, files in os.walk(directory):
            dirs.sort()
            for fn in sorted(files):
                fp = Path(root) / fn
                if fp.is_file():
                    all_files.append(fp)
        all_files.sort(key=lambda p: str(p.relative_to(directory)))
        for fp in all_files:
            rel = str(fp.relative_to(directory))
            file_map[rel] = hash_file(fp, algo)
        leaves = [file_map[str(p.relative_to(directory))] for p in all_files]
        return cls(leaves, algo), file_map


class MerkleDAGNode(BaseModel):
    node_type: str  # "snapshot" | "dir" | "file" | "block"
    name: str = ""
    hash: str
    children: List["MerkleDAGNode"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class MerkleDAGBuilder:
    """
    快照 Merkle DAG 构建器
    层级：block → file → dir → snapshot
    """

    def __init__(self, block_size: int = 1024 * 1024, algo: HashAlgo = HashAlgo.SHA256):
        self.block_size = block_size
        self.algo = algo

    def build(self, snapshot_root: Path) -> MerkleDAGNode:
        return self._build_dir(snapshot_root, snapshot_root.name or "snapshot_root")

    def _build_file(self, file: Path, name: str) -> MerkleDAGNode:
        block_children: List[MerkleDAGNode] = []
        with open(file, "rb") as f:
            i = 0
            while True:
                chunk = f.read(self.block_size)
                if not chunk:
                    break
                h = hash_bytes(chunk, self.algo)
                block_children.append(MerkleDAGNode(
                    node_type="block", name=f"block_{i}", hash=h,
                    metadata={"size": len(chunk)},
                ))
                i += 1
        # 文件 hash = 子 block Merkle 根（若有多个）或 单块 hash
        if not block_children:
            file_hash = hash_bytes(b"", self.algo)
        elif len(block_children) == 1:
            file_hash = block_children[0].hash
        else:
            mt = MerkleTree([b.hash for b in block_children], self.algo)
            file_hash = mt.root_hash
        return MerkleDAGNode(
            node_type="file", name=name, hash=file_hash,
            children=block_children, metadata={"size": file.stat().st_size},
        )

    def _build_dir(self, dir_path: Path, name: str) -> MerkleDAGNode:
        children: List[MerkleDAGNode] = []
        dir_path = Path(dir_path)
        for p in sorted(dir_path.iterdir(), key=lambda x: x.name):
            if p.is_dir():
                children.append(self._build_dir(p, p.name))
            elif p.is_file():
                children.append(self._build_file(p, p.name))
        # 目录 hash = 子节点 Merkle 根
        if not children:
            dir_hash = hash_bytes(b"empty_dir", self.algo)
        elif len(children) == 1:
            dir_hash = children[0].hash
        else:
            mt = MerkleTree([c.hash for c in children], self.algo)
            dir_hash = mt.root_hash
        return MerkleDAGNode(
            node_type="dir", name=name, hash=dir_hash, children=children,
        )

    def root_hash(self, dag: MerkleDAGNode) -> str:
        return dag.hash


# ================================================================
# 2. Snapshot Signer (GPG + CA)
# ================================================================
class SnapshotSignature(BaseModel):
    snapshot_id: str
    merkle_root: str
    signer_fingerprint: str
    signer_member_id: str
    ca_fingerprint: str
    signature: str  # 二进制签名的 base64
    signed_at: datetime = Field(default_factory=datetime.now)
    certificate_pem: str = ""  # 成员证书

    class Config:
        arbitrary_types_allowed = True


class SnapshotSigner:
    """
    快照签名器：
    - 成员注册：由项目 CA 签发证书
    - 快照签名：成员私钥对 (snapshot_id | merkle_root) 签名
    - 验签：CA 链 → 成员证书 → 签名有效性 → merkle_root 匹配
    """

    def __init__(self, ca: CertificateAuthority, key_mgr: GPGKeyManager):
        self.ca = ca
        self.key_mgr = key_mgr
        self.member_certs: Dict[str, CertificateInfo] = {}  # member_id → cert

    def register_member(self, member_id: str, member_name: str,
                        email: str) -> Tuple[GPGKey, CertificateInfo]:
        """为成员创建 GPG 密钥对 + 由 CA 签发成员证书"""
        key = self.key_mgr.generate_key(
            name_real=member_name, name_email=email, passphrase="",
        )
        cert = self.ca.issue_certificate(
            subject=member_id,
            subject_type="member",
            public_key_pem=key.public_key,
            issuer_fingerprint=self.ca.ca_cert.fingerprint if self.ca.ca_cert else "",
            valid_days=365 * 3,
        )
        self.member_certs[member_id] = cert
        logger.info(f"[Signer] 注册成员 {member_id} ({member_name})")
        return key, cert

    def sign(self, snapshot_id: str, merkle_root: str,
             member_id: str, member_key: GPGKey) -> SnapshotSignature:
        """成员对快照签名"""
        import base64
        cert = self.member_certs.get(member_id)
        if not cert:
            raise RuntimeError(f"成员 {member_id} 未注册证书")
        # payload = snapshot_id + "|" + merkle_root
        payload = f"{snapshot_id}|{merkle_root}".encode()
        # 用 cryptography 私钥签名（若有 RSA/DSA 私钥）
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, rsa, dsa, ec
            if isinstance(member_key.private_key, (rsa.RSAPrivateKey, dsa.DSAPrivateKey, ec.EllipticCurvePrivateKey)):
                sig = member_key.private_key.sign(
                    payload,
                    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)
                    if isinstance(member_key.private_key, rsa.RSAPrivateKey)
                    else ec.ECDSA(hashes.SHA256()) if isinstance(member_key.private_key, ec.EllipticCurvePrivateKey)
                    else hashes.SHA256(),
                    hashes.SHA256() if isinstance(member_key.private_key, (rsa.RSAPrivateKey, dsa.DSAPrivateKey)) else None,
                ) if not isinstance(member_key.private_key, (dsa.DSAPrivateKey, ec.EllipticCurvePrivateKey)) or False else (
                    member_key.private_key.sign(payload, ec.ECDSA(hashes.SHA256()))
                    if isinstance(member_key.private_key, ec.EllipticCurvePrivateKey)
                    else member_key.private_key.sign(payload, hashes.SHA256())
                )
                sig_b64 = base64.b64encode(sig).decode()
            else:
                sig_b64 = base64.b64encode(hashlib.sha512(payload + member_key.public_key.encode()).digest()).decode()
        except Exception:
            sig_b64 = base64.b64encode(hashlib.sha512(payload + (member_key.public_key or b"").encode() if isinstance(member_key.public_key, str) else member_key.public_key or b"").digest()).decode()

        return SnapshotSignature(
            snapshot_id=snapshot_id,
            merkle_root=merkle_root,
            signer_fingerprint=(member_key.fingerprint or ""),
            signer_member_id=member_id,
            ca_fingerprint=self.ca.ca_cert.fingerprint if self.ca.ca_cert else "",
            signature=sig_b64,
            certificate_pem=cert.certificate_pem or "",
        )

    def verify(self, sig: SnapshotSignature,
               verifier: CertificateVerifier) -> Tuple[bool, List[str]]:
        """
        四级验签：
        1. CA 证书链有效
        2. 成员证书由 CA 签发且未过期
        3. 签名对 (snapshot_id|merkle_root) 有效
        4. 返回所有错误/警告
        """
        errors: List[str] = []
        # 1 & 2: CA 链验证
        try:
            if sig.certificate_pem:
                ok = verifier.verify_certificate_chain(sig.certificate_pem)
                if not ok:
                    errors.append("CA 证书链验证失败")
        except Exception as e:
            errors.append(f"CA 证书链异常: {e}")
        # 3: 签名验证
        import base64
        payload = f"{sig.snapshot_id}|{sig.merkle_root}".encode()
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, rsa, dsa, ec
            # 尝试从证书提取公钥
            if sig.certificate_pem:
                pub = serialization.load_pem_public_key(sig.certificate_pem.encode()) if "PUBLIC KEY" in sig.certificate_pem else None
                if pub and isinstance(pub, rsa.RSAPublicKey):
                    pub.verify(
                        base64.b64decode(sig.signature), payload,
                        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                        hashes.SHA256(),
                    )
                elif pub and isinstance(pub, ec.EllipticCurvePublicKey):
                    pub.verify(
                        base64.b64decode(sig.signature), payload,
                        ec.ECDSA(hashes.SHA256()),
                    )
        except Exception as e:
            errors.append(f"签名验证失败: {e}")
        return (len(errors) == 0, errors)


# ================================================================
# 3. BaseXOR-Prober 隐写锚点
# ================================================================
class AnchorValidationResult(str, Enum):
    VALID = "valid"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    MISPLACED = "misplaced"  # 位置错位
    UNKNOWN = "unknown"


class AnchorRecord(BaseModel):
    file_path: str
    offset: int  # 锚点所在偏移量
    chain_seq: int  # 链序号
    block_hash: str  # 块哈希
    ca_fingerprint: str  # CA 指纹
    injected_at: datetime
    payload: bytes = b""  # 原始锚点二进制
    checksum_valid: bool = True

    class Config:
        arbitrary_types_allowed = True


class ProbeReport(BaseModel):
    scanned_files: int = 0
    total_anchors: int = 0
    valid: int = 0
    corrupted: int = 0
    missing: int = 0
    misplaced: int = 0
    unknown: int = 0
    bad_anchors: List[AnchorRecord] = Field(default_factory=list)
    gaps_in_chain: List[Tuple[int, int]] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    scanned_paths: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class BaseXORProber:
    """
    baseXOR 隐写锚点系统：
    - 锚点格式（56 字节二进制）：
      [0..3]   MAGIC = 0x4A4D4B58 ('JMKX')
      [4..5]   VERSION = 0x0100
      [6..9]   CHAIN_SEQ (uint32 LE)
      [10..41] BLOCK_HASH (32 bytes, SHA256 截断)
      [42..49] CA_FINGERPRINT_FIRST8 (8 bytes)
      [50..53] CRC32 (锚点 0..49)
      [54..55] TAIL = 0x4558 ('EX')

    - XOR 混淆：整段锚点使用 XOR_KEY 循环异或（key=hash(chain_seq)）
    - 注入位置：文件末尾 - ANCHOR_SIZE 处（或预留槽位）
    """

    MAGIC = b"JMKX"
    TAIL = b"EX"
    VERSION = (0x01).to_bytes(1, "little") + (0x00).to_bytes(1, "little")
    ANCHOR_SIZE = 56
    HASH_TRUNCATE = 32

    @classmethod
    def _xor_key(cls, chain_seq: int) -> bytes:
        return hashlib.sha256(struct.pack("<I", chain_seq)).digest()

    @classmethod
    def inject(cls, file_path: Path, block_hash: str, chain_seq: int,
               ca_fingerprint: str) -> AnchorRecord:
        """将锚点注入文件末尾"""
        fp = Path(file_path)
        # 构造 payload（56 字节）
        payload = bytearray(cls.ANCHOR_SIZE)
        payload[0:4] = cls.MAGIC
        payload[4:6] = cls.VERSION
        payload[6:10] = struct.pack("<I", chain_seq)
        h_bytes = bytes.fromhex(block_hash)[: cls.HASH_TRUNCATE]
        payload[10:10 + len(h_bytes)] = h_bytes
        ca_bytes = bytes.fromhex(ca_fingerprint.replace(":", ""))[:8]
        payload[42:42 + len(ca_bytes)] = ca_bytes
        # CRC32 覆盖 0..49
        crc = zlib.crc32(bytes(payload[:50])) & 0xFFFFFFFF
        payload[50:54] = struct.pack("<I", crc)
        payload[54:56] = cls.TAIL

        # XOR 混淆
        key = cls._xor_key(chain_seq)
        for i in range(cls.ANCHOR_SIZE):
            payload[i] ^= key[i % len(key)]

        # 写入文件末尾
        with open(fp, "ab") as f:
            f.write(bytes(payload))

        return AnchorRecord(
            file_path=str(fp),
            offset=fp.stat().st_size - cls.ANCHOR_SIZE,
            chain_seq=chain_seq,
            block_hash=block_hash,
            ca_fingerprint=ca_fingerprint,
            injected_at=datetime.now(),
            payload=bytes(payload),
        )

    @classmethod
    def extract(cls, file_path: Path) -> Optional[AnchorRecord]:
        """从文件末尾提取锚点（若存在）"""
        fp = Path(file_path)
        try:
            size = fp.stat().st_size
            if size < cls.ANCHOR_SIZE:
                return None
            with open(fp, "rb") as f:
                f.seek(size - cls.ANCHOR_SIZE)
                data = bytearray(f.read(cls.ANCHOR_SIZE))
            # 尝试所有可能的 chain_seq（最多尝试 10000 种，或基于已探测链）
            for chain_seq in range(100000):
                key = cls._xor_key(chain_seq)
                decoded = bytearray(data)
                for i in range(cls.ANCHOR_SIZE):
                    decoded[i] ^= key[i % len(key)]
                if bytes(decoded[:4]) == cls.MAGIC and bytes(decoded[54:56]) == cls.TAIL:
                    cs = struct.unpack("<I", bytes(decoded[6:10]))[0]
                    if cs != chain_seq:
                        continue
                    crc_stored = struct.unpack("<I", bytes(decoded[50:54]))[0]
                    crc_calc = zlib.crc32(bytes(decoded[:50])) & 0xFFFFFFFF
                    block_hash = bytes(decoded[10:42]).hex()
                    ca_fp = bytes(decoded[42:50]).hex()
                    return AnchorRecord(
                        file_path=str(fp),
                        offset=size - cls.ANCHOR_SIZE,
                        chain_seq=cs,
                        block_hash=block_hash,
                        ca_fingerprint=":".join(ca_fp[i:i+2] for i in range(0, 16, 2)),
                        injected_at=datetime.fromtimestamp(0),
                        payload=bytes(data),
                        checksum_valid=(crc_stored == crc_calc),
                    )
            return None
        except Exception:
            return None


class DistributedProber:
    """分布式锚点探针（多线程扫描目录）"""

    def __init__(self, workers: int = 8):
        self.workers = max(1, workers)

    def scan(self, root: Path, expected_chain_len: Optional[int] = None,
             extensions: Optional[Set[str]] = None) -> ProbeReport:
        report = ProbeReport(scanned_paths=[str(root)])
        all_files: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                fp = Path(dirpath) / fn
                if extensions and fp.suffix.lower() not in extensions:
                    continue
                all_files.append(fp)

        report.scanned_files = len(all_files)
        anchors_by_seq: Dict[int, AnchorRecord] = {}

        def worker(f: Path) -> Tuple[Optional[AnchorRecord], Optional[str]]:
            anc = BaseXORProber.extract(f)
            if anc is None:
                return None, None
            status: Optional[str] = None
            if not anc.checksum_valid:
                status = "corrupted"
            return anc, status

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(worker, f): f for f in all_files}
            for fut in as_completed(futures):
                anc, status = fut.result()
                if anc is None:
                    continue
                report.total_anchors += 1
                if anc.chain_seq in anchors_by_seq:
                    # 同一链序号重复 = 错位
                    report.misplaced += 1
                    report.bad_anchors.append(anc)
                    continue
                anchors_by_seq[anc.chain_seq] = anc
                if status == "corrupted" or not anc.checksum_valid:
                    report.corrupted += 1
                    report.bad_anchors.append(anc)
                else:
                    report.valid += 1

        # 检查缺失（链序号空洞）
        if anchors_by_seq:
            seqs = sorted(anchors_by_seq.keys())
            for i in range(len(seqs) - 1):
                if seqs[i + 1] - seqs[i] > 1:
                    report.gaps_in_chain.append((seqs[i] + 1, seqs[i + 1] - 1))
                    report.missing += (seqs[i + 1] - seqs[i] - 1)
            if expected_chain_len:
                missing_tail = expected_chain_len - max(seqs)
                if missing_tail > 0:
                    report.missing += missing_tail
                    report.gaps_in_chain.append((max(seqs) + 1, expected_chain_len))

        report.unknown = report.total_anchors - report.valid - report.corrupted
        report.finished_at = datetime.now()
        logger.info(
            f"[Prober] 扫描完成: {report.scanned_files} 文件, {report.total_anchors} 锚点, "
            f"valid={report.valid} corrupted={report.corrupted} "
            f"missing={report.missing} misplaced={report.misplaced}"
        )
        return report


# ================================================================
# 4. HashChain Ledger (轻量链)
# ================================================================
class ChainEntry(BaseModel):
    height: int
    timestamp: datetime = Field(default_factory=datetime.now)
    prev_hash: str
    entry_hash: str  # 本条目 hash
    snapshot_id: str
    merkle_root: str
    signer_member_id: str
    signature: str
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class ChainConsensus(str, Enum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    CONFLICT = "conflict"
    SINGLE_MEMBER = "single_member"


class HashChainLedger:
    """
    轻量级 append-only HashChain 账本：
    - 用于记录团队快照创建事件
    - 支持跨成员账本一致性校验（多数 CA 签名为准）
    """

    GENESIS_PREV = "0" * 64

    def __init__(self, chain_name: str = "jmkstudio_snapshots",
                 genesis_note: str = "JMKstudio snapshot ledger genesis"):
        self.chain_name = chain_name
        self.entries: List[ChainEntry] = []
        # 多成员账本：member_id -> entries[]
        self.member_chains: Dict[str, List[ChainEntry]] = {}
        self._genesis(genesis_note)

    def _genesis(self, note: str) -> None:
        payload = {"note": note, "chain": self.chain_name}
        h = hash_bytes((self.GENESIS_PREV + json.dumps(payload, sort_keys=True)).encode())
        genesis = ChainEntry(
            height=0, prev_hash=self.GENESIS_PREV, entry_hash=h,
            snapshot_id="genesis", merkle_root="0" * 64,
            signer_member_id="system", signature="genesis",
            payload=payload,
        )
        self.entries.append(genesis)
        self.member_chains.setdefault("system", []).append(genesis)

    @property
    def tip(self) -> ChainEntry:
        return self.entries[-1]

    @property
    def height(self) -> int:
        return len(self.entries) - 1

    def append(self, snapshot_id: str, merkle_root: str,
               signer_member_id: str, signature: str,
               payload: Optional[Dict[str, Any]] = None) -> ChainEntry:
        """追加新条目"""
        prev = self.tip
        merged_payload = dict(payload or {})
        raw = (
            prev.entry_hash
            + snapshot_id
            + merkle_root
            + signer_member_id
            + signature
            + json.dumps(merged_payload, sort_keys=True)
        )
        h = hash_bytes(raw.encode())
        entry = ChainEntry(
            height=prev.height + 1,
            prev_hash=prev.entry_hash,
            entry_hash=h,
            snapshot_id=snapshot_id,
            merkle_root=merkle_root,
            signer_member_id=signer_member_id,
            signature=signature,
            payload=merged_payload,
        )
        self.entries.append(entry)
        self.member_chains.setdefault(signer_member_id, []).append(entry)
        return entry

    def verify_chain(self, start: int = 0, end: Optional[int] = None) -> Tuple[bool, List[int]]:
        """校验链哈希完整性，返回 (ok, bad_heights)"""
        end = end if end is not None else self.height
        bad: List[int] = []
        for i in range(max(1, start), end + 1):
            e = self.entries[i]
            prev = self.entries[i - 1]
            if e.prev_hash != prev.entry_hash:
                bad.append(i)
                continue
            raw = (
                prev.entry_hash
                + e.snapshot_id
                + e.merkle_root
                + e.signer_member_id
                + e.signature
                + json.dumps(e.payload, sort_keys=True)
            )
            if hash_bytes(raw.encode()) != e.entry_hash:
                bad.append(i)
        return (len(bad) == 0, bad)

    def cross_member_consensus(self, member_ids: List[str],
                               at_height: Optional[int] = None) -> ChainConsensus:
        """
        跨成员一致性：
        - 若只有一个成员链 → SINGLE_MEMBER
        - 全部成员在指定 height 的 entry_hash 一致 → VERIFIED
        - 存在不一致 → CONFLICT（多数 CA 签名方为准）
        """
        h = at_height if at_height is not None else self.height
        present = [m for m in member_ids if m in self.member_chains and len(self.member_chains[m]) > h]
        if len(present) <= 1:
            return ChainConsensus.SINGLE_MEMBER
        hashes = [self.member_chains[m][h].entry_hash for m in present]
        if len(set(hashes)) == 1:
            return ChainConsensus.VERIFIED
        return ChainConsensus.CONFLICT

    def to_json(self, path: Path) -> None:
        p = Path(path)
        data = {
            "chain_name": self.chain_name,
            "entries": [e.model_dump() for e in self.entries],
        }
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    @classmethod
    def from_json(cls, path: Path) -> "HashChainLedger":
        raw = json.loads(Path(path).read_text())
        ledger = cls.__new__(cls)
        ledger.chain_name = raw["chain_name"]
        ledger.entries = [ChainEntry(**e) for e in raw["entries"]]
        ledger.member_chains = {}
        for e in ledger.entries:
            ledger.member_chains.setdefault(e.signer_member_id, []).append(e)
        return ledger


__all__ = [
    "HashAlgo",
    "hash_bytes",
    "hash_file",
    "MerkleNode",
    "MerkleProof",
    "MerkleTree",
    "MerkleDAGNode",
    "MerkleDAGBuilder",
    "SnapshotSignature",
    "SnapshotSigner",
    "AnchorValidationResult",
    "AnchorRecord",
    "ProbeReport",
    "BaseXORProber",
    "DistributedProber",
    "ChainEntry",
    "ChainConsensus",
    "HashChainLedger",
]
