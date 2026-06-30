"""几何证明生成与验证模块。

提供基于几何哈希的证明生成与验证功能，包括数据完整性证明、
几何证明点生成和Merkle证明路径验证等。
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ...core.crypto.hash import Hash
from ...core.data_structures.merkle import MerkleTree
from ...core.math.vector import Vector
from .geometric_hash import GeometricHash


class GeometricProof:
    """几何证明类。

    提供基于几何哈希的证明生成与验证功能，包括完整性证明、
    几何证明点生成和Merkle证明路径验证。

    Attributes:
        _geometric_hash: 几何哈希实例
        _hash_alg: 哈希算法名称
        _num_proof_points: 证明点数量
    """

    def __init__(
        self,
        dimensions: int = 4,
        hash_alg: str = 'sha256',
        num_proof_points: int = 8,
    ) -> None:
        """初始化几何证明生成器。

        Args:
            dimensions: 空间维度数，默认为4
            hash_alg: 哈希算法名称，默认为'sha256'
            num_proof_points: 证明点数量，默认为8

        Raises:
            ValueError: 当参数无效时
        """
        if num_proof_points < 1:
            raise ValueError("证明点数量必须大于0")

        self._geometric_hash = GeometricHash(dimensions, hash_alg)
        self._hash_alg = hash_alg
        self._num_proof_points = num_proof_points

    @property
    def dimensions(self) -> int:
        """获取空间维度数。

        Returns:
            维度数
        """
        return self._geometric_hash.dimensions

    @property
    def hash_alg(self) -> str:
        """获取哈希算法名称。

        Returns:
            哈希算法名称
        """
        return self._hash_alg

    @property
    def num_proof_points(self) -> int:
        """获取证明点数量。

        Returns:
            证明点数量
        """
        return self._num_proof_points

    def generate_proof(
        self,
        data: bytes,
        secret: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """生成几何证明。

        生成包含数据哈希、证明点、Merkle路径等信息的几何证明。

        Args:
            data: 待证明的数据
            secret: 可选的秘密值，用于生成签名

        Returns:
            证明字典，包含:
            - data_hash: 数据几何哈希
            - proof_points: 证明点列表（空间点坐标）
            - merkle_path: Merkle证明路径
            - signature: 证明签名（如果提供了secret）
            - timestamp: 时间戳
            - dimensions: 空间维度
        """
        data_hash = self._geometric_hash.hash_data(data)

        proof_points = self._generate_proof_points(data, self._num_proof_points)

        point_hashes = [self._vector_to_hash(p) for p in proof_points]
        point_hashes.insert(0, data_hash)
        merkle_tree = MerkleTree(point_hashes, self._hash_alg)
        merkle_path = merkle_tree.generate_proof(0)

        proof: Dict[str, Any] = {
            'data_hash': data_hash.hex(),
            'proof_points': [p.to_list() for p in proof_points],
            'merkle_path': [h.hex() for h in merkle_path],
            'merkle_root': merkle_tree.root.hex(),
            'timestamp': int(time.time()),
            'dimensions': self.dimensions,
        }

        if secret is not None:
            proof['signature'] = self._sign_proof(proof, secret).hex()

        return proof

    def verify_proof(self, data: bytes, proof: Dict[str, Any]) -> bool:
        """验证几何证明。

        验证数据的几何证明是否有效，包括哈希验证、证明点验证
        和Merkle路径验证。

        Args:
            data: 待验证的数据
            proof: 证明字典

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            data_hash = self._geometric_hash.hash_data(data)
            if data_hash.hex() != proof['data_hash']:
                return False

            proof_points = [Vector(p) for p in proof['proof_points']]
            expected_points = self._generate_proof_points(
                data, len(proof_points)
            )
            for actual, expected in zip(proof_points, expected_points):
                if actual != expected:
                    return False

            point_hashes = [self._vector_to_hash(p) for p in proof_points]
            point_hashes.insert(0, data_hash)

            merkle_path = [bytes.fromhex(h) for h in proof['merkle_path']]
            merkle_root = bytes.fromhex(proof['merkle_root'])

            tree = MerkleTree(point_hashes, self._hash_alg)
            return tree.verify_proof(point_hashes[0], merkle_path, merkle_root, 0)

        except (KeyError, ValueError, IndexError):
            return False

    def generate_integrity_proof(self, data: bytes) -> Dict[str, Any]:
        """生成完整性证明。

        生成数据的完整性证明，包括分块哈希和Merkle根。

        Args:
            data: 待证明的数据

        Returns:
            完整性证明字典
        """
        block_size = 64
        data_blocks = self._split_data(data, block_size)

        block_hashes = [self._geometric_hash.hash_data(b) for b in data_blocks]

        merkle_tree = MerkleTree(block_hashes, self._hash_alg)

        proof: Dict[str, Any] = {
            'data_size': len(data),
            'block_size': block_size,
            'block_count': len(data_blocks),
            'merkle_root': merkle_tree.root.hex(),
            'block_hashes': [h.hex() for h in block_hashes],
            'timestamp': int(time.time()),
        }

        return proof

    def verify_integrity_proof(
        self,
        data: bytes,
        proof: Dict[str, Any],
    ) -> bool:
        """验证完整性证明。

        验证数据完整性证明是否有效。

        Args:
            data: 待验证的数据
            proof: 完整性证明字典

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            if len(data) != proof['data_size']:
                return False

            block_size = proof['block_size']
            data_blocks = self._split_data(data, block_size)

            if len(data_blocks) != proof['block_count']:
                return False

            block_hashes = [
                self._geometric_hash.hash_data(b) for b in data_blocks
            ]
            expected_hashes = [
                bytes.fromhex(h) for h in proof['block_hashes']
            ]

            if len(block_hashes) != len(expected_hashes):
                return False

            for actual, expected in zip(block_hashes, expected_hashes):
                if actual != expected:
                    return False

            merkle_tree = MerkleTree(block_hashes, self._hash_alg)
            return merkle_tree.root.hex() == proof['merkle_root']

        except (KeyError, ValueError, IndexError):
            return False

    def generate_block_proof(
        self,
        data: bytes,
        block_index: int,
    ) -> Dict[str, Any]:
        """生成单个数据块的完整性证明。

        生成指定数据块的Merkle证明路径，用于验证单个块的完整性。

        Args:
            data: 完整数据
            block_index: 数据块索引

        Returns:
            块证明字典

        Raises:
            IndexError: 当块索引超出范围时
        """
        block_size = 64
        data_blocks = self._split_data(data, block_size)

        if block_index < 0 or block_index >= len(data_blocks):
            raise IndexError(
                f"块索引超出范围: {block_index}, 总块数: {len(data_blocks)}"
            )

        block_hashes = [
            self._geometric_hash.hash_data(b) for b in data_blocks
        ]
        merkle_tree = MerkleTree(block_hashes, self._hash_alg)
        merkle_path = merkle_tree.generate_proof(block_index)

        return {
            'block_index': block_index,
            'block_data': data_blocks[block_index].hex(),
            'block_hash': block_hashes[block_index].hex(),
            'merkle_path': [h.hex() for h in merkle_path],
            'merkle_root': merkle_tree.root.hex(),
            'block_count': len(data_blocks),
            'block_size': block_size,
        }

    def verify_block_proof(
        self,
        block_data: bytes,
        block_proof: Dict[str, Any],
    ) -> bool:
        """验证单个数据块的完整性证明。

        Args:
            block_data: 数据块内容
            block_proof: 块证明字典

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            block_hash = self._geometric_hash.hash_data(block_data)
            if block_hash.hex() != block_proof['block_hash']:
                return False

            merkle_path = [
                bytes.fromhex(h) for h in block_proof['merkle_path']
            ]
            merkle_root = bytes.fromhex(block_proof['merkle_root'])
            block_index = block_proof['block_index']

            tree = MerkleTree([block_hash], self._hash_alg)
            return tree.verify_proof(
                block_data, merkle_path, merkle_root, block_index
            )

        except (KeyError, ValueError, IndexError):
            return False

    def _generate_proof_points(
        self,
        data: bytes,
        num_points: int,
    ) -> List[Vector]:
        """生成证明点。

        基于数据生成多个几何证明点，用于构建证明。

        Args:
            data: 输入数据
            num_points: 证明点数量

        Returns:
            证明点向量列表
        """
        points = []
        for i in range(num_points):
            point_data = data + f"_proof_point_{i}".encode()
            point = self._geometric_hash.hash_to_point(point_data)
            points.append(point)
        return points

    def _vector_to_hash(self, vector: Vector) -> bytes:
        """将向量转换为哈希值。

        Args:
            vector: 向量

        Returns:
            哈希值
        """
        import struct

        vec_bytes = bytearray()
        for comp in vector.to_list():
            vec_bytes.extend(struct.pack('>d', comp))
        return self._geometric_hash.hash_data(bytes(vec_bytes))

    def _sign_proof(
        self,
        proof: Dict[str, Any],
        secret: bytes,
    ) -> bytes:
        """对证明进行签名。

        使用HMAC对证明内容进行签名。

        Args:
            proof: 证明字典
            secret: 密钥

        Returns:
            签名字节
        """
        sign_data = self._proof_to_bytes(proof)
        return Hash.hmac(secret, sign_data, self._hash_alg)

    def verify_signature(
        self,
        proof: Dict[str, Any],
        secret: bytes,
    ) -> bool:
        """验证证明签名。

        Args:
            proof: 证明字典（包含signature字段）
            secret: 密钥

        Returns:
            验证通过返回True，否则返回False
        """
        if 'signature' not in proof:
            return False

        try:
            proof_copy = {k: v for k, v in proof.items() if k != 'signature'}
            expected_sig = self._sign_proof(proof_copy, secret)
            actual_sig = bytes.fromhex(proof['signature'])
            return expected_sig == actual_sig
        except (ValueError, KeyError):
            return False

    def _proof_to_bytes(self, proof: Dict[str, Any]) -> bytes:
        """将证明字典序列化为字节。

        Args:
            proof: 证明字典

        Returns:
            序列化后的字节
        """
        result = bytearray()
        result.extend(bytes.fromhex(proof['data_hash']))
        for point in proof['proof_points']:
            import struct
            for comp in point:
                result.extend(struct.pack('>d', comp))
        for h in proof['merkle_path']:
            result.extend(bytes.fromhex(h))
        result.extend(bytes.fromhex(proof['merkle_root']))
        result.extend(proof['timestamp'].to_bytes(8, 'big'))
        result.extend(proof['dimensions'].to_bytes(4, 'big'))
        return bytes(result)

    def _split_data(self, data: bytes, block_size: int) -> List[bytes]:
        """将数据分割成固定大小的块。

        Args:
            data: 输入数据
            block_size: 块大小（字节）

        Returns:
            数据块列表
        """
        if len(data) == 0:
            return [b'']

        blocks = []
        for i in range(0, len(data), block_size):
            blocks.append(data[i:i + block_size])
        return blocks
