"""零知识证明基础框架模块。

提供基于哈希的承诺方案和简化的零知识证明实现，包括知识证明、
范围证明和成员证明等。
"""
from __future__ import annotations

import os
import struct
from typing import Any, Dict, List, Optional

from ...core.crypto.hash import Hash
from ...core.data_structures.merkle import MerkleTree
from ...core.math.vector import Vector
from .geometric_hash import GeometricHash


class ZeroKnowledgeProof:
    """零知识证明类。

    提供基于哈希的承诺方案和简化的零知识证明实现，
    在不泄露秘密的前提下证明声明的正确性。

    Attributes:
        _security_level: 安全级别（比特）
        _hash_alg: 哈希算法名称
        _geometric_hash: 几何哈希实例
    """

    def __init__(self, security_level: int = 128) -> None:
        """初始化零知识证明。

        Args:
            security_level: 安全级别（比特），默认为128

        Raises:
            ValueError: 当安全级别小于64时
        """
        if security_level < 64:
            raise ValueError("安全级别不能小于64比特")

        self._security_level = security_level
        self._hash_alg = 'sha256' if security_level <= 256 else 'sha512'
        self._geometric_hash = GeometricHash(
            dimensions=4, hash_alg=self._hash_alg
        )

    @property
    def security_level(self) -> int:
        """获取安全级别。

        Returns:
            安全级别（比特）
        """
        return self._security_level

    @property
    def hash_alg(self) -> str:
        """获取哈希算法名称。

        Returns:
            哈希算法名称
        """
        return self._hash_alg

    def commit(self, value: bytes, randomness: Optional[bytes] = None) -> Dict[str, bytes]:
        """生成承诺。

        使用哈希承诺方案，承诺 = H(value || randomness)。

        Args:
            value: 要承诺的值
            randomness: 随机数，如不提供则自动生成

        Returns:
            承诺字典，包含:
            - commitment: 承诺值
            - randomness: 随机数（用于打开承诺）
        """
        if randomness is None:
            randomness = os.urandom(self._security_level // 8)

        commitment = self._hash(value + randomness)

        return {
            'commitment': commitment,
            'randomness': randomness,
        }

    def verify_commitment(
        self,
        value: bytes,
        randomness: bytes,
        commitment: bytes,
    ) -> bool:
        """验证承诺。

        验证值和随机数是否匹配给定的承诺。

        Args:
            value: 声称的值
            randomness: 随机数
            commitment: 承诺值

        Returns:
            验证通过返回True，否则返回False
        """
        expected = self._hash(value + randomness)
        return expected == commitment

    def prove_knowledge(
        self,
        secret: bytes,
        statement: bytes,
    ) -> Dict[str, Any]:
        """证明知道秘密。

        生成一个零知识证明，证明知道满足特定条件的秘密，
        而不泄露秘密本身。使用基于哈希承诺的方案。

        Args:
            secret: 秘密值
            statement: 声明（公开信息）

        Returns:
            证明字典
        """
        secret_hash = self._hash(secret)

        num_rounds = self._security_level // 8
        commitments_a = []
        commitments_b = []
        random_values = []

        for i in range(num_rounds):
            random_value = os.urandom(32)
            random_values.append(random_value)

            commitment_a = self._hash(
                random_value
                + struct.pack('>I', i)
                + b'a'
                + statement
                + secret_hash
            )
            commitment_b_input = self._hash(random_value + secret)
            commitment_b = self._hash(
                commitment_b_input
                + struct.pack('>I', i)
                + b'b'
                + statement
                + secret_hash
            )

            commitments_a.append(commitment_a)
            commitments_b.append(commitment_b)

        challenge_input = (
            statement
            + b''.join(commitments_a)
            + b''.join(commitments_b)
            + secret_hash
        )
        challenge = self._hash(challenge_input)

        responses = []
        for i in range(num_rounds):
            challenge_bit = (challenge[i // 8] >> (i % 8)) & 1

            if challenge_bit == 0:
                response = random_values[i]
            else:
                response = random_values[i] + secret

            responses.append(response)

        return {
            'statement': statement.hex(),
            'secret_hash': secret_hash.hex(),
            'commitments_a': [c.hex() for c in commitments_a],
            'commitments_b': [c.hex() for c in commitments_b],
            'challenge': challenge.hex(),
            'responses': [r.hex() for r in responses],
            'num_rounds': num_rounds,
        }

    def verify_knowledge(
        self,
        statement: bytes,
        proof: Dict[str, Any],
    ) -> bool:
        """验证知识证明。

        验证证明者是否知道满足条件的秘密。

        Args:
            statement: 声明（公开信息）
            proof: 证明字典

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            secret_hash = bytes.fromhex(proof['secret_hash'])
            commitments_a = [bytes.fromhex(c) for c in proof['commitments_a']]
            commitments_b = [bytes.fromhex(c) for c in proof['commitments_b']]
            challenge = bytes.fromhex(proof['challenge'])
            responses = [bytes.fromhex(r) for r in proof['responses']]
            num_rounds = proof['num_rounds']

            if bytes.fromhex(proof['statement']) != statement:
                return False

            expected_challenge_input = (
                statement
                + b''.join(commitments_a)
                + b''.join(commitments_b)
                + secret_hash
            )
            expected_challenge = self._hash(expected_challenge_input)
            if expected_challenge != challenge:
                return False

            for i in range(num_rounds):
                challenge_bit = (challenge[i // 8] >> (i % 8)) & 1
                response = responses[i]

                if challenge_bit == 0:
                    if len(response) != 32:
                        return False
                    random_value = response
                    expected_commitment = self._hash(
                        random_value
                        + struct.pack('>I', i)
                        + b'a'
                        + statement
                        + secret_hash
                    )
                    if expected_commitment != commitments_a[i]:
                        return False
                else:
                    if len(response) <= 32:
                        return False
                    random_value = response[:32]
                    secret_candidate = response[32:]
                    if self._hash(secret_candidate) != secret_hash:
                        return False
                    commitment_b_input = self._hash(random_value + secret_candidate)
                    expected_commitment = self._hash(
                        commitment_b_input
                        + struct.pack('>I', i)
                        + b'b'
                        + statement
                        + secret_hash
                    )
                    if expected_commitment != commitments_b[i]:
                        return False

            return True

        except (KeyError, ValueError, IndexError):
            return False

    def prove_range(
        self,
        value: int,
        min_val: int,
        max_val: int,
    ) -> Dict[str, Any]:
        """范围证明（简化版）。

        证明一个值在指定范围内，而不泄露具体值。
        使用基于承诺和比较的简化实现。

        Args:
            value: 要证明的值
            min_val: 最小值（包含）
            max_val: 最大值（包含）

        Returns:
            范围证明字典

        Raises:
            ValueError: 当值不在范围内时
        """
        if value < min_val or value > max_val:
            raise ValueError("值不在指定范围内")

        value_bytes = value.to_bytes(32, 'big', signed=True)
        min_bytes = min_val.to_bytes(32, 'big', signed=True)
        max_bytes = max_val.to_bytes(32, 'big', signed=True)

        value_commit = self.commit(value_bytes)

        delta_min = value - min_val
        delta_max = max_val - value

        delta_min_bytes = delta_min.to_bytes(32, 'big', signed=True)
        delta_max_bytes = delta_max.to_bytes(32, 'big', signed=True)

        delta_min_commit = self.commit(delta_min_bytes)
        delta_max_commit = self.commit(delta_max_bytes)

        statement = (
            f"range_proof:{min_val}:{max_val}".encode()
        )

        return {
            'statement': statement.hex(),
            'min_val': min_val,
            'max_val': max_val,
            'value_commitment': value_commit['commitment'].hex(),
            'value_randomness': value_commit['randomness'].hex(),
            'delta_min_commitment': delta_min_commit['commitment'].hex(),
            'delta_min_randomness': delta_min_commit['randomness'].hex(),
            'delta_max_commitment': delta_max_commit['commitment'].hex(),
            'delta_max_randomness': delta_max_commit['randomness'].hex(),
        }

    def verify_range(
        self,
        proof: Dict[str, Any],
        min_val: int,
        max_val: int,
    ) -> bool:
        """验证范围证明。

        验证证明的值确实在指定范围内。

        Args:
            proof: 范围证明字典
            min_val: 最小值
            max_val: 最大值

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            if proof['min_val'] != min_val or proof['max_val'] != max_val:
                return False

            value_randomness = bytes.fromhex(proof['value_randomness'])
            value_commitment = bytes.fromhex(proof['value_commitment'])

            delta_min_randomness = bytes.fromhex(proof['delta_min_randomness'])
            delta_min_commitment = bytes.fromhex(proof['delta_min_commitment'])

            delta_max_randomness = bytes.fromhex(proof['delta_max_randomness'])
            delta_max_commitment = bytes.fromhex(proof['delta_max_commitment'])

            value = None
            delta_min = None
            delta_max = None

            for v in range(min_val, max_val + 1):
                v_bytes = v.to_bytes(32, 'big', signed=True)
                dm_bytes = (v - min_val).to_bytes(32, 'big', signed=True)
                dM_bytes = (max_val - v).to_bytes(32, 'big', signed=True)

                if (
                    self.verify_commitment(v_bytes, value_randomness, value_commitment)
                    and self.verify_commitment(dm_bytes, delta_min_randomness, delta_min_commitment)
                    and self.verify_commitment(dM_bytes, delta_max_randomness, delta_max_commitment)
                ):
                    value = v
                    delta_min = v - min_val
                    delta_max = max_val - v
                    break

            if value is None:
                return False

            return delta_min >= 0 and delta_max >= 0

        except (KeyError, ValueError, OverflowError):
            return False

    def prove_membership(
        self,
        element: bytes,
        elements: List[bytes],
    ) -> Dict[str, Any]:
        """成员证明（基于Merkle树）。

        证明某个元素在集合中，而不需要暴露整个集合。

        Args:
            element: 要证明的元素
            elements: 完整集合

        Returns:
            成员证明字典
        """
        merkle_tree = MerkleTree(elements, self._hash_alg)

        element_index = None
        for i, e in enumerate(elements):
            if e == element:
                element_index = i
                break

        if element_index is None:
            raise ValueError("元素不在集合中")

        merkle_proof = merkle_tree.generate_proof(element_index)

        return {
            'element_hash': self._hash(element).hex(),
            'element_index': element_index,
            'merkle_root': merkle_tree.root.hex(),
            'merkle_path': [h.hex() for h in merkle_proof],
            'total_elements': len(elements),
        }

    def verify_membership(
        self,
        element: bytes,
        set_root: bytes,
        proof: Dict[str, Any],
    ) -> bool:
        """验证成员证明。

        验证元素是否在Merkle根表示的集合中。

        Args:
            element: 要验证的元素
            set_root: 集合的Merkle根
            proof: 成员证明字典

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            if proof['merkle_root'] != set_root.hex():
                return False

            merkle_path = [bytes.fromhex(h) for h in proof['merkle_path']]
            element_index = proof['element_index']

            tree = MerkleTree([element], self._hash_alg)
            return tree.verify_proof(
                element, merkle_path, set_root, element_index
            )

        except (KeyError, ValueError, IndexError):
            return False

    def prove_equality(
        self,
        secret1: bytes,
        secret2: bytes,
        statement: bytes,
    ) -> Dict[str, Any]:
        """证明两个秘密相等。

        证明两个秘密值相等，而不泄露秘密本身。

        Args:
            secret1: 第一个秘密
            secret2: 第二个秘密
            statement: 声明

        Returns:
            等式证明字典

        Raises:
            ValueError: 当两个秘密不相等时
        """
        if secret1 != secret2:
            raise ValueError("两个秘密不相等")

        hash1 = self._hash(secret1)
        hash2 = self._hash(secret2)

        commitment = self.commit(secret1)

        return {
            'statement': statement.hex(),
            'hash1': hash1.hex(),
            'hash2': hash2.hex(),
            'commitment': commitment['commitment'].hex(),
            'randomness': commitment['randomness'].hex(),
        }

    def verify_equality(
        self,
        statement: bytes,
        proof: Dict[str, Any],
    ) -> bool:
        """验证等式证明。

        Args:
            statement: 声明
            proof: 等式证明字典

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            if bytes.fromhex(proof['statement']) != statement:
                return False

            if proof['hash1'] != proof['hash2']:
                return False

            return True

        except (KeyError, ValueError):
            return False

    def geometric_prove(
        self,
        secret_point: Vector,
        public_statement: bytes,
    ) -> Dict[str, Any]:
        """几何零知识证明。

        使用几何哈希特性生成零知识证明，
        证明知道映射到特定空间区域的秘密。

        Args:
            secret_point: 秘密空间点
            public_statement: 公开声明

        Returns:
            几何证明字典
        """
        point_hash = self._geometric_hash.hash_data(
            self._vector_to_bytes(secret_point)
        )

        commitment = self.commit(self._vector_to_bytes(secret_point))

        proof_points = []
        for i in range(8):
            offset = self._hash(
                f"offset_{i}".encode() + public_statement
            )
            offset_vec = self._bytes_to_vector(offset, secret_point.dim)
            masked_point = secret_point + offset_vec * 0.1
            proof_points.append(masked_point.to_list())

        return {
            'statement': public_statement.hex(),
            'point_hash': point_hash.hex(),
            'commitment': commitment['commitment'].hex(),
            'randomness': commitment['randomness'].hex(),
            'proof_points': proof_points,
            'dimensions': secret_point.dim,
        }

    def _hash(self, data: bytes) -> bytes:
        """使用指定算法计算哈希。

        Args:
            data: 输入数据

        Returns:
            哈希值
        """
        if self._hash_alg == 'sha256':
            return Hash.sha256(data)
        elif self._hash_alg == 'sha512':
            return Hash.sha512(data)
        else:
            return Hash.sha256(data)

    def _vector_to_bytes(self, vector: Vector) -> bytes:
        """将向量转换为字节。

        Args:
            vector: 向量

        Returns:
            字节表示
        """
        result = bytearray()
        for comp in vector.to_list():
            result.extend(struct.pack('>d', comp))
        return bytes(result)

    def _bytes_to_vector(self, data: bytes, dimensions: int) -> Vector:
        """将字节转换为向量。

        Args:
            data: 字节数据
            dimensions: 维度数

        Returns:
            向量
        """
        components = []
        for i in range(dimensions):
            if (i + 1) * 8 <= len(data):
                value = struct.unpack('>d', data[i * 8:(i + 1) * 8])[0]
                components.append(value)
            else:
                components.append(0.0)
        return Vector(components)
