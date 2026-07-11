"""分布式区块链编码校验 CA 数据容器。

实现一个轻量级「编码 CA 数据容器」：
- 每条记录（:class:`ChainRecord`）携带 CA 序列号、维度、时钟种子、XOR 密文与哈希；
- 记录之间通过 ``prev_hash`` 形成哈希链（区块链）；
- ``mine_wallet`` 按大模型字典条目挖出对应的编码钱包（轻量 PoW：寻找使哈希前缀
  匹配目标 difficulty 的 nonce）；
- ``verify_chain`` 对整链做分布式校验式解码。

该实现为纯 Python、无外部依赖，适用于审计审查与数据保全场景。
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable


@dataclass
class ChainRecord:
    """区块链编码记录。"""

    index: int
    ca_serial: str
    dimension: str
    clock_seed: int
    ciphertext: bytes
    prev_hash: str
    nonce: int = 0
    timestamp: float = field(default_factory=time.time)
    extra: dict[str, Any] = field(default_factory=dict)
    hash: str = ""

    def compute_hash(self) -> str:
        payload = json.dumps(
            {
                "index": self.index,
                "ca_serial": self.ca_serial,
                "dimension": self.dimension,
                "clock_seed": self.clock_seed,
                "ciphertext": self.ciphertext.hex(),
                "prev_hash": self.prev_hash,
                "nonce": self.nonce,
                "timestamp": self.timestamp,
                "extra": self.extra,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def finalize(self) -> ChainRecord:
        self.hash = self.compute_hash()
        return self

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ciphertext"] = self.ciphertext.hex()
        return d


class BlockchainEncodingContainer:
    """编码 CA 数据容器（区块链）。"""

    def __init__(self, chain_id: str | None = None) -> None:
        self.chain_id: str = chain_id or uuid.uuid4().hex
        self.records: list[ChainRecord] = []
        self._init_genesis()

    # ------------------------------------------------------------------ genesis
    def _init_genesis(self) -> None:
        genesis = ChainRecord(
            index=0,
            ca_serial="genesis",
            dimension="root",
            clock_seed=0,
            ciphertext=b"",
            prev_hash="0" * 64,
            nonce=0,
            timestamp=time.time(),
            extra={"chain_id": self.chain_id},
        )
        genesis.finalize()
        self.records.append(genesis)

    # ------------------------------------------------------------------ append
    def append(
        self,
        ca_serial: str,
        dimension: str,
        clock_seed: int,
        ciphertext: bytes,
        extra: dict[str, Any] | None = None,
    ) -> ChainRecord:
        prev = self.records[-1]
        record = ChainRecord(
            index=prev.index + 1,
            ca_serial=ca_serial,
            dimension=dimension,
            clock_seed=clock_seed,
            ciphertext=ciphertext,
            prev_hash=prev.hash,
            nonce=0,
            extra=extra or {},
        )
        record.finalize()
        self.records.append(record)
        return record

    # ------------------------------------------------------------------ mine
    def mine_wallet(
        self,
        dictionary_entry: str,
        ca_serial: str,
        dimension: str,
        clock_seed: int,
        ciphertext: bytes,
        difficulty: int = 2,
        max_attempts: int = 100_000,
    ) -> ChainRecord:
        """按大模型字典条目挖出对应编码钱包（轻量 PoW）。

        寻找 ``nonce`` 使 ``sha256(dictionary_entry || nonce || ciphertext)`` 的
        十六进制前 ``difficulty`` 位为 '0'。
        """
        target = "0" * difficulty
        base = f"{dictionary_entry}|{ca_serial}|{dimension}|{clock_seed}|".encode("utf-8")
        cipher_hex = ciphertext.hex().encode("utf-8")
        nonce = 0
        while nonce < max_attempts:
            candidate = base + str(nonce).encode("utf-8") + b"|" + cipher_hex
            digest = hashlib.sha256(candidate).hexdigest()
            if digest.startswith(target):
                prev = self.records[-1]
                record = ChainRecord(
                    index=prev.index + 1,
                    ca_serial=ca_serial,
                    dimension=dimension,
                    clock_seed=clock_seed,
                    ciphertext=ciphertext,
                    prev_hash=prev.hash,
                    nonce=nonce,
                    extra={
                        "dictionary_entry": dictionary_entry,
                        "mine_hash": digest,
                        "difficulty": difficulty,
                    },
                )
                record.finalize()
                self.records.append(record)
                return record
            nonce += 1
        raise RuntimeError(f"在 {max_attempts} 次尝试内未挖出 difficulty={difficulty} 的解")

    # ------------------------------------------------------------------ verify
    def verify_chain(self) -> bool:
        """校验整链完整性。"""
        for i, rec in enumerate(self.records):
            if rec.compute_hash() != rec.hash:
                return False
            if i == 0:
                if rec.prev_hash != "0" * 64:
                    return False
            else:
                if rec.prev_hash != self.records[i - 1].hash:
                    return False
        return True

    # ------------------------------------------------------------------ query
    def find_by_ca(self, ca_serial: str) -> list[ChainRecord]:
        return [r for r in self.records if r.ca_serial == ca_serial]

    def find_by_dimension(self, dimension: str) -> list[ChainRecord]:
        return [r for r in self.records if r.dimension == dimension]

    def latest_hash(self) -> str:
        return self.records[-1].hash if self.records else "0" * 64

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "length": len(self.records),
            "records": [r.to_dict() for r in self.records],
            "latest_hash": self.latest_hash(),
        }


def merge_chains(*chains: BlockchainEncodingContainer) -> BlockchainEncodingContainer:
    """分布式合并多个链（按 index 重排，保留各自记录并重建哈希链）。"""
    merged = BlockchainEncodingContainer(chain_id=f"merged-{uuid.uuid4().hex[:8]}")
    for chain in chains:
        for rec in chain.records[1:]:  # 跳过各自的 genesis
            merged.append(
                ca_serial=rec.ca_serial,
                dimension=rec.dimension,
                clock_seed=rec.clock_seed,
                ciphertext=rec.ciphertext,
                extra=rec.extra,
            )
    return merged
