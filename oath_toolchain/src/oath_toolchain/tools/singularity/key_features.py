"""密钥奇点特征提取模块。

提供密钥的多维度奇点特征提取功能，包括字节分布特征、序列特征、
结构特征、频谱特征和几何特征。
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List


class KeySingularityFeatures:
    """密钥奇点特征提取类。

    从密钥中提取多维度的奇点特征，生成特征向量并计算相似度。

    Features:
        字节分布特征（熵、均匀度、偏度）
        序列特征（自相关、周期检测）
        结构特征（模式重复、递增/递减序列）
        频谱特征（字节频率分布）
        几何特征（字节值空间分布）
    """

    def extract(self, key: bytes) -> Dict[str, float]:
        """提取密钥奇点特征。

        Args:
            key: 密钥字节

        Returns:
            包含各类特征的字典

        Raises:
            TypeError: 当key不是bytes类型时
        """
        if not isinstance(key, bytes):
            raise TypeError("key必须是bytes类型")

        features: Dict[str, float] = {}

        distribution = self._extract_distribution_features(key)
        features.update(distribution)

        sequence = self._extract_sequence_features(key)
        features.update(sequence)

        structure = self._extract_structure_features(key)
        features.update(structure)

        spectral = self._extract_spectral_features(key)
        features.update(spectral)

        geometric = self._extract_geometric_features(key)
        features.update(geometric)

        return features

    def feature_vector(self, key: bytes, size: int = 64) -> List[float]:
        """生成定长特征向量。

        Args:
            key: 密钥字节
            size: 特征向量长度，默认64

        Returns:
            定长特征向量列表

        Raises:
            TypeError: 当key不是bytes类型时
            ValueError: 当size小于1时
        """
        if not isinstance(key, bytes):
            raise TypeError("key必须是bytes类型")
        if size < 1:
            raise ValueError("size必须大于0")

        features = self.extract(key)
        feature_values = list(features.values())

        vector: List[float] = []

        if len(feature_values) >= size:
            vector = feature_values[:size]
        else:
            vector = feature_values + [0.0] * (size - len(feature_values))

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def similarity(self, key1: bytes, key2: bytes) -> float:
        """计算两个密钥的特征相似度。

        使用余弦相似度计算特征向量的相似程度。

        Args:
            key1: 第一个密钥字节
            key2: 第二个密钥字节

        Returns:
            相似度值(0-1)，1表示完全相同

        Raises:
            TypeError: 当key1或key2不是bytes类型时
        """
        if not isinstance(key1, bytes) or not isinstance(key2, bytes):
            raise TypeError("key必须是bytes类型")

        v1 = self.feature_vector(key1)
        v2 = self.feature_vector(key2)

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(v * v for v in v1))
        norm2 = math.sqrt(sum(v * v for v in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return max(0.0, min(1.0, similarity))

    def _extract_distribution_features(self, key: bytes) -> Dict[str, float]:
        """提取字节分布特征。

        包括熵、均匀度、偏度、峰度等。

        Args:
            key: 密钥字节

        Returns:
            分布特征字典
        """
        features: Dict[str, float] = {}
        n = len(key)

        if n == 0:
            return {
                'dist_entropy': 0.0,
                'dist_uniformity': 0.0,
                'dist_skewness': 0.0,
                'dist_kurtosis': 0.0,
                'dist_unique_ratio': 0.0,
                'dist_max_ratio': 0.0,
                'dist_min_ratio': 0.0,
            }

        byte_counts = Counter(key)
        total = n

        entropy = 0.0
        for count in byte_counts.values():
            prob = count / total
            entropy -= prob * math.log2(prob)
        features['dist_entropy'] = entropy

        unique_count = len(byte_counts)
        features['dist_unique_ratio'] = unique_count / 256.0

        expected_count = total / 256.0
        chi_square = sum(
            (count - expected_count) ** 2 / expected_count
            for count in byte_counts.values()
        ) + (256 - unique_count) * expected_count
        uniformity = 1.0 / (1.0 + chi_square / total)
        features['dist_uniformity'] = uniformity

        values = list(byte_counts.keys())
        counts = list(byte_counts.values())
        mean = sum(v * c for v, c in zip(values, counts)) / total
        variance = sum(c * (v - mean) ** 2 for v, c in zip(values, counts)) / total
        std = math.sqrt(variance) if variance > 0 else 0.0

        if std > 0:
            skewness = sum(
                c * ((v - mean) / std) ** 3
                for v, c in zip(values, counts)
            ) / total
            kurtosis = sum(
                c * ((v - mean) / std) ** 4
                for v, c in zip(values, counts)
            ) / total - 3.0
        else:
            skewness = 0.0
            kurtosis = 0.0

        features['dist_skewness'] = skewness
        features['dist_kurtosis'] = kurtosis

        max_count = max(byte_counts.values())
        min_count = min(byte_counts.values())
        features['dist_max_ratio'] = max_count / total
        features['dist_min_ratio'] = min_count / total

        return features

    def _extract_sequence_features(self, key: bytes) -> Dict[str, float]:
        """提取序列特征。

        包括自相关系数、周期检测、相邻字节差分等。

        Args:
            key: 密钥字节

        Returns:
            序列特征字典
        """
        features: Dict[str, float] = {}
        n = len(key)

        if n < 4:
            return {
                'seq_autocorr_1': 0.0,
                'seq_autocorr_2': 0.0,
                'seq_autocorr_4': 0.0,
                'seq_period_strength': 0.0,
                'seq_diff_mean': 0.0,
                'seq_diff_std': 0.0,
                'seq_run_count': 0.0,
            }

        key_vals = list(key)
        mean_val = sum(key_vals) / n
        variance = sum((v - mean_val) ** 2 for v in key_vals) / n

        def autocorr(lag: int) -> float:
            if variance == 0:
                return 0.0
            cov = sum(
                (key_vals[i] - mean_val) * (key_vals[i + lag] - mean_val)
                for i in range(n - lag)
            ) / (n - lag)
            return cov / variance

        features['seq_autocorr_1'] = autocorr(1)
        features['seq_autocorr_2'] = autocorr(2)
        features['seq_autocorr_4'] = autocorr(min(4, n // 4))

        diffs = [key_vals[i] - key_vals[i - 1] for i in range(1, n)]
        features['seq_diff_mean'] = sum(diffs) / len(diffs)
        diff_var = sum((d - features['seq_diff_mean']) ** 2 for d in diffs) / len(diffs)
        features['seq_diff_std'] = math.sqrt(diff_var)

        run_count = 1
        for i in range(1, n):
            if key_vals[i] != key_vals[i - 1]:
                run_count += 1
        features['seq_run_count'] = run_count / n

        period_strength = 0.0
        for period in range(2, min(16, n // 4)):
            score = 0.0
            for offset in range(period):
                segment = key_vals[offset::period]
                if len(segment) >= 3:
                    seg_mean = sum(segment) / len(segment)
                    seg_var = sum((v - seg_mean) ** 2 for v in segment) / len(segment)
                    if seg_var < variance * 0.5:
                        score += 1.0
            period_strength = max(period_strength, score / period)
        features['seq_period_strength'] = period_strength

        return features

    def _extract_structure_features(self, key: bytes) -> Dict[str, float]:
        """提取结构特征。

        包括模式重复、递增/递减序列、重复字节等。

        Args:
            key: 密钥字节

        Returns:
            结构特征字典
        """
        features: Dict[str, float] = {}
        n = len(key)

        if n < 4:
            return {
                'struct_repeat_max': 0.0,
                'struct_repeat_ratio': 0.0,
                'struct_increasing_max': 0.0,
                'struct_decreasing_max': 0.0,
                'struct_zero_ratio': 0.0,
                'struct_ff_ratio': 0.0,
                'struct_pattern_count': 0.0,
            }

        max_repeat = 1
        current_repeat = 1
        for i in range(1, n):
            if key[i] == key[i - 1]:
                current_repeat += 1
                max_repeat = max(max_repeat, current_repeat)
            else:
                current_repeat = 1
        features['struct_repeat_max'] = float(max_repeat)
        features['struct_repeat_ratio'] = max_repeat / n

        max_incr = 1
        current_incr = 1
        max_decr = 1
        current_decr = 1
        for i in range(1, n):
            if key[i] == key[i - 1] + 1:
                current_incr += 1
                max_incr = max(max_incr, current_incr)
            else:
                current_incr = 1
            if key[i] == key[i - 1] - 1:
                current_decr += 1
                max_decr = max(max_decr, current_decr)
            else:
                current_decr = 1
        features['struct_increasing_max'] = float(max_incr)
        features['struct_decreasing_max'] = float(max_decr)

        zero_count = key.count(b'\x00')
        ff_count = key.count(b'\xff')
        features['struct_zero_ratio'] = zero_count / n
        features['struct_ff_ratio'] = ff_count / n

        pattern_count = 0
        for length in range(2, min(8, n // 4)):
            seen = set()
            for i in range(n - length + 1):
                pattern = key[i:i + length]
                if pattern in seen:
                    pattern_count += 1
                else:
                    seen.add(pattern)
        features['struct_pattern_count'] = pattern_count / max(1, n)

        return features

    def _extract_spectral_features(self, key: bytes) -> Dict[str, float]:
        """提取频谱特征。

        字节频率分布的统计特征。

        Args:
            key: 密钥字节

        Returns:
            频谱特征字典
        """
        features: Dict[str, float] = {}
        n = len(key)

        if n == 0:
            return {
                'spec_low_ratio': 0.0,
                'spec_mid_ratio': 0.0,
                'spec_high_ratio': 0.0,
                'spec_band_energy_0': 0.0,
                'spec_band_energy_1': 0.0,
                'spec_band_energy_2': 0.0,
                'spec_band_energy_3': 0.0,
                'spec_centroid': 0.0,
                'spec_spread': 0.0,
            }

        byte_counts = Counter(key)

        low_count = sum(byte_counts.get(b, 0) for b in range(0, 64))
        mid_count = sum(byte_counts.get(b, 0) for b in range(64, 192))
        high_count = sum(byte_counts.get(b, 0) for b in range(192, 256))

        features['spec_low_ratio'] = low_count / n
        features['spec_mid_ratio'] = mid_count / n
        features['spec_high_ratio'] = high_count / n

        band_size = 64
        for band in range(4):
            start = band * band_size
            end = start + band_size
            band_count = sum(byte_counts.get(b, 0) for b in range(start, end))
            features[f'spec_band_energy_{band}'] = band_count / n

        centroid = sum(b * byte_counts.get(b, 0) for b in range(256)) / n
        features['spec_centroid'] = centroid / 255.0

        spread = math.sqrt(
            sum(((b - centroid) ** 2) * byte_counts.get(b, 0) for b in range(256)) / n
        ) / 255.0
        features['spec_spread'] = spread

        return features

    def _extract_geometric_features(self, key: bytes) -> Dict[str, float]:
        """提取几何特征。

        字节值空间分布的几何特征。

        Args:
            key: 密钥字节

        Returns:
            几何特征字典
        """
        features: Dict[str, float] = {}
        n = len(key)

        if n < 2:
            return {
                'geo_distance_mean': 0.0,
                'geo_distance_max': 0.0,
                'geo_distance_min': 0.0,
                'geo_centroid_x': 0.0,
                'geo_centroid_y': 0.0,
                'geo_cluster_count': 0.0,
                'geo_dispersion': 0.0,
                'geo_span': 0.0,
            }

        key_vals = list(key)

        distances = [abs(key_vals[i] - key_vals[i - 1]) for i in range(1, n)]
        features['geo_distance_mean'] = sum(distances) / len(distances) / 255.0
        features['geo_distance_max'] = max(distances) / 255.0
        features['geo_distance_min'] = min(distances) / 255.0

        xs = [i % 16 for i in range(n)]
        ys = [key_vals[i] // 16 for i in range(n)]
        centroid_x = sum(xs) / n
        centroid_y = sum(ys) / n
        features['geo_centroid_x'] = centroid_x / 15.0
        features['geo_centroid_y'] = centroid_y / 15.0

        unique_positions = set(zip(xs, ys))
        features['geo_cluster_count'] = len(unique_positions) / min(n, 256)

        dispersion = math.sqrt(
            sum(((xs[i] - centroid_x) ** 2 + (ys[i] - centroid_y) ** 2) for i in range(n)) / n
        )
        max_dispersion = math.sqrt(15 ** 2 + 15 ** 2)
        features['geo_dispersion'] = dispersion / max_dispersion

        val_min = min(key_vals)
        val_max = max(key_vals)
        features['geo_span'] = (val_max - val_min) / 255.0

        return features
