"""隐写容量与安全性分析模块。

提供隐写系统的容量计算、安全性评估和统计分析功能，
帮助评估隐写方案的有效性和隐蔽性。
"""
from __future__ import annotations

import math
from typing import Optional


class StegoCapacityAnalyzer:
    """隐写容量与安全性分析类。

    提供隐写系统的综合分析功能：
    - 载体容量分析
    - 隐写安全性评估
    - 统计特性比较
    - 分析报告生成

    Attributes:
        SUPPORTED_TYPES: 支持的载体类型列表
    """

    SUPPORTED_TYPES: list[str] = [
        "binary",
        "text",
        "image",
        "audio",
        "certificate",
    ]

    def __init__(self) -> None:
        """初始化容量分析器。"""
        pass

    def analyze_carrier(
        self,
        carrier_data: bytes,
        carrier_type: str = "binary",
    ) -> dict:
        """分析载体容量。

        对给定的载体数据进行容量分析，估算可用于隐写的容量。

        Args:
            carrier_data: 载体数据
            carrier_type: 载体类型，可选 'binary'、'text'、'image'、'audio'、'certificate'

        Returns:
            包含分析结果的字典：
            - carrier_type: 载体类型
            - total_size: 总大小（字节）
            - estimated_capacity: 估算隐写容量（字节）
            - capacity_ratio: 容量比率
            - entropy: 信息熵
            - byte_distribution: 字节分布统计
            - recommendation: 建议

        Raises:
            ValueError: 当载体类型不支持时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(carrier_data, bytes):
            raise TypeError("载体数据必须是bytes类型")
        if carrier_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"不支持的载体类型: {carrier_type}，支持的类型: {self.SUPPORTED_TYPES}"
            )

        total_size = len(carrier_data)
        entropy = self._calculate_entropy(carrier_data)
        byte_dist = self._byte_distribution(carrier_data)

        if carrier_type == "binary":
            capacity_ratio = 0.1
        elif carrier_type == "text":
            capacity_ratio = 0.05
        elif carrier_type == "image":
            capacity_ratio = 0.01
        elif carrier_type == "audio":
            capacity_ratio = 0.005
        elif carrier_type == "certificate":
            capacity_ratio = 0.02
        else:
            capacity_ratio = 0.01

        estimated_capacity = int(total_size * capacity_ratio)

        if entropy < 4:
            recommendation = "载体熵值较低，建议谨慎使用高容量隐写"
        elif entropy < 6:
            recommendation = "载体熵值适中，适合中等容量隐写"
        else:
            recommendation = "载体熵值较高，适合较高容量隐写"

        return {
            "carrier_type": carrier_type,
            "total_size": total_size,
            "estimated_capacity": estimated_capacity,
            "capacity_ratio": capacity_ratio,
            "entropy": entropy,
            "byte_distribution": byte_dist,
            "recommendation": recommendation,
        }

    def estimate_security(
        self,
        stego_data: bytes,
        original_data: bytes,
    ) -> dict:
        """评估隐写安全性。

        通过比较隐写前后的数据，评估隐写的安全性和可检测性。

        Args:
            stego_data: 隐写后的数据
            original_data: 原始载体数据

        Returns:
            包含安全评估结果的字典：
            - changed_bytes: 改变的字节数
            - change_ratio: 改变比率
            - original_entropy: 原始数据熵值
            - stego_entropy: 隐写后熵值
            - entropy_diff: 熵值差异
            - psnr: 峰值信噪比（dB）
            - detectability: 可检测性估计（low/medium/high）
            - security_score: 安全性评分（0-100）

        Raises:
            ValueError: 当数据长度不一致时
            TypeError: 当输入类型不正确时
        """
        if not isinstance(stego_data, bytes):
            raise TypeError("隐写数据必须是bytes类型")
        if not isinstance(original_data, bytes):
            raise TypeError("原始数据必须是bytes类型")
        if len(stego_data) != len(original_data):
            raise ValueError("隐写数据和原始数据长度必须相同")

        changed_bytes = 0
        mse = 0.0
        for i in range(len(original_data)):
            if stego_data[i] != original_data[i]:
                changed_bytes += 1
                diff = stego_data[i] - original_data[i]
                mse += diff * diff

        change_ratio = changed_bytes / len(original_data) if len(original_data) > 0 else 0
        mse = mse / len(original_data) if len(original_data) > 0 else 0

        original_entropy = self._calculate_entropy(original_data)
        stego_entropy = self._calculate_entropy(stego_data)
        entropy_diff = abs(stego_entropy - original_entropy)

        if mse > 0:
            psnr = 10 * math.log10((255 ** 2) / mse)
        else:
            psnr = float("inf")

        if change_ratio < 0.001 and entropy_diff < 0.1:
            detectability = "low"
            security_score = 90
        elif change_ratio < 0.01 and entropy_diff < 0.5:
            detectability = "medium"
            security_score = 60
        else:
            detectability = "high"
            security_score = 30

        return {
            "changed_bytes": changed_bytes,
            "change_ratio": change_ratio,
            "original_entropy": original_entropy,
            "stego_entropy": stego_entropy,
            "entropy_diff": entropy_diff,
            "psnr": psnr,
            "detectability": detectability,
            "security_score": security_score,
        }

    def compare_statistics(
        self,
        data1: bytes,
        data2: bytes,
    ) -> dict:
        """比较两组数据的统计特性。

        比较两组数据的统计特性，分析它们的相似性和差异。

        Args:
            data1: 第一组数据
            data2: 第二组数据

        Returns:
            包含比较结果的字典：
            - size1: 数据1大小
            - size2: 数据2大小
            - size_diff: 大小差异
            - entropy1: 数据1熵值
            - entropy2: 数据2熵值
            - entropy_diff: 熵值差异
            - mean1: 数据1平均值
            - mean2: 数据2平均值
            - mean_diff: 平均值差异
            - std1: 数据1标准差
            - std2: 数据2标准差
            - std_diff: 标准差差异
            - correlation: 相关系数
            - chi_square: 卡方检验值

        Raises:
            TypeError: 当输入类型不正确时
        """
        if not isinstance(data1, bytes):
            raise TypeError("数据1必须是bytes类型")
        if not isinstance(data2, bytes):
            raise TypeError("数据2必须是bytes类型")

        entropy1 = self._calculate_entropy(data1)
        entropy2 = self._calculate_entropy(data2)

        mean1 = sum(data1) / len(data1) if len(data1) > 0 else 0
        mean2 = sum(data2) / len(data2) if len(data2) > 0 else 0

        std1 = self._calculate_std(data1, mean1)
        std2 = self._calculate_std(data2, mean2)

        min_len = min(len(data1), len(data2))
        if min_len > 0:
            sum_product = sum((data1[i] - mean1) * (data2[i] - mean2) for i in range(min_len))
            if std1 > 0 and std2 > 0:
                correlation = sum_product / (min_len * std1 * std2)
            else:
                correlation = 0.0
        else:
            correlation = 0.0

        chi_square = self._chi_square_test(data1, data2)

        return {
            "size1": len(data1),
            "size2": len(data2),
            "size_diff": abs(len(data1) - len(data2)),
            "entropy1": entropy1,
            "entropy2": entropy2,
            "entropy_diff": abs(entropy1 - entropy2),
            "mean1": mean1,
            "mean2": mean2,
            "mean_diff": abs(mean1 - mean2),
            "std1": std1,
            "std2": std2,
            "std_diff": abs(std1 - std2),
            "correlation": correlation,
            "chi_square": chi_square,
        }

    def generate_report(
        self,
        carrier: bytes,
        secret: bytes,
        method: str = "xor",
    ) -> dict:
        """生成隐写分析报告。

        生成一份完整的隐写分析报告，包括容量分析、安全性评估等。

        Args:
            carrier: 载体数据
            secret: 秘密数据
            method: 隐写方法名称

        Returns:
            包含完整分析报告的字典：
            - method: 隐写方法
            - carrier_analysis: 载体分析结果
            - secret_size: 秘密数据大小
            - capacity_sufficient: 容量是否足够
            - security_estimation: 安全性评估
            - overall_score: 综合评分
            - recommendations: 建议列表

        Raises:
            TypeError: 当输入类型不正确时
        """
        if not isinstance(carrier, bytes):
            raise TypeError("载体数据必须是bytes类型")
        if not isinstance(secret, bytes):
            raise TypeError("秘密数据必须是bytes类型")

        carrier_analysis = self.analyze_carrier(carrier)
        secret_size = len(secret)
        capacity_sufficient = secret_size <= carrier_analysis["estimated_capacity"]

        from .xor_stego import XORSteganography
        xor_stego = XORSteganography()
        try:
            stego_data = xor_stego.embed(secret, carrier)
            security_est = self.estimate_security(stego_data, carrier)
        except Exception:
            security_est = {
                "changed_bytes": 0,
                "change_ratio": 0,
                "original_entropy": carrier_analysis["entropy"],
                "stego_entropy": carrier_analysis["entropy"],
                "entropy_diff": 0,
                "psnr": float("inf"),
                "detectability": "unknown",
                "security_score": 0,
            }

        recommendations = []
        if not capacity_sufficient:
            recommendations.append("秘密数据过大，建议使用更大的载体或压缩秘密数据")
        if security_est["detectability"] == "high":
            recommendations.append("隐写可检测性较高，建议使用更隐蔽的隐写方法")
        if carrier_analysis["entropy"] < 4:
            recommendations.append("载体熵值较低，建议选择熵值更高的载体")

        overall_score = int(
            (carrier_analysis["entropy"] / 8 * 30)
            + (security_est["security_score"] * 0.5)
            + (50 if capacity_sufficient else 0)
        )
        overall_score = min(100, overall_score)

        return {
            "method": method,
            "carrier_analysis": carrier_analysis,
            "secret_size": secret_size,
            "capacity_sufficient": capacity_sufficient,
            "security_estimation": security_est,
            "overall_score": overall_score,
            "recommendations": recommendations,
        }

    @staticmethod
    def _calculate_entropy(data: bytes) -> float:
        """计算数据的信息熵（香农熵）。

        Args:
            data: 字节数据

        Returns:
            信息熵值（0-8比特/字节）
        """
        if not data:
            return 0.0

        freq = [0] * 256
        for byte in data:
            freq[byte] += 1

        length = len(data)
        entropy = 0.0
        for count in freq:
            if count > 0:
                p = count / length
                entropy -= p * math.log2(p)

        return entropy

    @staticmethod
    def _byte_distribution(data: bytes) -> dict:
        """计算字节分布统计。

        Args:
            data: 字节数据

        Returns:
            包含分布统计的字典
        """
        if not data:
            return {"min": 0, "max": 0, "mean": 0, "median": 0}

        sorted_data = sorted(data)
        n = len(sorted_data)
        mean_val = sum(data) / n

        if n % 2 == 0:
            median = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
        else:
            median = sorted_data[n // 2]

        return {
            "min": min(data),
            "max": max(data),
            "mean": mean_val,
            "median": median,
        }

    @staticmethod
    def _calculate_std(data: bytes, mean: float) -> float:
        """计算标准差。

        Args:
            data: 字节数据
            mean: 平均值

        Returns:
            标准差值
        """
        if len(data) == 0:
            return 0.0

        variance = sum((b - mean) ** 2 for b in data) / len(data)
        return math.sqrt(variance)

    @staticmethod
    def _chi_square_test(data1: bytes, data2: bytes) -> float:
        """计算卡方检验值。

        Args:
            data1: 第一组数据
            data2: 第二组数据

        Returns:
            卡方检验值
        """
        freq1 = [0] * 256
        freq2 = [0] * 256

        for byte in data1:
            freq1[byte] += 1
        for byte in data2:
            freq2[byte] += 1

        n1 = len(data1) if len(data1) > 0 else 1
        n2 = len(data2) if len(data2) > 0 else 1

        chi_square = 0.0
        for i in range(256):
            expected = (freq1[i] + freq2[i]) / 2
            if expected > 0:
                chi_square += ((freq1[i] - expected) ** 2) / expected
                chi_square += ((freq2[i] - expected) ** 2) / expected

        return chi_square
