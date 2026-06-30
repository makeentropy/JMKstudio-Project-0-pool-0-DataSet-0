"""奇点验证器主工具模块。

提供质能质量子奇点验证的主工具类，继承自OathTool并注册到工具注册表。
"""
from __future__ import annotations

import base64
import time
from typing import Any, Dict, Optional

from ...core.base import OathTool
from ...core.exceptions import ValidationError
from ...core.registry import register_tool
from .key_features import KeySingularityFeatures
from .mass_energy import DataMassEnergy
from .singularity_detector import (
    SingularityDetectionResult,
    SingularityDetector,
)


@register_tool
class SingularityVerifier(OathTool):
    """质能质量子奇点验证器。

    基于数据质能模型和奇点检测算法，对数据和密钥进行多维度的
    奇点验证，识别异常模式并生成验证报告。

    Attributes:
        name: 工具名称
        description: 工具描述
        _version: 版本号
        _tags: 标签列表
        _category: 分类
        fast_mode: 是否使用快速模式
    """

    name: str = "singularity_verifier"
    description: str = "质能质量子奇点验证器"
    _version: str = "0.1.0"
    _tags: list[str] = ["verification", "singularity", "mass-energy", "crypto"]
    _category: str = "verification"

    def __init__(self) -> None:
        """初始化奇点验证器。"""
        super().__init__()
        self.fast_mode: bool = False
        self._detector = SingularityDetector()
        self._features = KeySingularityFeatures()

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """执行工具。

        Args:
            params: 输入参数字典
                - action: 操作类型('verify'/'detect'/'features')
                - data: base64编码或字符串数据
                - key: base64编码或字符串密钥
                - mode: 模式('fast'/'full')
                - sensitivity: 检测灵敏度(0-1)

        Returns:
            执行结果字典
                - valid: 是否通过验证
                - score: 验证评分
                - report: 验证报告
                - features: 特征数据

        Raises:
            ValidationError: 当参数验证失败时
        """
        self.validate_params(params)

        action = params.get('action', 'verify')
        mode = params.get('mode', 'full')
        self.fast_mode = (mode == 'fast')

        sensitivity = params.get('sensitivity', 0.8)
        if sensitivity is not None:
            self._detector = SingularityDetector(sensitivity=sensitivity)

        if action == 'verify':
            if 'key' in params:
                key_bytes = self._decode_input(params['key'])
                result = self.verify_key(key_bytes, mode)
                return result
            elif 'data' in params:
                data_bytes = self._decode_input(params['data'])
                result = self.verify_data(data_bytes, mode)
                return result
            else:
                raise ValidationError(
                    field='data/key',
                    message='必须提供data或key参数',
                )

        elif action == 'detect':
            if 'data' in params:
                data_bytes = self._decode_input(params['data'])
                mass_energy = DataMassEnergy(data_bytes)
                detection = self._detector.detect(data_bytes, mass_energy)
                return {
                    'valid': not detection.is_singular,
                    'score': detection.overall_score,
                    'report': self.generate_report(detection),
                    'features': {},
                }
            else:
                raise ValidationError(
                    field='data',
                    message='detect操作需要data参数',
                )

        elif action == 'features':
            if 'key' in params:
                key_bytes = self._decode_input(params['key'])
                features = self._features.extract(key_bytes)
                feature_vector = self._features.feature_vector(key_bytes)
                return {
                    'valid': True,
                    'score': 1.0,
                    'report': {},
                    'features': {
                        'detailed': features,
                        'vector': feature_vector,
                    },
                }
            else:
                raise ValidationError(
                    field='key',
                    message='features操作需要key参数',
                )

        else:
            raise ValidationError(
                field='action',
                message=f'不支持的操作类型: {action}',
            )

    def validate_params(self, params: dict[str, Any]) -> bool:
        """验证输入参数。

        Args:
            params: 输入参数字典

        Returns:
            验证通过返回True

        Raises:
            ValidationError: 当参数验证失败时
        """
        if not isinstance(params, dict):
            raise ValidationError(
                field='params',
                message='参数必须是字典类型',
            )

        action = params.get('action', 'verify')
        if action not in ('verify', 'detect', 'features'):
            raise ValidationError(
                field='action',
                message=f'不支持的操作类型: {action}',
            )

        mode = params.get('mode', 'full')
        if mode not in ('fast', 'full'):
            raise ValidationError(
                field='mode',
                message=f'不支持的模式: {mode}',
            )

        sensitivity = params.get('sensitivity', 0.8)
        if sensitivity is not None:
            if not isinstance(sensitivity, (int, float)):
                raise ValidationError(
                    field='sensitivity',
                    message='sensitivity必须是数字类型',
                )
            if not 0.0 <= sensitivity <= 1.0:
                raise ValidationError(
                    field='sensitivity',
                    message='sensitivity必须在[0, 1]范围内',
                )

        return True

    def verify_key(self, key: bytes, mode: str = 'full') -> dict[str, Any]:
        """验证密钥奇点特征。

        Args:
            key: 密钥字节
            mode: 验证模式('fast'/'full')

        Returns:
            验证结果字典
        """
        if not isinstance(key, bytes):
            raise TypeError("key必须是bytes类型")

        self.fast_mode = (mode == 'fast')

        mass_energy = DataMassEnergy(key)
        detection = self._detector.detect(key, mass_energy)

        if self.fast_mode:
            score = detection.overall_score * 0.7 + mass_energy.density * 0.3
            features = {}
        else:
            features = self._features.extract(key)
            feature_score = self._calculate_feature_score(features)
            score = detection.overall_score * 0.5 + mass_energy.density * 0.2 + feature_score * 0.3

        valid = score >= 0.5 and not detection.is_singular

        return {
            'valid': valid,
            'score': score,
            'report': self.generate_report(detection),
            'features': {
                'mass_energy': mass_energy.to_dict(),
                'key_features': features,
            },
        }

    def verify_data(self, data: bytes, mode: str = 'full') -> dict[str, Any]:
        """验证数据奇点。

        Args:
            data: 数据字节
            mode: 验证模式('fast'/'full')

        Returns:
            验证结果字典
        """
        if not isinstance(data, bytes):
            raise TypeError("data必须是bytes类型")

        self.fast_mode = (mode == 'fast')

        mass_energy = DataMassEnergy(data)
        detection = self._detector.detect(data, mass_energy)

        score = detection.overall_score

        valid = score >= 0.5 and not detection.is_singular

        return {
            'valid': valid,
            'score': score,
            'report': self.generate_report(detection),
            'features': {
                'mass_energy': mass_energy.to_dict(),
            },
        }

    def generate_report(
        self,
        result: SingularityDetectionResult,
    ) -> dict[str, Any]:
        """生成验证报告。

        Args:
            result: 奇点检测结果

        Returns:
            验证报告字典
        """
        report: Dict[str, Any] = {
            'is_singular': result.is_singular,
            'overall_score': result.overall_score,
            'total_singularities': result.total_count,
            'critical_count': result.critical_count,
            'severity_breakdown': {},
            'type_breakdown': {},
            'singularities': [],
            'verdict': '',
            'recommendations': [],
        }

        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        type_counts: Dict[str, int] = {}

        for s in result.singularities:
            severity_counts[s.severity] = severity_counts.get(s.severity, 0) + 1
            type_counts[s.type] = type_counts.get(s.type, 0) + 1
            report['singularities'].append({
                'type': s.type,
                'severity': s.severity,
                'value': s.value,
                'threshold': s.threshold,
                'description': s.description,
            })

        report['severity_breakdown'] = severity_counts
        report['type_breakdown'] = type_counts

        if result.is_singular:
            report['verdict'] = '未通过奇点检测'
        else:
            report['verdict'] = '通过奇点检测'

        report['recommendations'] = self._generate_recommendations(result)

        return report

    def _calculate_feature_score(self, features: Dict[str, float]) -> float:
        """根据特征计算评分。

        Args:
            features: 特征字典

        Returns:
            特征评分(0-1)
        """
        score = 1.0

        entropy = features.get('dist_entropy', 0.0)
        score *= min(entropy / 7.0, 1.0)

        uniformity = features.get('dist_uniformity', 0.0)
        score *= (0.5 + uniformity * 0.5)

        repeat_ratio = features.get('struct_repeat_ratio', 0.0)
        score *= max(0.3, 1.0 - repeat_ratio * 2)

        period_strength = features.get('seq_period_strength', 0.0)
        score *= max(0.5, 1.0 - period_strength)

        return max(0.0, min(1.0, score))

    def _generate_recommendations(
        self,
        result: SingularityDetectionResult,
    ) -> list[str]:
        """生成改进建议。

        Args:
            result: 奇点检测结果

        Returns:
            建议列表
        """
        recommendations = []

        if result.critical_count > 0:
            recommendations.append('存在严重奇点，建议立即审查数据安全性')

        types_present = {s.type for s in result.singularities}

        if 'mass_threshold' in types_present:
            recommendations.append('数据质量异常，建议调整数据长度')

        if 'energy_singularity' in types_present:
            recommendations.append('熵值异常，建议增加数据随机性')

        if 'mass_energy_imbalance' in types_present:
            recommendations.append('质能比失衡，建议优化数据结构')

        if 'statistical_anomaly' in types_present:
            recommendations.append('统计分布异常，建议增加字节多样性')

        if 'critical_point' in types_present:
            recommendations.append('接近临界阈值，建议关注数据质量')

        if not recommendations:
            recommendations.append('数据质量良好，未检测到明显奇点')

        return recommendations

    def _decode_input(self, input_data: Any) -> bytes:
        """解码输入数据。

        Args:
            input_data: 输入数据（base64字符串或普通字符串）

        Returns:
            解码后的字节数据

        Raises:
            ValidationError: 当输入无效时
        """
        if isinstance(input_data, bytes):
            return input_data

        if isinstance(input_data, str):
            try:
                return base64.b64decode(input_data)
            except Exception:
                return input_data.encode('utf-8')

        raise ValidationError(
            field='input',
            message='输入数据必须是bytes、base64字符串或普通字符串',
        )
