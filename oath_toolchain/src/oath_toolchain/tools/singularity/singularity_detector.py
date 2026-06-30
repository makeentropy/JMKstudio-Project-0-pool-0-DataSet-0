"""奇点检测算法模块。

提供多种类型的奇点检测功能，包括质量阈值奇点、能量奇点、
质能失衡奇点、临界奇点和统计异常奇点。
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional

from .mass_energy import DataMassEnergy


@dataclass
class SingularityPoint:
    """奇点数据类。

    表示一个检测到的奇点，包含类型、严重程度、检测值、阈值和描述。

    Attributes:
        type: 奇点类型
        severity: 严重程度(critical/high/medium/low)
        value: 检测值
        threshold: 阈值
        description: 描述
    """

    type: str
    severity: str
    value: float
    threshold: float
    description: str


@dataclass
class SingularityDetectionResult:
    """奇点检测结果数据类。

    包含奇点检测的完整结果，包括奇点列表、统计信息和总体评分。

    Attributes:
        total_count: 奇点总数
        critical_count: 严重数
        singularities: 奇点列表
        overall_score: 总体评分(0-1)
        is_singular: 是否达到奇点判定
    """

    total_count: int = 0
    critical_count: int = 0
    singularities: List[SingularityPoint] = field(default_factory=list)
    overall_score: float = 1.0
    is_singular: bool = False

    def to_dict(self) -> dict:
        """转换为字典。

        Returns:
            检测结果字典
        """
        return {
            'total_count': self.total_count,
            'critical_count': self.critical_count,
            'singularities': [
                {
                    'type': s.type,
                    'severity': s.severity,
                    'value': s.value,
                    'threshold': s.threshold,
                    'description': s.description,
                }
                for s in self.singularities
            ],
            'overall_score': self.overall_score,
            'is_singular': self.is_singular,
        }


class SingularityDetector:
    """奇点检测器类。

    对数据进行多维度的奇点检测，识别异常数据模式。

    Attributes:
        sensitivity: 检测灵敏度(0-1)，值越高越灵敏
    """

    def __init__(self, sensitivity: float = 0.8) -> None:
        """初始化奇点检测器。

        Args:
            sensitivity: 检测灵敏度(0-1)，默认0.8

        Raises:
            ValueError: 当sensitivity不在[0, 1]范围内时
        """
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("sensitivity必须在[0, 1]范围内")
        self.sensitivity = sensitivity

    def detect(
        self,
        data: bytes,
        mass_energy: Optional[DataMassEnergy] = None,
    ) -> SingularityDetectionResult:
        """检测数据中的奇点。

        Args:
            data: 输入数据字节
            mass_energy: 预计算的质能数据，可选

        Returns:
            奇点检测结果

        Raises:
            TypeError: 当data不是bytes类型时
        """
        if not isinstance(data, bytes):
            raise TypeError("data必须是bytes类型")

        if mass_energy is None:
            mass_energy = DataMassEnergy(data)

        result = SingularityDetectionResult()
        singularities: List[SingularityPoint] = []

        singularities.extend(self._detect_mass_threshold(data, mass_energy))
        singularities.extend(self._detect_energy_anomaly(data, mass_energy))
        singularities.extend(self._detect_mass_energy_imbalance(mass_energy))
        singularities.extend(self._detect_critical_point(data, mass_energy))
        singularities.extend(self._detect_statistical_anomaly(data, mass_energy))

        result.singularities = singularities
        result.total_count = len(singularities)
        result.critical_count = sum(
            1 for s in singularities if s.severity == 'critical'
        )

        result.overall_score = self._calculate_overall_score(singularities)

        has_critical = any(s.severity == 'critical' for s in singularities)
        threshold = 0.5 + (1 - self.sensitivity) * 0.3
        result.is_singular = has_critical or result.overall_score < threshold

        return result

    def _detect_mass_threshold(
        self,
        data: bytes,
        mass_energy: DataMassEnergy,
    ) -> List[SingularityPoint]:
        """检测质量阈值奇点。

        数据量异常（过大或过小）。

        Args:
            data: 输入数据
            mass_energy: 质能数据

        Returns:
            奇点列表
        """
        singularities = []
        data_len = len(data)

        if data_len == 0:
            singularities.append(SingularityPoint(
                type='mass_threshold',
                severity='critical',
                value=0.0,
                threshold=1.0,
                description='数据为空，质量为零',
            ))
            return singularities

        mass_threshold_low = 0.15 - 0.08 * self.sensitivity
        mass_threshold_high = 0.85 + 0.08 * self.sensitivity

        if mass_energy.data_mass < mass_threshold_low:
            severity = self._get_severity(
                mass_threshold_low - mass_energy.data_mass,
                mass_threshold_low,
            )
            singularities.append(SingularityPoint(
                type='mass_threshold',
                severity=severity,
                value=mass_energy.data_mass,
                threshold=mass_threshold_low,
                description=f'数据质量过低: {mass_energy.data_mass:.4f}',
            ))

        if mass_energy.data_mass > mass_threshold_high:
            severity = self._get_severity(
                mass_energy.data_mass - mass_threshold_high,
                1.0 - mass_threshold_high,
            )
            singularities.append(SingularityPoint(
                type='mass_threshold',
                severity=severity,
                value=mass_energy.data_mass,
                threshold=mass_threshold_high,
                description=f'数据质量过高: {mass_energy.data_mass:.4f}',
            ))

        return singularities

    def _detect_energy_anomaly(
        self,
        data: bytes,
        mass_energy: DataMassEnergy,
    ) -> List[SingularityPoint]:
        """检测能量奇点。

        熵值异常（过高或过低）。

        Args:
            data: 输入数据
            mass_energy: 质能数据

        Returns:
            奇点列表
        """
        singularities = []

        if len(data) == 0:
            return singularities

        entropy_threshold_low = 1.0 * self.sensitivity
        entropy_threshold_high = 7.5 + (1 - self.sensitivity) * 0.5

        if mass_energy.entropy < entropy_threshold_low:
            severity = self._get_severity(
                entropy_threshold_low - mass_energy.entropy,
                entropy_threshold_low,
            )
            singularities.append(SingularityPoint(
                type='energy_singularity',
                severity=severity,
                value=mass_energy.entropy,
                threshold=entropy_threshold_low,
                description=f'熵值过低: {mass_energy.entropy:.4f} 比特/字节',
            ))

        if mass_energy.entropy > entropy_threshold_high and len(data) > 32:
            severity = self._get_severity(
                mass_energy.entropy - entropy_threshold_high,
                8.0 - entropy_threshold_high,
            )
            singularities.append(SingularityPoint(
                type='energy_singularity',
                severity=severity,
                value=mass_energy.entropy,
                threshold=entropy_threshold_high,
                description=f'熵值异常偏高: {mass_energy.entropy:.4f} 比特/字节',
            ))

        return singularities

    def _detect_mass_energy_imbalance(
        self,
        mass_energy: DataMassEnergy,
    ) -> List[SingularityPoint]:
        """检测质能失衡奇点。

        质能比异常。

        Args:
            mass_energy: 质能数据

        Returns:
            奇点列表
        """
        singularities = []

        if mass_energy.data_mass == 0:
            return singularities

        ratio = mass_energy.mass_energy_ratio
        expected_ratio = 1.1
        ratio_threshold_low = expected_ratio * 0.3 * self.sensitivity
        ratio_threshold_high = expected_ratio * 1.5 + (1 - self.sensitivity) * 0.5

        if ratio < ratio_threshold_low:
            severity = self._get_severity(
                ratio_threshold_low - ratio,
                ratio_threshold_low,
            )
            singularities.append(SingularityPoint(
                type='mass_energy_imbalance',
                severity=severity,
                value=ratio,
                threshold=ratio_threshold_low,
                description=f'质能比过低: {ratio:.4f}',
            ))

        if ratio > ratio_threshold_high:
            severity = self._get_severity(
                ratio - ratio_threshold_high,
                ratio_threshold_high,
            )
            singularities.append(SingularityPoint(
                type='mass_energy_imbalance',
                severity=severity,
                value=ratio,
                threshold=ratio_threshold_high,
                description=f'质能比过高: {ratio:.4f}',
            ))

        return singularities

    def _detect_critical_point(
        self,
        data: bytes,
        mass_energy: DataMassEnergy,
    ) -> List[SingularityPoint]:
        """检测临界奇点。

        接近阈值的临界点。

        Args:
            data: 输入数据
            mass_energy: 质能数据

        Returns:
            奇点列表
        """
        singularities = []

        if len(data) < 8:
            return singularities

        critical_margin = 0.1 * self.sensitivity

        low_entropy_threshold = 2.0
        if low_entropy_threshold <= mass_energy.entropy < low_entropy_threshold + critical_margin:
            singularities.append(SingularityPoint(
                type='critical_point',
                severity='low',
                value=mass_energy.entropy,
                threshold=low_entropy_threshold,
                description='接近低熵临界阈值',
            ))

        density_threshold = 0.25
        if density_threshold <= mass_energy.density < density_threshold + critical_margin:
            singularities.append(SingularityPoint(
                type='critical_point',
                severity='low',
                value=mass_energy.density,
                threshold=density_threshold,
                description='接近低密度临界阈值',
            ))

        return singularities

    def _detect_statistical_anomaly(
        self,
        data: bytes,
        mass_energy: DataMassEnergy,
    ) -> List[SingularityPoint]:
        """检测统计异常奇点。

        分布异常、偏度异常等。

        Args:
            data: 输入数据
            mass_energy: 质能数据

        Returns:
            奇点列表
        """
        singularities = []

        if len(data) < 16:
            return singularities

        byte_counts = Counter(data)
        total = len(data)

        max_count = max(byte_counts.values())
        max_ratio = max_count / total

        concentration_threshold = 0.3 * self.sensitivity

        if max_ratio > concentration_threshold:
            severity = self._get_severity(
                max_ratio - concentration_threshold,
                1.0 - concentration_threshold,
            )
            singularities.append(SingularityPoint(
                type='statistical_anomaly',
                severity=severity,
                value=max_ratio,
                threshold=concentration_threshold,
                description=f'字节分布高度集中: {max_ratio:.4f}',
            ))

        unique_ratio = len(byte_counts) / 256.0
        unique_threshold = 0.1 * self.sensitivity

        if unique_ratio < unique_threshold:
            severity = self._get_severity(
                unique_threshold - unique_ratio,
                unique_threshold,
            )
            singularities.append(SingularityPoint(
                type='statistical_anomaly',
                severity=severity,
                value=unique_ratio,
                threshold=unique_threshold,
                description=f'字节多样性过低: {unique_ratio:.4f}',
            ))

        skewness = self._calculate_skewness(data, byte_counts)
        if abs(skewness) > 1.0 * self.sensitivity:
            severity = self._get_severity(
                abs(skewness) - 1.0,
                2.0,
            )
            singularities.append(SingularityPoint(
                type='statistical_anomaly',
                severity=severity,
                value=skewness,
                threshold=1.0 * self.sensitivity,
                description=f'分布偏度异常: {skewness:.4f}',
            ))

        max_incr = 1
        current_incr = 1
        max_decr = 1
        current_decr = 1
        for i in range(1, len(data)):
            if data[i] == data[i - 1] + 1:
                current_incr += 1
                max_incr = max(max_incr, current_incr)
            else:
                current_incr = 1
            if data[i] == data[i - 1] - 1:
                current_decr += 1
                max_decr = max(max_decr, current_decr)
            else:
                current_decr = 1

        sequence_threshold = max(8, int(len(data) * 0.2 * self.sensitivity))
        max_sequence = max(max_incr, max_decr)
        if max_sequence >= sequence_threshold and sequence_threshold >= 4:
            sequence_ratio = max_sequence / len(data)
            severity = self._get_severity(
                sequence_ratio - 0.1,
                0.9,
            )
            singularities.append(SingularityPoint(
                type='statistical_anomaly',
                severity=severity,
                value=float(max_sequence),
                threshold=float(sequence_threshold),
                description=f'存在长连续序列: {max_sequence}',
            ))

        return singularities

    def _calculate_skewness(self, data: bytes, byte_counts: Counter) -> float:
        """计算分布偏度。

        Args:
            data: 输入数据
            byte_counts: 字节计数

        Returns:
            偏度值
        """
        n = len(data)
        if n < 3:
            return 0.0

        values = list(byte_counts.keys())
        counts = list(byte_counts.values())

        mean = sum(v * c for v, c in zip(values, counts)) / n

        variance = sum(c * (v - mean) ** 2 for v, c in zip(values, counts)) / n
        std = math.sqrt(variance) if variance > 0 else 0.0

        if std == 0:
            return 0.0

        skewness = sum(c * ((v - mean) / std) ** 3 for v, c in zip(values, counts)) / n

        return skewness

    def _get_severity(self, deviation: float, range_value: float) -> str:
        """根据偏差程度获取严重等级。

        Args:
            deviation: 偏差值
            range_value: 参考范围

        Returns:
            严重等级(critical/high/medium/low)
        """
        if range_value == 0:
            return 'low'

        ratio = deviation / range_value

        if ratio >= 0.8:
            return 'critical'
        elif ratio >= 0.5:
            return 'high'
        elif ratio >= 0.2:
            return 'medium'
        else:
            return 'low'

    def _calculate_overall_score(
        self,
        singularities: List[SingularityPoint],
    ) -> float:
        """计算总体评分。

        Args:
            singularities: 奇点列表

        Returns:
            总体评分(0-1)
        """
        if not singularities:
            return 1.0

        severity_weights = {
            'critical': 0.3,
            'high': 0.15,
            'medium': 0.08,
            'low': 0.03,
        }

        total_penalty = 0.0
        for s in singularities:
            total_penalty += severity_weights.get(s.severity, 0.05)

        return max(0.0, 1.0 - total_penalty)
