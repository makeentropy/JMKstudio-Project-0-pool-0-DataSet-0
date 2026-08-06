"""
存储池扩展（O5）：NAS / S3 多后端 + 3 副本复制 + Reed-Solomon (4+2) 纠删码

实现：
- StoragePool: 统一接口（put/get/stat/list/delete/verify/replicate）
- LocalPool / NASNfsPool / NASSmbPool / S3Pool
- ReplicationManager: 3 副本跨池复制
- ReedSolomonCodec: (k+m) 纠删码编解码 + 重建
"""

from __future__ import annotations

import json
import math
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class PoolType(str, Enum):
    LOCAL = "local"
    NAS_NFS = "nas_nfs"
    NAS_SMB = "nas_smb"
    S3 = "s3"


class ObjectInfo(BaseModel):
    key: str
    size_bytes: int
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    etag: str = ""
    metadata: Dict[str, str] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class IntegrityReport(BaseModel):
    total_objects: int = 0
    ok: int = 0
    corrupted: int = 0
    missing: int = 0
    bad_keys: List[str] = Field(default_factory=list)
    finished_at: Optional[datetime] = None


# =========================================================
# StoragePool 抽象
# =========================================================
class StoragePool(ABC):
    pool_type: PoolType = PoolType.LOCAL
    name: str = "default"

    @abstractmethod
    def put(self, key: str, data_or_path, metadata: Optional[Dict[str, str]] = None) -> ObjectInfo: ...

    @abstractmethod
    def get(self, key: str, dest_path: Optional[Path] = None) -> Optional[bytes]: ...

    @abstractmethod
    def stat(self, key: str) -> Optional[ObjectInfo]: ...

    @abstractmethod
    def list(self, prefix: str = "") -> List[ObjectInfo]: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...

    @abstractmethod
    def verify_integrity(self, expected_etags: Dict[str, str] = None) -> IntegrityReport: ...

    @abstractmethod
    def replicate_from(self, src: "StoragePool", key: str) -> bool:
        """从另一个池复制指定对象（跨池副本）"""


# =========================================================
# LocalPool
# =========================================================
class LocalPool(StoragePool):
    pool_type = PoolType.LOCAL

    def __init__(self, root: Path, name: str = "local"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.meta_path = self.root / ".pool_meta.json"
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._load_meta()

    def _keypath(self, key: str) -> Path:
        safe = key.lstrip("/").replace("..", "__")
        return self.root / safe

    def _load_meta(self) -> None:
        if self.meta_path.exists():
            try:
                self._meta = json.loads(self.meta_path.read_text())
            except Exception:
                self._meta = {}

    def _save_meta(self) -> None:
        try:
            self.meta_path.write_text(json.dumps(self._meta, ensure_ascii=False, indent=2, default=str))
        except Exception:
            pass

    def put(self, key: str, data_or_path, metadata: Optional[Dict[str, str]] = None) -> ObjectInfo:
        import hashlib
        p = self._keypath(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data_or_path, (str, Path)):
            shutil.copy2(data_or_path, p)
            data = Path(data_or_path).read_bytes()
        elif isinstance(data_or_path, bytes):
            p.write_bytes(data_or_path)
            data = data_or_path
        elif hasattr(data_or_path, "read"):
            data = data_or_path.read()
            p.write_bytes(data)
        else:
            raise TypeError("data_or_path 必须是 path/bytes/file-like")
        size = p.stat().st_size
        etag = hashlib.sha256(data).hexdigest()
        now = datetime.now()
        self._meta[key] = {
            "size": size, "etag": etag, "metadata": metadata or {},
            "created_at": self._meta.get(key, {}).get("created_at", now.isoformat()),
            "updated_at": now.isoformat(),
        }
        self._save_meta()
        return ObjectInfo(
            key=key, size_bytes=size, etag=etag,
            metadata=metadata or {},
            created_at=datetime.fromisoformat(self._meta[key]["created_at"]),
            updated_at=now,
        )

    def get(self, key: str, dest_path: Optional[Path] = None) -> Optional[bytes]:
        p = self._keypath(key)
        if not p.exists():
            return None
        data = p.read_bytes()
        if dest_path is not None:
            Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
            Path(dest_path).write_bytes(data)
        return data

    def stat(self, key: str) -> Optional[ObjectInfo]:
        p = self._keypath(key)
        if not p.exists():
            return None
        m = self._meta.get(key)
        if not m:
            return ObjectInfo(key=key, size_bytes=p.stat().st_size)
        return ObjectInfo(
            key=key, size_bytes=m["size"], etag=m.get("etag", ""),
            metadata=m.get("metadata", {}),
            created_at=datetime.fromisoformat(m["created_at"]),
            updated_at=datetime.fromisoformat(m["updated_at"]),
        )

    def list(self, prefix: str = "") -> List[ObjectInfo]:
        result: List[ObjectInfo] = []
        for root, dirs, files in os.walk(self.root):
            for fn in files:
                if fn == ".pool_meta.json":
                    continue
                fp = Path(root) / fn
                rel = str(fp.relative_to(self.root))
                if prefix and not rel.startswith(prefix):
                    continue
                st = self.stat(rel)
                if st:
                    result.append(st)
        return result

    def delete(self, key: str) -> bool:
        p = self._keypath(key)
        if p.exists():
            p.unlink()
            self._meta.pop(key, None)
            self._save_meta()
            return True
        return False

    def verify_integrity(self, expected_etags: Dict[str, str] = None) -> IntegrityReport:
        import hashlib
        report = IntegrityReport()
        for obj in self.list():
            report.total_objects += 1
            p = self._keypath(obj.key)
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
            expected = (expected_etags or {}).get(obj.key, obj.etag)
            if expected and actual != expected:
                report.corrupted += 1
                report.bad_keys.append(obj.key)
            else:
                report.ok += 1
        report.finished_at = datetime.now()
        return report

    def replicate_from(self, src: StoragePool, key: str) -> bool:
        data = src.get(key)
        if data is None:
            return False
        st = src.stat(key)
        self.put(key, data, metadata=st.metadata if st else None)
        return True


# =========================================================
# NAS Pool (NFS / SMB 已本地挂载 → 等同 LocalPool 语义)
# =========================================================
class NASNfsPool(LocalPool):
    pool_type = PoolType.NAS_NFS

    def __init__(self, mount_point: Path, name: str = "nas_nfs"):
        if not Path(mount_point).exists():
            logger.warning(f"[NAS NFS] 挂载点不存在: {mount_point}，将使用本地回退目录")
            Path(mount_point).mkdir(parents=True, exist_ok=True)
        super().__init__(mount_point, name=name)

    def _health_check(self) -> bool:
        try:
            test = self.root / ".nfs_write_test"
            test.write_text(str(datetime.now()))
            test.unlink()
            return True
        except Exception as e:
            logger.error(f"[NAS NFS] 健康检查失败: {e}")
            return False


class NASSmbPool(LocalPool):
    pool_type = PoolType.NAS_SMB

    def __init__(self, smb_mount_point: Path, name: str = "nas_smb"):
        super().__init__(smb_mount_point, name=name)


# =========================================================
# S3Pool (boto3 / minio 兼容)
# =========================================================
class S3Pool(StoragePool):
    pool_type = PoolType.S3

    def __init__(self, bucket: str, endpoint: Optional[str] = None,
                 access_key: str = "", secret_key: str = "",
                 region: str = "us-east-1", name: str = "s3"):
        self.name = name
        try:
            import boto3
            self.client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
        except Exception as e:
            raise RuntimeError(f"boto3 初始化失败: {e}")
        self.bucket = bucket

    def put(self, key: str, data_or_path, metadata: Optional[Dict[str, str]] = None) -> ObjectInfo:
        import hashlib
        extra = {"Metadata": metadata} if metadata else {}
        if isinstance(data_or_path, (str, Path)):
            data = Path(data_or_path).read_bytes()
            self.client.upload_file(str(data_or_path), self.bucket, key, ExtraArgs=extra or None)
        elif isinstance(data_or_path, bytes):
            data = data_or_path
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra or {})
        else:
            data = data_or_path.read()
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra or {})
        etag = hashlib.sha256(data).hexdigest()
        size = len(data)
        return ObjectInfo(key=key, size_bytes=size, etag=etag, metadata=metadata or {})

    def get(self, key: str, dest_path: Optional[Path] = None) -> Optional[bytes]:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
            data = resp["Body"].read()
        except Exception as e:
            logger.warning(f"[S3] get {key} 失败: {e}")
            return None
        if dest_path is not None:
            Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
            Path(dest_path).write_bytes(data)
        return data

    def stat(self, key: str) -> Optional[ObjectInfo]:
        try:
            resp = self.client.head_object(Bucket=self.bucket, Key=key)
            return ObjectInfo(
                key=key,
                size_bytes=resp["ContentLength"],
                etag=resp.get("ETag", "").strip('"'),
                metadata=resp.get("Metadata", {}),
                last_modified=resp.get("LastModified"),
            )
        except Exception:
            return None

    def list(self, prefix: str = "") -> List[ObjectInfo]:
        out: List[ObjectInfo] = []
        pag = self.client.get_paginator("list_objects_v2")
        for page in pag.paginate(Bucket=self.bucket, Prefix=prefix or ""):
            for o in page.get("Contents", []):
                out.append(ObjectInfo(
                    key=o["Key"], size_bytes=o["Size"],
                    etag=o.get("ETag", "").strip('"'),
                    created_at=o.get("LastModified", datetime.now()),
                ))
        return out

    def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def verify_integrity(self, expected_etags: Dict[str, str] = None) -> IntegrityReport:
        report = IntegrityReport()
        for obj in self.list():
            report.total_objects += 1
            data = self.get(obj.key)
            if data is None:
                report.missing += 1
                report.bad_keys.append(obj.key)
                continue
            import hashlib
            actual = hashlib.sha256(data).hexdigest()
            expected = (expected_etags or {}).get(obj.key)
            if expected and expected != actual:
                report.corrupted += 1
                report.bad_keys.append(obj.key)
            else:
                report.ok += 1
        report.finished_at = datetime.now()
        return report

    def replicate_from(self, src: StoragePool, key: str) -> bool:
        data = src.get(key)
        if data is None:
            return False
        self.put(key, data, metadata=(src.stat(key).metadata if src.stat(key) else None))
        return True


# =========================================================
# ReplicationManager: 多池副本复制
# =========================================================
class ReplicationResult(BaseModel):
    key: str
    ok: bool
    attempts: int = 0
    error: str = ""
    pool_targets_success: List[str] = Field(default_factory=list)


class ReplicationManager:
    """
    N 副本跨池复制（默认 3 副本）
    - key 写入主池 → 异步分发到 2 个从池
    - 关键数据（元数据/CA链/账本）使用 N=3，普通数据 N=2
    - 提供副本修复：若某池缺失 → 从其他完好副本重建
    """

    def __init__(self, pools: List[StoragePool], primary_index: int = 0, replica_count: int = 3):
        if len(pools) < 1:
            raise ValueError("至少需要一个存储池")
        self.pools = pools
        self.primary = pools[primary_index]
        self.replica_count = replica_count
        self.target_pools = pools[:replica_count]

    def replicate(self, key: str) -> ReplicationResult:
        res = ReplicationResult(key=key, ok=False)
        # 先从主池读
        data = self.primary.get(key)
        if data is None:
            res.error = "主池找不到 key"
            return res
        ok_count = 0
        for pool in self.target_pools:
            res.attempts += 1
            try:
                if pool is self.primary:
                    ok_count += 1
                    res.pool_targets_success.append(pool.name)
                    continue
                pool.put(key, data, metadata=self.primary.stat(key).metadata if self.primary.stat(key) else None)
                st = pool.stat(key)
                if st is not None and st.size_bytes == len(data):
                    ok_count += 1
                    res.pool_targets_success.append(pool.name)
            except Exception as e:
                res.error = f"{pool.name}: {e}"
        res.ok = ok_count >= self.replica_count
        return res

    def repair(self, key: str) -> bool:
        """副本修复：从完好的池写入损坏的池"""
        # 找到一个完好的池
        good_pool: Optional[StoragePool] = None
        for p in self.target_pools:
            st = p.stat(key)
            if st is not None:
                good_pool = p
                break
        if good_pool is None:
            logger.error(f"[RepMgr] 找不到完好副本: {key}")
            return False
        repaired = 0
        for p in self.target_pools:
            if p.stat(key) is None:
                data = good_pool.get(key)
                if data is not None:
                    p.put(key, data)
                    repaired += 1
        logger.info(f"[RepMgr] 修复 {key}: 修复 {repaired} 个副本")
        return True

    def audit_all(self, critical_prefixes: Optional[List[str]] = None) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        total_keys = 0
        replica_counts: Dict[str, int] = {}
        all_keys: set = set()
        for p in self.target_pools:
            for obj in p.list():
                all_keys.add(obj.key)
        for k in sorted(all_keys):
            total_keys += 1
            cnt = sum(1 for p in self.target_pools if p.stat(k) is not None)
            replica_counts[k] = cnt
            is_critical = (
                critical_prefixes is None
                or any(k.startswith(pr) for pr in critical_prefixes)
            )
            need = self.replica_count if is_critical else max(1, self.replica_count - 1)
            if cnt < need:
                issues.append({"key": k, "have": cnt, "need": need, "critical": is_critical})
        return {
            "total_keys": total_keys,
            "replica_counts": replica_counts,
            "issues": issues,
            "pools": [p.name for p in self.target_pools],
        }


# =========================================================
# Reed-Solomon 纠删码（纯 Python 实现，通用 k+m）
# =========================================================
# GF(2^8) 实现，基于指数/对数表
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256


def _init_gf_tables() -> None:
    x = 1
    for i in range(255):
        _GF_EXP[i] = x
        _GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D  # 0x11D: x^8 + x^4 + x^3 + x^2 + 1
    for i in range(255, 512):
        _GF_EXP[i] = _GF_EXP[i - 255]


_init_gf_tables()


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def gf_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError
    if a == 0:
        return 0
    return _GF_EXP[(_GF_LOG[a] - _GF_LOG[b]) % 255]


class ReedSolomonCodec:
    """
    Reed-Solomon 纠删码编码器/解码器（基于 Vandermonde 矩阵）
    默认 k=4 data shards, m=2 parity shards，可容忍任意 2 个 shard 丢失
    """

    def __init__(self, data_shards: int = 4, parity_shards: int = 2):
        self.k = data_shards
        self.m = parity_shards
        self.n = data_shards + parity_shards
        self.enc_matrix = self._build_encoding_matrix()

    # ------- 矩阵工具 -------
    @staticmethod
    def _mat_mul(A, B):
        rA, cA, cB = len(A), len(A[0]), len(B[0])
        C = [[0] * cB for _ in range(rA)]
        for i in range(rA):
            for k_ in range(cA):
                aik = A[i][k_]
                if aik == 0:
                    continue
                for j in range(cB):
                    C[i][j] ^= gf_mul(aik, B[k_][j])
        return C

    @staticmethod
    def _mat_inv(mat):
        n = len(mat)
        aug = [row[:] + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(mat)]
        for c in range(n):
            # 选主元
            piv = -1
            for r in range(c, n):
                if aug[r][c] != 0:
                    piv = r
                    break
            if piv < 0:
                raise ValueError("矩阵不可逆")
            aug[c], aug[piv] = aug[piv], aug[c]
            inv = gf_div(1, aug[c][c])
            for j in range(2 * n):
                aug[c][j] = gf_mul(aug[c][j], inv)
            for r in range(n):
                if r != c and aug[r][c] != 0:
                    f = aug[r][c]
                    for j in range(2 * n):
                        aug[r][j] ^= gf_mul(f, aug[c][j])
        return [row[n:] for row in aug]

    def _build_encoding_matrix(self):
        """Vandermonde: [I; V]，前 k 行单位矩阵"""
        k, m = self.k, self.m
        A = [[0] * k for _ in range(k + m)]
        for i in range(k):
            A[i][i] = 1
        for i in range(m):
            for j in range(k):
                A[k + i][j] = gf_pow(i + 1, j)
        return A

    # ------- 编码 -------
    def encode(self, data: bytes) -> List[bytes]:
        k, n = self.k, self.n
        # pad 到 k 的倍数
        pad_len = (-len(data)) % k
        data_padded = data + bytes(pad_len)
        shard_sz = len(data_padded) // k
        # 切分成 k 个 data shard
        data_shards = [
            bytearray(data_padded[i * shard_sz: (i + 1) * shard_sz])
            for i in range(k)
        ]
        parity_shards = [bytearray(shard_sz) for _ in range(self.m)]
        # 逐字节编码
        for s in range(shard_sz):
            col = [[data_shards[i][s]] for i in range(k)]
            res = self._mat_mul(self.enc_matrix, col)
            for p in range(self.m):
                parity_shards[p][s] = res[k + p][0]
        shards = [bytes(s) for s in data_shards + parity_shards]
        # 元信息：原始长度（写入第 0 shard 开头）
        # 方式：返回 dict 形式更清晰；我们返回 shards 列表 + pad_len 通过属性
        self._last_pad = pad_len
        self._last_len = len(data)
        return shards

    # ------- 解码/重建 -------
    def decode(self, shards: List[Optional[bytes]], original_len: Optional[int] = None) -> Optional[bytes]:
        """
        shards: 长度 n 的列表，缺失项为 None
        original_len: 原始数据字节数（用于去除 padding）
        """
        if len(shards) != self.n:
            raise ValueError(f"需要 {self.n} 个 shards")
        k = self.k
        present_idx = [i for i, s in enumerate(shards) if s is not None]
        if len(present_idx) < k:
            return None
        shard_sz = len(shards[present_idx[0]])
        # 选择子矩阵并求逆
        sub_rows = [self.enc_matrix[i][:] for i in present_idx[:k]]
        inv = self._mat_inv(sub_rows)
        # 逐字节解码
        data_shards = [bytearray(shard_sz) for _ in range(k)]
        picked_shards = [shards[i] for i in present_idx[:k]]
        for s in range(shard_sz):
            col = [[picked_shards[jj][s]] for jj in range(k)]
            decoded = self._mat_mul(inv, col)
            for i in range(k):
                data_shards[i][s] = decoded[i][0]
        data = b"".join(bytes(d) for d in data_shards)
        if original_len is not None and 0 <= original_len <= len(data):
            return data[:original_len]
        # 去掉零填充末尾
        return data.rstrip(b"\x00")

    def reconstruct(self, shards: List[Optional[bytes]]) -> List[bytes]:
        """重建所有缺失的 shards，返回完整的 n 个 shards"""
        k = self.k
        present_idx = [i for i, s in enumerate(shards) if s is not None]
        if len(present_idx) < k:
            raise ValueError("可用 shards < k，无法重建")
        # 先解码得到 data shards
        decoded = self.decode(shards, original_len=None)
        if decoded is None:
            raise ValueError("解码失败")
        # 重新编码
        return self.encode(decoded + b"\x00" * (len(shards[present_idx[0]]) * k - len(decoded)))


def gf_pow(b: int, e: int) -> int:
    r = 1
    cur = b
    while e:
        if e & 1:
            r = gf_mul(r, cur)
        cur = gf_mul(cur, cur)
        e >>= 1
    return r


__all__ = [
    "PoolType",
    "ObjectInfo",
    "IntegrityReport",
    "StoragePool",
    "LocalPool",
    "NASNfsPool",
    "NASSmbPool",
    "S3Pool",
    "ReplicationResult",
    "ReplicationManager",
    "ReedSolomonCodec",
    "gf_mul",
    "gf_div",
]
