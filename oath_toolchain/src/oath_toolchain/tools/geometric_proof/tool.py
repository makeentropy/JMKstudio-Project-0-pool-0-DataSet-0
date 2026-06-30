"""几何证据加密主工具模块。

提供几何证据加密工具的统一入口，集成几何哈希、几何证明、
零知识证明和可验证随机函数等功能。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...core.base import OathTool
from ...core.exceptions import ValidationError
from ...core.registry import register_tool
from .geometric_hash import GeometricHash
from .proof_generator import GeometricProof
from .zero_knowledge import ZeroKnowledgeProof
from .vrf import VerifiableRandomFunction


@register_tool
class GeometricProofTool(OathTool):
    """几何证据加密工具。

    集成几何哈希、几何证明、零知识证明和可验证随机函数，
    提供统一的几何证据加密功能接口。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
        _geometric_hash: 几何哈希实例
        _geometric_proof: 几何证明实例
        _zk_proof: 零知识证明实例
        _vrf: 可验证随机函数实例
    """

    name: str = "geometric_proof"
    description: str = "几何证据加密工具"
    _version: str = "0.1.0"
    _tags: list[str] = ["crypto", "geometric", "proof", "zkp", "vrf"]
    _category: str = "crypto"

    def __init__(self) -> None:
        """初始化几何证据加密工具。"""
        super().__init__()
        self._geometric_hash = GeometricHash(dimensions=4, hash_alg='sha256')
        self._geometric_proof = GeometricProof(dimensions=4, hash_alg='sha256')
        self._zk_proof = ZeroKnowledgeProof(security_level=128)
        self._vrf = VerifiableRandomFunction()

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具。

        根据action参数执行不同的几何证据加密操作。

        Args:
            params: 输入参数字典，必须包含action字段
                支持的action:
                - hash: 计算几何哈希
                - hash_to_point: 将数据映射到空间点
                - distance_hash: 计算两个数据的距离哈希
                - geometric_roothash: 计算几何根哈希
                - prove: 生成几何证明
                - verify: 验证几何证明
                - integrity_prove: 生成完整性证明
                - integrity_verify: 验证完整性证明
                - zk_prove: 生成零知识证明
                - zk_verify: 验证零知识证明
                - zk_commit: 生成承诺
                - zk_range_prove: 生成范围证明
                - zk_range_verify: 验证范围证明
                - vrf_gen: 生成VRF密钥对
                - vrf_compute: 计算VRF输出
                - vrf_verify: 验证VRF
                - vrf_random: 生成可验证随机数

        Returns:
            执行结果字典

        Raises:
            ValidationError: 当参数验证失败时
        """
        self.validate_params(params)

        action = params.get('action')

        try:
            if action == 'hash':
                return self._action_hash(params)
            elif action == 'hash_to_point':
                return self._action_hash_to_point(params)
            elif action == 'distance_hash':
                return self._action_distance_hash(params)
            elif action == 'geometric_roothash':
                return self._action_geometric_roothash(params)
            elif action == 'prove':
                return self._action_prove(params)
            elif action == 'verify':
                return self._action_verify(params)
            elif action == 'integrity_prove':
                return self._action_integrity_prove(params)
            elif action == 'integrity_verify':
                return self._action_integrity_verify(params)
            elif action == 'zk_prove':
                return self._action_zk_prove(params)
            elif action == 'zk_verify':
                return self._action_zk_verify(params)
            elif action == 'zk_commit':
                return self._action_zk_commit(params)
            elif action == 'zk_range_prove':
                return self._action_zk_range_prove(params)
            elif action == 'zk_range_verify':
                return self._action_zk_range_verify(params)
            elif action == 'zk_membership_prove':
                return self._action_zk_membership_prove(params)
            elif action == 'zk_membership_verify':
                return self._action_zk_membership_verify(params)
            elif action == 'vrf_gen':
                return self._action_vrf_gen(params)
            elif action == 'vrf_compute':
                return self._action_vrf_compute(params)
            elif action == 'vrf_verify':
                return self._action_vrf_verify(params)
            elif action == 'vrf_random':
                return self._action_vrf_random(params)
            else:
                raise ValidationError(
                    field='action',
                    message=f"不支持的操作: {action}"
                )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                field='execution',
                message=f"执行失败: {str(e)}"
            ) from e

    def validate_params(self, params: dict[str, Any]) -> bool:
        """验证输入参数。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        if 'action' not in params:
            raise ValidationError(
                field='action',
                message="缺少必需的action参数"
            )

        action = params['action']
        valid_actions = [
            'hash', 'hash_to_point', 'distance_hash', 'geometric_roothash',
            'prove', 'verify', 'integrity_prove', 'integrity_verify',
            'zk_prove', 'zk_verify', 'zk_commit',
            'zk_range_prove', 'zk_range_verify',
            'zk_membership_prove', 'zk_membership_verify',
            'vrf_gen', 'vrf_compute', 'vrf_verify', 'vrf_random',
        ]

        if action not in valid_actions:
            raise ValidationError(
                field='action',
                message=f"不支持的操作: {action}"
            )

        return True

    def _action_hash(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行几何哈希操作。"""
        data = self._get_bytes_param(params, 'data')
        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')

        gh = GeometricHash(dimensions=dimensions, hash_alg=hash_alg)
        result = gh.hash_data(data)

        return {
            'success': True,
            'action': 'hash',
            'hash': result.hex(),
            'dimensions': dimensions,
            'hash_alg': hash_alg,
        }

    def _action_hash_to_point(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行哈希到点操作。"""
        data = self._get_bytes_param(params, 'data')
        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')

        gh = GeometricHash(dimensions=dimensions, hash_alg=hash_alg)
        point = gh.hash_to_point(data)

        return {
            'success': True,
            'action': 'hash_to_point',
            'point': point.to_list(),
            'dimensions': dimensions,
        }

    def _action_distance_hash(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行距离哈希操作。"""
        data1 = self._get_bytes_param(params, 'data1')
        data2 = self._get_bytes_param(params, 'data2')
        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')

        gh = GeometricHash(dimensions=dimensions, hash_alg=hash_alg)
        distance = gh.distance_hash(data1, data2)
        cosine_sim = gh.cosine_similarity_hash(data1, data2)

        return {
            'success': True,
            'action': 'distance_hash',
            'euclidean_distance': distance,
            'cosine_similarity': cosine_sim,
        }

    def _action_geometric_roothash(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行几何根哈希操作。"""
        data_blocks = self._get_bytes_list_param(params, 'data_blocks')
        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')

        gh = GeometricHash(dimensions=dimensions, hash_alg=hash_alg)
        root_hash = gh.geometric_roothash(data_blocks)

        return {
            'success': True,
            'action': 'geometric_roothash',
            'root_hash': root_hash.hex(),
            'block_count': len(data_blocks),
        }

    def _action_prove(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行几何证明生成操作。"""
        data = self._get_bytes_param(params, 'data')
        secret = params.get('secret')
        if secret is not None and isinstance(secret, str):
            secret = secret.encode()

        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')
        num_proof_points = params.get('num_proof_points', 8)

        gp = GeometricProof(
            dimensions=dimensions,
            hash_alg=hash_alg,
            num_proof_points=num_proof_points,
        )
        proof = gp.generate_proof(data, secret)

        return {
            'success': True,
            'action': 'prove',
            'proof': proof,
        }

    def _action_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行几何证明验证操作。"""
        data = self._get_bytes_param(params, 'data')
        proof = params.get('proof')
        if not isinstance(proof, dict):
            raise ValidationError(
                field='proof',
                message="proof必须是字典类型"
            )

        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')

        gp = GeometricProof(dimensions=dimensions, hash_alg=hash_alg)
        valid = gp.verify_proof(data, proof)

        return {
            'success': True,
            'action': 'verify',
            'valid': valid,
        }

    def _action_integrity_prove(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行完整性证明生成操作。"""
        data = self._get_bytes_param(params, 'data')
        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')

        gp = GeometricProof(dimensions=dimensions, hash_alg=hash_alg)
        proof = gp.generate_integrity_proof(data)

        return {
            'success': True,
            'action': 'integrity_prove',
            'proof': proof,
        }

    def _action_integrity_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行完整性证明验证操作。"""
        data = self._get_bytes_param(params, 'data')
        proof = params.get('proof')
        if not isinstance(proof, dict):
            raise ValidationError(
                field='proof',
                message="proof必须是字典类型"
            )

        dimensions = params.get('dimensions', 4)
        hash_alg = params.get('hash_alg', 'sha256')

        gp = GeometricProof(dimensions=dimensions, hash_alg=hash_alg)
        valid = gp.verify_integrity_proof(data, proof)

        return {
            'success': True,
            'action': 'integrity_verify',
            'valid': valid,
        }

    def _action_zk_prove(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行零知识证明生成操作。"""
        secret = self._get_bytes_param(params, 'secret')
        statement = self._get_bytes_param(params, 'statement')
        security_level = params.get('security_level', 128)

        zkp = ZeroKnowledgeProof(security_level=security_level)
        proof = zkp.prove_knowledge(secret, statement)

        return {
            'success': True,
            'action': 'zk_prove',
            'proof': proof,
        }

    def _action_zk_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行零知识证明验证操作。"""
        statement = self._get_bytes_param(params, 'statement')
        proof = params.get('proof')
        if not isinstance(proof, dict):
            raise ValidationError(
                field='proof',
                message="proof必须是字典类型"
            )

        security_level = params.get('security_level', 128)

        zkp = ZeroKnowledgeProof(security_level=security_level)
        valid = zkp.verify_knowledge(statement, proof)

        return {
            'success': True,
            'action': 'zk_verify',
            'valid': valid,
        }

    def _action_zk_commit(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行零知识承诺操作。"""
        value = self._get_bytes_param(params, 'value')
        security_level = params.get('security_level', 128)

        zkp = ZeroKnowledgeProof(security_level=security_level)
        commitment = zkp.commit(value)

        return {
            'success': True,
            'action': 'zk_commit',
            'commitment': commitment['commitment'].hex(),
            'randomness': commitment['randomness'].hex(),
        }

    def _action_zk_range_prove(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行范围证明生成操作。"""
        value = params.get('value')
        min_val = params.get('min_val')
        max_val = params.get('max_val')

        if not isinstance(value, int):
            raise ValidationError(field='value', message="value必须是整数")
        if not isinstance(min_val, int):
            raise ValidationError(field='min_val', message="min_val必须是整数")
        if not isinstance(max_val, int):
            raise ValidationError(field='max_val', message="max_val必须是整数")

        security_level = params.get('security_level', 128)
        zkp = ZeroKnowledgeProof(security_level=security_level)
        proof = zkp.prove_range(value, min_val, max_val)

        return {
            'success': True,
            'action': 'zk_range_prove',
            'proof': proof,
        }

    def _action_zk_range_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行范围证明验证操作。"""
        proof = params.get('proof')
        min_val = params.get('min_val')
        max_val = params.get('max_val')

        if not isinstance(proof, dict):
            raise ValidationError(field='proof', message="proof必须是字典类型")
        if not isinstance(min_val, int):
            raise ValidationError(field='min_val', message="min_val必须是整数")
        if not isinstance(max_val, int):
            raise ValidationError(field='max_val', message="max_val必须是整数")

        security_level = params.get('security_level', 128)
        zkp = ZeroKnowledgeProof(security_level=security_level)
        valid = zkp.verify_range(proof, min_val, max_val)

        return {
            'success': True,
            'action': 'zk_range_verify',
            'valid': valid,
        }

    def _action_zk_membership_prove(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行成员证明生成操作。"""
        element = self._get_bytes_param(params, 'element')
        elements = self._get_bytes_list_param(params, 'elements')
        security_level = params.get('security_level', 128)

        zkp = ZeroKnowledgeProof(security_level=security_level)
        proof = zkp.prove_membership(element, elements)

        return {
            'success': True,
            'action': 'zk_membership_prove',
            'proof': proof,
        }

    def _action_zk_membership_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行成员证明验证操作。"""
        element = self._get_bytes_param(params, 'element')
        set_root = self._get_bytes_param(params, 'set_root')
        proof = params.get('proof')
        if not isinstance(proof, dict):
            raise ValidationError(field='proof', message="proof必须是字典类型")

        security_level = params.get('security_level', 128)
        zkp = ZeroKnowledgeProof(security_level=security_level)
        valid = zkp.verify_membership(element, set_root, proof)

        return {
            'success': True,
            'action': 'zk_membership_verify',
            'valid': valid,
        }

    def _action_vrf_gen(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行VRF密钥对生成操作。"""
        vrf = VerifiableRandomFunction()
        private_key, public_key = vrf.generate_keypair()

        return {
            'success': True,
            'action': 'vrf_gen',
            'private_key': private_key.hex(),
            'public_key': public_key.hex(),
        }

    def _action_vrf_compute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行VRF计算操作。"""
        secret_key = self._get_hex_bytes_param(params, 'secret_key')
        input_data = self._get_bytes_param(params, 'input_data')

        vrf = VerifiableRandomFunction()
        output, proof = vrf.compute(secret_key, input_data)

        return {
            'success': True,
            'action': 'vrf_compute',
            'output': output.hex(),
            'proof': proof.hex(),
        }

    def _action_vrf_verify(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行VRF验证操作。"""
        public_key = self._get_hex_bytes_param(params, 'public_key')
        input_data = self._get_bytes_param(params, 'input_data')
        output = self._get_hex_bytes_param(params, 'output')
        proof = self._get_hex_bytes_param(params, 'proof')

        vrf = VerifiableRandomFunction()
        valid = vrf.verify(public_key, input_data, output, proof)

        return {
            'success': True,
            'action': 'vrf_verify',
            'valid': valid,
        }

    def _action_vrf_random(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行VRF随机数生成操作。"""
        secret_key = self._get_hex_bytes_param(params, 'secret_key')
        seed = self._get_bytes_param(params, 'seed')

        vrf = VerifiableRandomFunction()
        random_output = vrf.random_output(secret_key, seed)

        return {
            'success': True,
            'action': 'vrf_random',
            'random_output': random_output.hex(),
        }

    def _get_bytes_param(self, params: dict[str, Any], key: str) -> bytes:
        """获取字节类型参数。

        Args:
            params: 参数字典
            key: 参数名

        Returns:
            字节值

        Raises:
            ValidationError: 当参数不存在或类型错误时
        """
        if key not in params:
            raise ValidationError(field=key, message=f"缺少必需的参数: {key}")

        value = params[key]
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            return value.encode()
        else:
            raise ValidationError(
                field=key,
                message=f"参数{key}必须是bytes或str类型"
            )

    def _get_bytes_list_param(
        self,
        params: dict[str, Any],
        key: str,
    ) -> List[bytes]:
        """获取字节列表类型参数。

        Args:
            params: 参数字典
            key: 参数名

        Returns:
            字节列表

        Raises:
            ValidationError: 当参数不存在或类型错误时
        """
        if key not in params:
            raise ValidationError(field=key, message=f"缺少必需的参数: {key}")

        value = params[key]
        if not isinstance(value, list):
            raise ValidationError(field=key, message=f"参数{key}必须是列表类型")

        result = []
        for item in value:
            if isinstance(item, bytes):
                result.append(item)
            elif isinstance(item, str):
                result.append(item.encode())
            else:
                raise ValidationError(
                    field=key,
                    message=f"参数{key}中的元素必须是bytes或str类型"
                )

        return result

    def _get_hex_bytes_param(self, params: dict[str, Any], key: str) -> bytes:
        """获取十六进制编码的字节参数。

        Args:
            params: 参数字典
            key: 参数名

        Returns:
            解码后的字节

        Raises:
            ValidationError: 当参数不存在或格式错误时
        """
        if key not in params:
            raise ValidationError(field=key, message=f"缺少必需的参数: {key}")

        value = params[key]
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            try:
                return bytes.fromhex(value)
            except ValueError as e:
                raise ValidationError(
                    field=key,
                    message=f"参数{key}不是有效的十六进制字符串: {e}"
                ) from e
        else:
            raise ValidationError(
                field=key,
                message=f"参数{key}必须是bytes或十六进制字符串"
            )
