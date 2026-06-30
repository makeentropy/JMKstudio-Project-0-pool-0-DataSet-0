"""数据质能计算模型模块。

提供数据质量、数据能量、质能比、信息熵、信息密度和复杂度估计等
质能相关指标的计算功能。
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DataMassEnergy:
    """数据质能计算类。

    计算数据的质量、能量、熵值、密度和复杂度等质能指标。

    Attributes:
        data: 输入数据字节
        data_mass: 数据质量（字节数的归一化值）
        data_energy: 数据能量（基于熵值计算）
        mass_energy_ratio: 质能比
        entropy: 信息熵
        density: 信息密度
        complexity: 算法复杂度估计
    """

    data: bytes
    data_mass: float = 0.0
    data_energy: float = 0.0
    mass_energy_ratio: float = 0.0
    entropy: float = 0.0
    density: float = 0.0
    complexity: float = 0.0

    def __init__(self, data: bytes) -> None:
        """初始化数据质能计算器。

        Args:
            data: 输入数据字节

        Raises:
            TypeError: 当data不是bytes类型时
        """
        if not isinstance(data, bytes):
            raise TypeError("data必须是bytes类型")
        self.data = data
        self.calculate()

    def calculate(self) -> Dict[str, float]:
        """计算所有质能指标。

        Returns:
            包含所有质能指标的字典
        """
        data_len = len(self.data)

        if data_len == 0:
            self.data_mass = 0.0
            self.data_energy = 0.0
            self.mass_energy_ratio = 0.0
            self.entropy = 0.0
            self.density = 0.0
            self.complexity = 0.0
            return self.to_dict()

        self.entropy = self._calculate_entropy()
        self.data_mass = self._calculate_mass(data_len)
        self.data_energy = self._calculate_energy(data_len)
        self.mass_energy_ratio = self._calculate_mass_energy_ratio()
        self.density = self._calculate_density()
        self.complexity = self._calculate_complexity(data_len)

        return self.to_dict()

    def _calculate_entropy(self) -> float:
        """计算香农熵。

        Returns:
            香农熵值（比特/字节）
        """
        if not self.data:
            return 0.0

        byte_counts = Counter(self.data)
        total = len(self.data)
        entropy = 0.0

        for count in byte_counts.values():
            probability = count / total
            entropy -= probability * math.log2(probability)

        return entropy

    def _calculate_mass(self, data_len: int) -> float:
        """计算数据质量（归一化）。

        使用对数归一化将字节长度映射到[0, 1]区间。

        Args:
            data_len: 数据长度（字节）

        Returns:
            归一化的数据质量值
        """
        if data_len == 0:
            return 0.0
        return min(math.log2(data_len + 1) / 20.0, 1.0)

    def _calculate_energy(self, data_len: int) -> float:
        """计算数据能量。

        数据能量 = 熵值 * 数据量（比特），然后归一化。

        Args:
            data_len: 数据长度（字节）

        Returns:
            归一化的数据能量值
        """
        if data_len == 0:
            return 0.0
        total_bits = self.entropy * data_len
        return min(math.log2(total_bits + 1) / 24.0, 1.0)

    def _calculate_mass_energy_ratio(self) -> float:
        """计算质能比。

        质能比 = 数据能量 / 数据质量

        Returns:
            质能比值
        """
        if self.data_mass == 0:
            return 0.0
        return self.data_energy / self.data_mass

    def _calculate_density(self) -> float:
        """计算信息密度。

        信息密度 = 实际熵值 / 最大可能熵值（8比特/字节）

        Returns:
            信息密度值（0-1）
        """
        return self.entropy / 8.0 if self.entropy > 0 else 0.0

    def _calculate_complexity(self, data_len: int) -> float:
        """估计算法复杂度。

        基于字节分布和模式多样性来估算数据的算法复杂度。
        考虑因素：唯一字节数、熵值、模式变化率。

        Args:
            data_len: 数据长度（字节）

        Returns:
            复杂度估计值（0-1）
        """
        if data_len == 0:
            return 0.0

        unique_bytes = len(set(self.data))
        unique_ratio = unique_bytes / 256.0

        pattern_changes = 0
        for i in range(1, data_len):
            if self.data[i] != self.data[i - 1]:
                pattern_changes += 1
        change_ratio = pattern_changes / (data_len - 1) if data_len > 1 else 0.0

        complexity = (self.density * 0.5 + unique_ratio * 0.3 + change_ratio * 0.2)

        return min(complexity, 1.0)

    def to_dict(self) -> Dict[str, float]:
        """序列化为字典。

        Returns:
            包含所有质能指标的字典
        """
        return {
            'data_mass': self.data_mass,
            'data_energy': self.data_energy,
            'mass_energy_ratio': self.mass_energy_ratio,
            'entropy': self.entropy,
            'density': self.density,
            'complexity': self.complexity,
            'byte_length': len(self.data),
        }
