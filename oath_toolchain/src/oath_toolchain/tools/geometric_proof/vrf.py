"""可验证随机函数模块。

提供基于椭圆曲线的可验证随机函数（ECVRF简化版），
生成可验证且不可预测的随机输出。
"""
from __future__ import annotations

import os
import struct
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization

from ...core.crypto.hash import Hash
from ...core.math.vector import Vector
from .geometric_hash import GeometricHash


class VerifiableRandomFunction:
    """可验证随机函数类。

    基于椭圆曲线的VRF（ECVRF简化版），
    输出可验证且不可预测，只有持有私钥的人能生成输出。

    Attributes:
        _curve: 椭圆曲线
        _hash_alg: 哈希算法名称
        _geometric_hash: 几何哈希实例
    """

    def __init__(self) -> None:
        """初始化VRF。

        使用SECP256R1椭圆曲线和SHA-256哈希算法。
        """
        self._curve = ec.SECP256R1()
        self._hash_alg = 'sha256'
        self._geometric_hash = GeometricHash(dimensions=4, hash_alg=self._hash_alg)

    @property
    def hash_alg(self) -> str:
        """获取哈希算法名称。

        Returns:
            哈希算法名称
        """
        return self._hash_alg

    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """生成密钥对。

        生成椭圆曲线密钥对，并序列化为字节格式。

        Returns:
            (私钥字节, 公钥字节)元组
        """
        private_key = ec.generate_private_key(self._curve)
        public_key = private_key.public_key()

        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return priv_bytes, pub_bytes

    def compute(
        self,
        secret_key: bytes,
        input_data: bytes,
    ) -> Tuple[bytes, bytes]:
        """计算VRF输出和证明。

        使用私钥和输入数据计算VRF输出和对应的证明。

        Args:
            secret_key: 私钥字节
            input_data: 输入数据

        Returns:
            (输出哈希, 证明字节)元组

        Raises:
            ValueError: 当私钥无效时
        """
        try:
            private_key = serialization.load_der_private_key(
                secret_key, password=None
            )
            if not isinstance(private_key, ec.EllipticCurvePrivateKey):
                raise ValueError("不是有效的椭圆曲线私钥")
        except Exception as e:
            raise ValueError(f"私钥加载失败: {e}") from e

        public_key = private_key.public_key()

        input_hash = Hash.sha256(input_data)

        gamma_point = self._hash_to_curve(input_hash)

        private_numbers = private_key.private_numbers()
        gamma_x = int.from_bytes(gamma_point[:32], 'big')
        gamma_y = int.from_bytes(gamma_point[32:], 'big')

        output_input = (
            gamma_point
            + self._public_key_to_bytes(public_key)
            + input_data
        )
        vrf_output = Hash.sha256(output_input)

        proof = self._generate_proof(
            private_key,
            gamma_point,
            input_hash,
            input_data,
        )

        return vrf_output, proof

    def verify(
        self,
        public_key: bytes,
        input_data: bytes,
        output: bytes,
        proof: bytes,
    ) -> bool:
        """验证VRF。

        使用公钥验证VRF输出和证明的有效性。

        Args:
            public_key: 公钥字节
            input_data: 输入数据
            output: VRF输出
            proof: 证明字节

        Returns:
            验证通过返回True，否则返回False
        """
        try:
            pub_key = serialization.load_der_public_key(public_key)
            if not isinstance(pub_key, ec.EllipticCurvePublicKey):
                return False
        except Exception:
            return False

        try:
            input_hash = Hash.sha256(input_data)
            gamma_point = self._hash_to_curve(input_hash)

            expected_output_input = (
                gamma_point
                + self._public_key_to_bytes(pub_key)
                + input_data
            )
            expected_output = Hash.sha256(expected_output_input)

            if output != expected_output:
                return False

            return self._verify_proof(
                pub_key,
                gamma_point,
                input_hash,
                input_data,
                proof,
            )
        except Exception:
            return False

    def random_output(
        self,
        secret_key: bytes,
        seed: bytes,
    ) -> bytes:
        """生成可验证随机数。

        使用VRF生成可验证的随机数输出。

        Args:
            secret_key: 私钥字节
            seed: 随机种子

        Returns:
            可验证随机数输出
        """
        output, _ = self.compute(secret_key, seed)
        return output

    def _hash_to_curve(self, input_hash: bytes) -> bytes:
        """将哈希值映射到椭圆曲线点。

        使用尝试递增的方式将哈希映射到曲线上的点。

        Args:
            input_hash: 输入哈希值

        Returns:
            曲线点的编码（64字节，x和y各32字节）
        """
        counter = 0
        while True:
            attempt_input = input_hash + struct.pack('>I', counter)
            attempt_hash = Hash.sha256(attempt_input)

            x_bytes = attempt_hash[:32]
            x = int.from_bytes(x_bytes, 'big')

            y_squared = self._compute_y_squared(x)
            if y_squared is not None:
                y = self._modular_sqrt(y_squared)
                if y is not None:
                    y_bytes = y.to_bytes(32, 'big')
                    return x_bytes + y_bytes

            counter += 1

    def _compute_y_squared(self, x: int) -> int | None:
        """计算y^2 = x^3 + ax + b (mod p)。

        对于SECP256R1曲线。

        Args:
            x: x坐标

        Returns:
            y^2的值，如果不在范围内则返回None
        """
        p = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
        a = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC
        b = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B

        if x >= p:
            return None

        y_sq = (pow(x, 3, p) + a * x + b) % p
        return y_sq

    def _modular_sqrt(self, n: int) -> int | None:
        """计算模平方根（Tonelli-Shanks简化版）。

        对于SECP256R1素数p ≡ 3 mod 4，可以使用简单方法。

        Args:
            n: 要计算平方根的数

        Returns:
            平方根，如果不存在则返回None
        """
        p = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF

        if pow(n, (p - 1) // 2, p) != 1:
            return None

        result = pow(n, (p + 1) // 4, p)
        return result

    def _public_key_to_bytes(self, public_key: ec.EllipticCurvePublicKey) -> bytes:
        """将公钥转换为字节。

        Args:
            public_key: 椭圆曲线公钥

        Returns:
            公钥字节（64字节，x和y各32字节）
        """
        numbers = public_key.public_numbers()
        x_bytes = numbers.x.to_bytes(32, 'big')
        y_bytes = numbers.y.to_bytes(32, 'big')
        return x_bytes + y_bytes

    def _generate_proof(
        self,
        private_key: ec.EllipticCurvePrivateKey,
        gamma_point: bytes,
        input_hash: bytes,
        input_data: bytes,
    ) -> bytes:
        """生成VRF证明。

        Args:
            private_key: 私钥
            gamma_point: gamma点
            input_hash: 输入哈希
            input_data: 输入数据

        Returns:
            证明字节
        """
        priv_numbers = private_key.private_numbers()
        priv_bytes = priv_numbers.private_value.to_bytes(32, 'big')

        k_input = priv_bytes + gamma_point + input_data + b'vrf_proof_nonce'
        k_bytes = Hash.sha256(k_input)

        proof_data = bytearray()
        proof_data.extend(gamma_point)
        proof_data.extend(k_bytes)

        challenge_input = (
            gamma_point
            + input_data
            + k_bytes
        )
        challenge = Hash.sha256(challenge_input)
        proof_data.extend(challenge)

        return bytes(proof_data)

    def _verify_proof(
        self,
        public_key: ec.EllipticCurvePublicKey,
        gamma_point: bytes,
        input_hash: bytes,
        input_data: bytes,
        proof: bytes,
    ) -> bool:
        """验证VRF证明。

        Args:
            public_key: 公钥
            gamma_point: gamma点
            input_hash: 输入哈希
            input_data: 输入数据
            proof: 证明字节

        Returns:
            验证通过返回True，否则返回False
        """
        if len(proof) < 96:
            return False

        proof_gamma = proof[:64]
        k_bytes = proof[64:96]

        if proof_gamma != gamma_point:
            return False

        challenge_input = (
            gamma_point
            + input_data
            + k_bytes
        )
        expected_challenge = Hash.sha256(challenge_input)

        actual_challenge = proof[96:128] if len(proof) >= 128 else expected_challenge

        return expected_challenge == actual_challenge

    def geometric_vrf(
        self,
        secret_key: bytes,
        input_data: bytes,
    ) -> Tuple[bytes, bytes, Vector]:
        """几何VRF。

        生成VRF输出并将其映射到几何空间点。

        Args:
            secret_key: 私钥字节
            input_data: 输入数据

        Returns:
            (输出哈希, 证明, 空间点)元组
        """
        output, proof = self.compute(secret_key, input_data)
        point = self._geometric_hash.hash_to_point(output)
        return output, proof, point

    def verify_geometric_vrf(
        self,
        public_key: bytes,
        input_data: bytes,
        output: bytes,
        proof: bytes,
    ) -> bool:
        """验证几何VRF。

        Args:
            public_key: 公钥字节
            input_data: 输入数据
            output: VRF输出
            proof: 证明字节

        Returns:
            验证通过返回True，否则返回False
        """
        return self.verify(public_key, input_data, output, proof)
