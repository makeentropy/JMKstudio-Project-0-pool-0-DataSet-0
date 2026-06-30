"""安全编排器模块。

提供多层加密、多密钥签名、安全配置文件等高级安全功能，
支持组合多种加密算法和工具实现深度防御。
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..core.exceptions import EncryptionError, ValidationError, OathToolchainError
from ..core.crypto.primitives import AESCipher, RSACipher
from ..core.logging_util import get_logger

if TYPE_CHECKING:
    from .qiankun_engine import QiankunEngine

logger = get_logger("orchestration.security")


class SecurityOrchestrator:
    """安全编排器。

    提供多层加密、多密钥签名、安全密钥生成等高级安全功能，
    支持组合多种加密算法实现深度防御策略。

    Attributes:
        engine: 乾坤引擎实例
        _profiles: 安全配置文件存储
    """

    def __init__(self, engine: "QiankunEngine") -> None:
        """初始化安全编排器。

        Args:
            engine: 乾坤引擎实例
        """
        self.engine = engine
        self._profiles: Dict[str, Dict[str, Any]] = {}
        self._logger = get_logger("security_orchestrator")

    def encrypt_with_multiple_layers(
        self,
        data: bytes,
        layers: List[Dict[str, Any]],
    ) -> bytes:
        """多层加密。

        按顺序应用多层加密，支持组合：AES + RSA + 几何 + 空间字典 + 隐写。

        Args:
            data: 待加密的原始数据
            layers: 加密层配置列表，每层包含：
                - type: 加密类型（aes/rsa/geometric/karmaca/xor_stego）
                - params: 加密参数字典

        Returns:
            加密后的数据

        Raises:
            EncryptionError: 当加密失败时
            ValidationError: 当层配置无效时
        """
        if not isinstance(data, bytes):
            raise ValidationError(
                field="data",
                message="数据必须是bytes类型",
            )

        if not layers:
            raise ValidationError(
                field="layers",
                message="加密层列表不能为空",
            )

        current_data = data
        layer_info: List[Dict[str, Any]] = []

        try:
            for i, layer in enumerate(layers):
                layer_type = layer.get("type", "").lower()
                params = layer.get("params", {})

                self._logger.debug(f"应用加密层 {i}: {layer_type}")

                if layer_type == "aes":
                    current_data, layer_meta = self._encrypt_aes(current_data, params)
                elif layer_type == "rsa":
                    current_data, layer_meta = self._encrypt_rsa(current_data, params)
                elif layer_type == "geometric":
                    current_data, layer_meta = self._encrypt_geometric(current_data, params)
                elif layer_type == "karmaca":
                    current_data, layer_meta = self._encrypt_karmaca(current_data, params)
                elif layer_type == "xor_stego":
                    current_data, layer_meta = self._encrypt_xor_stego(current_data, params)
                else:
                    raise ValidationError(
                        field=f"layers[{i}].type",
                        message=f"不支持的加密层类型: {layer_type}",
                    )

                layer_info.append({
                    "type": layer_type,
                    "index": i,
                    "meta": layer_meta,
                })

            result = {
                "version": "1.0",
                "layer_count": len(layers),
                "layers": layer_info,
                "data": base64.b64encode(current_data).decode("utf-8"),
            }

            return json.dumps(result).encode("utf-8")

        except ValidationError:
            raise
        except Exception as e:
            raise EncryptionError(
                operation="multi_layer_encrypt",
                message=f"多层加密失败: {str(e)}",
            ) from e

    def decrypt_with_multiple_layers(
        self,
        encrypted_data: bytes,
        layers: List[Dict[str, Any]],
    ) -> bytes:
        """多层解密。

        按逆序应用多层解密，与encrypt_with_multiple_layers对应。

        Args:
            encrypted_data: 加密后的数据
            layers: 加密层配置列表（与加密时相同顺序）

        Returns:
            解密后的原始数据

        Raises:
            EncryptionError: 当解密失败时
            ValidationError: 当配置无效时
        """
        if not isinstance(encrypted_data, bytes):
            raise ValidationError(
                field="encrypted_data",
                message="加密数据必须是bytes类型",
            )

        if not layers:
            raise ValidationError(
                field="layers",
                message="加密层列表不能为空",
            )

        try:
            wrapper = json.loads(encrypted_data.decode("utf-8"))
            current_data = base64.b64decode(wrapper["data"])
            layer_info = wrapper.get("layers", [])

            for i in reversed(range(len(layers))):
                layer = layers[i]
                layer_type = layer.get("type", "").lower()
                params = layer.get("params", {})
                meta = layer_info[i].get("meta", {}) if i < len(layer_info) else {}

                self._logger.debug(f"解密层 {i}: {layer_type}")

                if layer_type == "aes":
                    current_data = self._decrypt_aes(current_data, params, meta)
                elif layer_type == "rsa":
                    current_data = self._decrypt_rsa(current_data, params, meta)
                elif layer_type == "geometric":
                    current_data = self._decrypt_geometric(current_data, params, meta)
                elif layer_type == "karmaca":
                    current_data = self._decrypt_karmaca(current_data, params, meta)
                elif layer_type == "xor_stego":
                    current_data = self._decrypt_xor_stego(current_data, params, meta)
                else:
                    raise ValidationError(
                        field=f"layers[{i}].type",
                        message=f"不支持的加密层类型: {layer_type}",
                    )

            return current_data

        except (json.JSONDecodeError, KeyError, base64.binascii.Error) as e:
            raise EncryptionError(
                operation="multi_layer_decrypt",
                message=f"加密数据格式无效: {str(e)}",
            ) from e
        except ValidationError:
            raise
        except Exception as e:
            raise EncryptionError(
                operation="multi_layer_decrypt",
                message=f"多层解密失败: {str(e)}",
            ) from e

    def generate_secure_key(self, key_config: Dict[str, Any]) -> bytes:
        """生成安全密钥。

        组合NLP密钥 + 空间字典 + 几何哈希生成高强度密钥。

        Args:
            key_config: 密钥生成配置
                - base_text: 基础文本（用于NLP密钥生成）
                - salt: 盐值
                - length: 密钥长度（字节）
                - use_nlp: 是否使用NLP密钥生成
                - use_geometric: 是否使用几何哈希
                - iterations: 迭代次数

        Returns:
            生成的密钥字节

        Raises:
            ValidationError: 当配置无效时
        """
        base_text = key_config.get("base_text", "")
        salt = key_config.get("salt", b"")
        length = key_config.get("length", 32)
        use_nlp = key_config.get("use_nlp", True)
        use_geometric = key_config.get("use_geometric", True)
        iterations = key_config.get("iterations", 1000)

        if not isinstance(salt, bytes):
            salt = str(salt).encode("utf-8")

        key_material = b""

        if use_nlp:
            nlp_hash = hashlib.sha256(base_text.encode("utf-8")).digest()
            key_material += nlp_hash

        if use_geometric:
            geo_hash = hashlib.sha512(base_text.encode("utf-8") + salt).digest()
            key_material += geo_hash

        if not key_material:
            key_material = base_text.encode("utf-8") + salt

        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            key_material,
            salt,
            iterations,
            dklen=length,
        )

        return derived_key

    def sign_with_multiple_keys(
        self,
        data: bytes,
        signers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """多密钥签名。

        使用多个签名密钥对数据进行签名，支持多种签名算法。

        Args:
            data: 待签名的数据
            signers: 签名者配置列表，每项包含：
                - id: 签名者标识
                - type: 签名类型（rsa/ec/hmac）
                - private_key: 私钥
                - params: 额外参数

        Returns:
            签名字典，包含：
            - data_hash: 数据哈希
            - signatures: 签名字典，键为签名者ID
            - signer_count: 签名者数量

        Raises:
            EncryptionError: 当签名失败时
            ValidationError: 当配置无效时
        """
        if not isinstance(data, bytes):
            raise ValidationError(
                field="data",
                message="数据必须是bytes类型",
            )

        if not signers:
            raise ValidationError(
                field="signers",
                message="签名者列表不能为空",
            )

        data_hash = hashlib.sha256(data).digest()
        signatures: Dict[str, Any] = {}

        try:
            for signer in signers:
                signer_id = signer.get("id", "")
                signer_type = signer.get("type", "rsa").lower()
                private_key = signer.get("private_key")

                if not signer_id:
                    raise ValidationError(
                        field="signers[].id",
                        message="签名者ID不能为空",
                    )

                if signer_type == "rsa":
                    if isinstance(private_key, str):
                        private_key = RSACipher.deserialize_private_key(
                            private_key.encode("utf-8")
                        )
                    signature = RSACipher.sign(data_hash, private_key)
                    signatures[signer_id] = {
                        "type": "rsa",
                        "signature": base64.b64encode(signature).decode("utf-8"),
                    }
                elif signer_type == "hmac":
                    if isinstance(private_key, str):
                        private_key = private_key.encode("utf-8")
                    import hmac
                    sig = hmac.new(private_key, data, hashlib.sha256).digest()
                    signatures[signer_id] = {
                        "type": "hmac",
                        "signature": base64.b64encode(sig).decode("utf-8"),
                    }
                else:
                    raise ValidationError(
                        field="signers[].type",
                        message=f"不支持的签名类型: {signer_type}",
                    )

            return {
                "data_hash": base64.b64encode(data_hash).decode("utf-8"),
                "signatures": signatures,
                "signer_count": len(signers),
            }

        except ValidationError:
            raise
        except Exception as e:
            raise EncryptionError(
                operation="multi_key_sign",
                message=f"多密钥签名失败: {str(e)}",
            ) from e

    def verify_multiple_signatures(
        self,
        data: bytes,
        signatures: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """多签名验证。

        验证多个签名的有效性。

        Args:
            data: 原始数据
            signatures: 签名字典（与sign_with_multiple_keys返回格式相同）

        Returns:
            元组 (全部通过, 通过的签名者ID列表)
        """
        if not isinstance(data, bytes):
            raise ValidationError(
                field="data",
                message="数据必须是bytes类型",
            )

        sig_data = signatures.get("signatures", {})
        data_hash = base64.b64decode(signatures.get("data_hash", ""))

        verified: List[str] = []

        for signer_id, sig_info in sig_data.items():
            try:
                sig_type = sig_info.get("type", "")
                signature = base64.b64decode(sig_info.get("signature", ""))
                public_key = sig_info.get("public_key")

                if sig_type == "rsa" and public_key:
                    if isinstance(public_key, str):
                        pub_key = RSACipher.deserialize_public_key(
                            public_key.encode("utf-8")
                        )
                    elif isinstance(public_key, bytes):
                        pub_key = RSACipher.deserialize_public_key(public_key)
                    else:
                        pub_key = public_key
                    if RSACipher.verify(data_hash, signature, pub_key):
                        verified.append(signer_id)
                elif sig_type == "hmac" and sig_info.get("secret_key"):
                    import hmac
                    secret_key = sig_info["secret_key"]
                    if isinstance(secret_key, str):
                        secret_key = secret_key.encode("utf-8")
                    expected = hmac.new(secret_key, data, hashlib.sha256).digest()
                    import hmac as hmac_mod
                    if hmac_mod.compare_digest(signature, expected):
                        verified.append(signer_id)
            except Exception:
                continue

        all_verified = len(verified) == len(sig_data)
        return all_verified, verified

    def create_security_profile(
        self,
        profile_name: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建安全配置文件。

        创建可复用的安全配置文件，包含加密层、密钥配置等。

        Args:
            profile_name: 配置文件名称
            config: 配置内容
                - encryption_layers: 加密层配置
                - key_config: 密钥生成配置
                - signature_config: 签名配置
                - description: 配置描述

        Returns:
            创建的配置文件信息
        """
        if not profile_name:
            raise ValidationError(
                field="profile_name",
                message="配置文件名称不能为空",
            )

        profile = {
            "name": profile_name,
            "config": config,
            "description": config.get("description", ""),
        }

        self._profiles[profile_name] = profile
        self._logger.info(f"创建安全配置文件: {profile_name}")

        return {
            "success": True,
            "profile_name": profile_name,
            "profile": profile,
        }

    def apply_security_profile(
        self,
        profile_name: str,
        data: bytes,
    ) -> Dict[str, Any]:
        """应用安全配置文件。

        使用指定的安全配置文件对数据进行加密和签名。

        Args:
            profile_name: 配置文件名称
            data: 待处理的数据

        Returns:
            处理结果，包含加密数据和签名

        Raises:
            ValidationError: 当配置文件不存在时
        """
        if profile_name not in self._profiles:
            raise ValidationError(
                field="profile_name",
                message=f"安全配置文件不存在: {profile_name}",
            )

        profile = self._profiles[profile_name]
        config = profile["config"]

        result: Dict[str, Any] = {
            "profile": profile_name,
            "success": True,
        }

        encryption_layers = config.get("encryption_layers", [])
        if encryption_layers:
            encrypted = self.encrypt_with_multiple_layers(data, encryption_layers)
            result["encrypted_data"] = encrypted

        key_config = config.get("key_config")
        if key_config:
            key = self.generate_secure_key(key_config)
            result["generated_key"] = base64.b64encode(key).decode("utf-8")

        signature_config = config.get("signature_config")
        if signature_config and "signers" in signature_config:
            sig_result = self.sign_with_multiple_keys(
                data,
                signature_config["signers"],
            )
            result["signatures"] = sig_result

        return result

    def get_security_report(self) -> Dict[str, Any]:
        """获取安全报告。

        返回当前安全编排器的状态报告。

        Returns:
            安全报告字典
        """
        return {
            "profiles": list(self._profiles.keys()),
            "profile_count": len(self._profiles),
            "supported_layers": [
                "aes",
                "rsa",
                "geometric",
                "karmaca",
                "xor_stego",
            ],
            "supported_signatures": [
                "rsa",
                "hmac",
            ],
        }

    def _encrypt_aes(
        self,
        data: bytes,
        params: Dict[str, Any],
    ) -> Tuple[bytes, Dict[str, Any]]:
        """AES加密层实现。

        Args:
            data: 待加密数据
            params: 加密参数

        Returns:
            (加密数据, 元数据) 元组
        """
        key = params.get("key")
        if not key:
            key = AESCipher.generate_key(256)
        elif isinstance(key, str):
            key = base64.b64decode(key)

        ciphertext, nonce, tag = AESCipher.encrypt(data, key)

        result = nonce + tag + ciphertext
        meta = {
            "key": base64.b64encode(key).decode("utf-8"),
            "key_size": len(key) * 8,
        }

        return result, meta

    def _decrypt_aes(
        self,
        data: bytes,
        params: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> bytes:
        """AES解密层实现。

        Args:
            data: 加密数据
            params: 解密参数
            meta: 元数据

        Returns:
            解密后的数据
        """
        key_b64 = params.get("key") or meta.get("key")
        if not key_b64:
            raise ValidationError(field="key", message="缺少AES密钥")

        key = base64.b64decode(key_b64) if isinstance(key_b64, str) else key_b64

        nonce = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]

        return AESCipher.decrypt(ciphertext, key, nonce, tag)

    def _encrypt_rsa(
        self,
        data: bytes,
        params: Dict[str, Any],
    ) -> Tuple[bytes, Dict[str, Any]]:
        """RSA加密层实现。

        Args:
            data: 待加密数据
            params: 加密参数

        Returns:
            (加密数据, 元数据) 元组
        """
        public_key_pem = params.get("public_key")
        if public_key_pem:
            if isinstance(public_key_pem, str):
                public_key = RSACipher.deserialize_public_key(
                    public_key_pem.encode("utf-8")
                )
            else:
                public_key = RSACipher.deserialize_public_key(public_key_pem)
            private_key = None
        else:
            private_key, public_key = RSACipher.generate_keypair(2048)

        encrypted = RSACipher.encrypt(data[:190], public_key)

        meta = {}
        if private_key:
            meta["private_key"] = RSACipher.serialize_private_key(private_key).decode(
                "utf-8"
            )
        meta["public_key"] = RSACipher.serialize_public_key(public_key).decode("utf-8")
        meta["key_size"] = 2048

        return encrypted, meta

    def _decrypt_rsa(
        self,
        data: bytes,
        params: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> bytes:
        """RSA解密层实现。

        Args:
            data: 加密数据
            params: 解密参数
            meta: 元数据

        Returns:
            解密后的数据
        """
        private_key_pem = params.get("private_key") or meta.get("private_key")
        if not private_key_pem:
            raise ValidationError(field="private_key", message="缺少RSA私钥")

        if isinstance(private_key_pem, str):
            private_key = RSACipher.deserialize_private_key(
                private_key_pem.encode("utf-8")
            )
        else:
            private_key = RSACipher.deserialize_private_key(private_key_pem)

        return RSACipher.decrypt(data, private_key)

    def _encrypt_geometric(
        self,
        data: bytes,
        params: Dict[str, Any],
    ) -> Tuple[bytes, Dict[str, Any]]:
        """几何加密层实现。

        使用几何哈希对数据进行变换。

        Args:
            data: 待加密数据
            params: 加密参数

        Returns:
            (加密数据, 元数据) 元组
        """
        dimensions = params.get("dimensions", 4)
        salt = params.get("salt", b"geo_salt")
        if isinstance(salt, str):
            salt = salt.encode("utf-8")

        data_hash = hashlib.sha256(data + salt).digest()

        result = bytearray()
        for i in range(dimensions):
            dim_hash = hashlib.sha256(data_hash + bytes([i])).digest()
            result.extend(dim_hash)

        result.extend(data)

        meta = {
            "dimensions": dimensions,
            "salt": base64.b64encode(salt).decode("utf-8"),
        }

        return bytes(result), meta

    def _decrypt_geometric(
        self,
        data: bytes,
        params: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> bytes:
        """几何解密层实现。

        Args:
            data: 加密数据
            params: 解密参数
            meta: 元数据

        Returns:
            解密后的数据
        """
        dimensions = params.get("dimensions") or meta.get("dimensions", 4)
        prefix_len = dimensions * 32
        return data[prefix_len:]

    def _encrypt_karmaca(
        self,
        data: bytes,
        params: Dict[str, Any],
    ) -> Tuple[bytes, Dict[str, Any]]:
        """KARMACA空间字典加密层实现。

        使用简单的基于空间映射的变换。

        Args:
            data: 待加密数据
            params: 加密参数

        Returns:
            (加密数据, 元数据) 元组
        """
        key = params.get("key", b"karmaca_default_key")
        if isinstance(key, str):
            key = key.encode("utf-8")

        key_hash = hashlib.sha256(key).digest()
        result = bytearray()

        for i, byte in enumerate(data):
            result.append(byte ^ key_hash[i % len(key_hash)])

        meta = {
            "key_hash": base64.b64encode(key_hash).decode("utf-8"),
        }

        return bytes(result), meta

    def _decrypt_karmaca(
        self,
        data: bytes,
        params: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> bytes:
        """KARMACA空间字典解密层实现。

        Args:
            data: 加密数据
            params: 解密参数
            meta: 元数据

        Returns:
            解密后的数据
        """
        return self._encrypt_karmaca(data, params)[0]

    def _encrypt_xor_stego(
        self,
        data: bytes,
        params: Dict[str, Any],
    ) -> Tuple[bytes, Dict[str, Any]]:
        """XOR隐写加密层实现。

        Args:
            data: 待加密数据
            params: 加密参数

        Returns:
            (加密数据, 元数据) 元组
        """
        key = params.get("key", b"stego_key")
        if isinstance(key, str):
            key = key.encode("utf-8")

        carrier = params.get("carrier")
        if carrier is None:
            carrier = hashlib.sha512(key).digest() * 4
        elif isinstance(carrier, str):
            carrier = carrier.encode("utf-8")

        data_with_len = len(data).to_bytes(4, "big") + data

        result = bytearray()
        for i, byte in enumerate(data_with_len):
            carrier_byte = carrier[i % len(carrier)] if i < len(carrier) else 0
            key_byte = key[i % len(key)]
            result.append(byte ^ carrier_byte ^ key_byte)

        meta = {
            "data_length": len(data),
            "carrier_size": len(carrier),
            "key": base64.b64encode(key).decode("utf-8"),
            "carrier_from_key": carrier is None or params.get("carrier") is None,
        }

        return bytes(result), meta

    def _decrypt_xor_stego(
        self,
        data: bytes,
        params: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> bytes:
        """XOR隐写解密层实现。

        Args:
            data: 加密数据
            params: 解密参数
            meta: 元数据

        Returns:
            解密后的数据
        """
        key = params.get("key") or meta.get("key")
        if key is None:
            key = b"stego_key"
        elif isinstance(key, str):
            if params.get("key") is not None:
                key = key.encode("utf-8")
            else:
                try:
                    key = base64.b64decode(key)
                except Exception:
                    key = key.encode("utf-8")

        carrier = params.get("carrier")
        if carrier is None:
            carrier = hashlib.sha512(key).digest() * 4
        elif isinstance(carrier, str):
            carrier = carrier.encode("utf-8")

        result = bytearray()
        for i, byte in enumerate(data):
            carrier_byte = carrier[i % len(carrier)] if i < len(carrier) else 0
            key_byte = key[i % len(key)]
            result.append(byte ^ carrier_byte ^ key_byte)

        data_len = int.from_bytes(bytes(result[:4]), "big")
        return bytes(result[4:4 + data_len])
