"""密钥强度评估模块。

提供密钥强度的综合评估功能，包括熵值计算、模式检测、
破解时间估算和强度评级。
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List


class KeyStrengthEvaluator:
    """密钥强度评估器。

    对密钥进行多维度的强度评估，包括香农熵计算、弱模式检测、
    破解时间估算和综合强度评分。

    Attributes:
        _COMMON_PATTERNS: 常见弱模式列表
    """

    _COMMON_PATTERNS = [
        b'\x00' * 4,
        b'\xff' * 4,
        b'\x01\x02\x03\x04',
        b'\x04\x03\x02\x01',
        b'password',
        b'12345678',
        b'abcdefgh',
    ]

    _WEAK_KEYWORDS = [
        b'password', b'admin', b'root', b'test', b'guest',
        b'qwerty', b'abc123', b'letmein', b'monkey', b'dragon',
    ]

    def evaluate(self, key: bytes) -> dict:
        """综合评估密钥强度。

        Args:
            key: 待评估的密钥字节

        Returns:
            包含评估结果的字典：
            - entropy: 香农熵值（比特/字节）
            - bit_size: 密钥位数
            - char_diversity: 字符多样性统计
            - pattern_detection: 弱模式检测结果
            - strength_score: 强度评分（0-1）
            - strength_level: 强度等级
            - crack_time: 破解时间估算
            - recommendations: 改进建议列表
        """
        if not isinstance(key, bytes):
            raise TypeError("key必须是bytes类型")

        entropy = self.calculate_entropy(key)
        bit_size = len(key) * 8
        char_diversity = self._char_diversity(key)
        patterns = self.detect_patterns(key)
        crack_time = self.estimate_crack_time(key)

        score = self._calculate_strength_score(key, entropy, patterns)
        level = self._get_strength_level(score)
        recommendations = self._get_recommendations(key, entropy, patterns, score)

        return {
            'entropy': entropy,
            'bit_size': bit_size,
            'char_diversity': char_diversity,
            'pattern_detection': patterns,
            'strength_score': score,
            'strength_level': level,
            'crack_time': crack_time,
            'recommendations': recommendations,
        }

    def calculate_entropy(self, key: bytes) -> float:
        """计算密钥的香农熵。

        Args:
            key: 密钥字节

        Returns:
            香农熵值（比特/字节）
        """
        if not key:
            return 0.0

        byte_counts = Counter(key)
        total = len(key)
        entropy = 0.0

        for count in byte_counts.values():
            probability = count / total
            entropy -= probability * math.log2(probability)

        return entropy

    def detect_patterns(self, key: bytes) -> dict:
        """检测密钥中的弱模式。

        Args:
            key: 密钥字节

        Returns:
            包含各种模式检测结果的字典
        """
        if not isinstance(key, bytes):
            raise TypeError("key必须是bytes类型")

        return {
            'repeated_bytes': self._detect_repeated_bytes(key),
            'increasing_sequence': self._detect_increasing_sequence(key),
            'decreasing_sequence': self._detect_decreasing_sequence(key),
            'common_patterns': self._detect_common_patterns(key),
            'weak_keywords': self._detect_weak_keywords(key),
            'zero_padding': self._detect_zero_padding(key),
            'ff_padding': self._detect_ff_padding(key),
        }

    def estimate_crack_time(self, key: bytes) -> dict:
        """估算密钥的破解时间。

        基于暴力破解的假设进行估算，考虑不同的攻击场景。

        Args:
            key: 密钥字节

        Returns:
            包含不同场景下破解时间估算的字典
        """
        if not key:
            return {
                'online_attack': 'instant',
                'offline_fast': 'instant',
                'offline_slow': 'instant',
                'brute_force': 'instant',
            }

        entropy = self.calculate_entropy(key)
        total_entropy = entropy * len(key)

        guesses_per_second_online = 100
        guesses_per_second_fast = 1e12
        guesses_per_second_slow = 1e9

        online_time = self._format_time(
            self._crack_time(total_entropy, guesses_per_second_online)
        )
        fast_time = self._format_time(
            self._crack_time(total_entropy, guesses_per_second_fast)
        )
        slow_time = self._format_time(
            self._crack_time(total_entropy, guesses_per_second_slow)
        )
        brute_time = self._format_time(
            self._crack_time(len(key) * 8, guesses_per_second_fast)
        )

        return {
            'online_attack': online_time,
            'offline_fast': fast_time,
            'offline_slow': slow_time,
            'brute_force': brute_time,
            'total_entropy_bits': total_entropy,
        }

    def _char_diversity(self, key: bytes) -> dict:
        """统计密钥的字符多样性。

        Args:
            key: 密钥字节

        Returns:
            包含多样性统计的字典
        """
        if not key:
            return {
                'unique_bytes': 0,
                'total_bytes': 0,
                'diversity_ratio': 0.0,
                'byte_range_min': 0,
                'byte_range_max': 0,
            }

        unique_bytes = len(set(key))
        total_bytes = len(key)
        diversity_ratio = unique_bytes / 256.0

        return {
            'unique_bytes': unique_bytes,
            'total_bytes': total_bytes,
            'diversity_ratio': diversity_ratio,
            'byte_range_min': min(key),
            'byte_range_max': max(key),
        }

    def _detect_repeated_bytes(self, key: bytes) -> dict:
        """检测重复字节模式。

        Args:
            key: 密钥字节

        Returns:
            检测结果字典
        """
        if len(key) < 4:
            return {
                'found': False,
                'max_run_length': 0,
                'byte_value': None,
            }

        max_run = 1
        current_run = 1
        max_byte = key[0] if key else None

        for i in range(1, len(key)):
            if key[i] == key[i - 1]:
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
                    max_byte = key[i]
            else:
                current_run = 1

        return {
            'found': max_run >= 4,
            'max_run_length': max_run,
            'byte_value': max_byte,
        }

    def _detect_increasing_sequence(self, key: bytes) -> dict:
        """检测递增字节序列。

        Args:
            key: 密钥字节

        Returns:
            检测结果字典
        """
        if len(key) < 4:
            return {
                'found': False,
                'max_run_length': 0,
            }

        max_run = 1
        current_run = 1

        for i in range(1, len(key)):
            if key[i] == key[i - 1] + 1:
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
            else:
                current_run = 1

        return {
            'found': max_run >= 4,
            'max_run_length': max_run,
        }

    def _detect_decreasing_sequence(self, key: bytes) -> dict:
        """检测递减字节序列。

        Args:
            key: 密钥字节

        Returns:
            检测结果字典
        """
        if len(key) < 4:
            return {
                'found': False,
                'max_run_length': 0,
            }

        max_run = 1
        current_run = 1

        for i in range(1, len(key)):
            if key[i] == key[i - 1] - 1:
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
            else:
                current_run = 1

        return {
            'found': max_run >= 4,
            'max_run_length': max_run,
        }

    def _detect_common_patterns(self, key: bytes) -> dict:
        """检测常见弱模式。

        Args:
            key: 密钥字节

        Returns:
            检测结果字典
        """
        found_patterns = []

        for pattern in self._COMMON_PATTERNS:
            if pattern in key:
                found_patterns.append(pattern.hex())

        return {
            'found': len(found_patterns) > 0,
            'patterns': found_patterns,
        }

    def _detect_weak_keywords(self, key: bytes) -> dict:
        """检测弱密码关键词。

        Args:
            key: 密钥字节

        Returns:
            检测结果字典
        """
        found_keywords = []
        key_lower = key.lower()

        for keyword in self._WEAK_KEYWORDS:
            if keyword in key_lower:
                found_keywords.append(keyword.decode('ascii', errors='replace'))

        return {
            'found': len(found_keywords) > 0,
            'keywords': found_keywords,
        }

    def _detect_zero_padding(self, key: bytes) -> dict:
        """检测零填充模式。

        Args:
            key: 密钥字节

        Returns:
            检测结果字典
        """
        if len(key) < 8:
            return {
                'found': False,
                'zero_count': 0,
                'zero_ratio': 0.0,
            }

        zero_count = key.count(b'\x00')
        zero_ratio = zero_count / len(key)

        return {
            'found': zero_ratio > 0.25,
            'zero_count': zero_count,
            'zero_ratio': zero_ratio,
        }

    def _detect_ff_padding(self, key: bytes) -> dict:
        """检测0xFF填充模式。

        Args:
            key: 密钥字节

        Returns:
            检测结果字典
        """
        if len(key) < 8:
            return {
                'found': False,
                'ff_count': 0,
                'ff_ratio': 0.0,
            }

        ff_count = key.count(b'\xff')
        ff_ratio = ff_count / len(key)

        return {
            'found': ff_ratio > 0.25,
            'ff_count': ff_count,
            'ff_ratio': ff_ratio,
        }

    def _calculate_strength_score(
        self,
        key: bytes,
        entropy: float,
        patterns: dict,
    ) -> float:
        """计算密钥强度评分。

        Args:
            key: 密钥字节
            entropy: 熵值
            patterns: 模式检测结果

        Returns:
            强度评分（0-1）
        """
        if not key:
            return 0.0

        score = 1.0

        score *= min(entropy / 8.0, 1.0)

        score *= min(len(key) / 32.0, 1.0)

        penalty = 0.0
        if patterns['repeated_bytes']['found']:
            penalty += 0.2
        if patterns['increasing_sequence']['found']:
            penalty += 0.15
        if patterns['decreasing_sequence']['found']:
            penalty += 0.15
        if patterns['common_patterns']['found']:
            penalty += 0.2
        if patterns['weak_keywords']['found']:
            penalty += 0.25
        if patterns['zero_padding']['found']:
            penalty += 0.15
        if patterns['ff_padding']['found']:
            penalty += 0.15

        score = max(0.0, score - penalty)

        return score

    def _get_strength_level(self, score: float) -> str:
        """根据评分获取强度等级。

        Args:
            score: 强度评分（0-1）

        Returns:
            强度等级字符串
        """
        if score >= 0.8:
            return 'very_strong'
        elif score >= 0.6:
            return 'strong'
        elif score >= 0.3:
            return 'medium'
        else:
            return 'weak'

    def _get_recommendations(
        self,
        key: bytes,
        entropy: float,
        patterns: dict,
        score: float,
    ) -> List[str]:
        """生成密钥改进建议。

        Args:
            key: 密钥字节
            entropy: 熵值
            patterns: 模式检测结果
            score: 强度评分

        Returns:
            建议列表
        """
        recommendations = []

        if len(key) < 16:
            recommendations.append("增加密钥长度到至少16字节（128位）")
        elif len(key) < 32:
            recommendations.append("建议使用32字节（256位）密钥以获得更高安全性")

        if entropy < 4.0:
            recommendations.append("密钥熵值过低，建议使用更多样化的字符")
        elif entropy < 6.0:
            recommendations.append("密钥熵值一般，可以进一步增加字符多样性")

        if patterns['repeated_bytes']['found']:
            recommendations.append("避免使用重复字节序列")

        if patterns['increasing_sequence']['found']:
            recommendations.append("避免使用递增字节序列")

        if patterns['decreasing_sequence']['found']:
            recommendations.append("避免使用递减字节序列")

        if patterns['common_patterns']['found']:
            recommendations.append("避免使用常见的弱模式")

        if patterns['weak_keywords']['found']:
            recommendations.append("避免使用常见弱密码关键词")

        if patterns['zero_padding']['found']:
            recommendations.append("避免大量零字节填充")

        if patterns['ff_padding']['found']:
            recommendations.append("避免大量0xFF字节填充")

        if not recommendations:
            recommendations.append("密钥强度良好，继续保持")

        return recommendations

    def _crack_time(self, entropy_bits: float, guesses_per_second: float) -> float:
        """计算破解时间（秒）。

        Args:
            entropy_bits: 熵值（比特）
            guesses_per_second: 每秒猜测次数

        Returns:
            破解时间（秒）
        """
        if entropy_bits <= 0:
            return 0.0

        total_guesses = 2 ** entropy_bits / 2
        return total_guesses / guesses_per_second

    def _format_time(self, seconds: float) -> str:
        """格式化时间为可读字符串。

        Args:
            seconds: 秒数

        Returns:
            可读的时间字符串
        """
        if seconds < 0.001:
            return 'instant'
        elif seconds < 1:
            return f'{seconds * 1000:.2f}毫秒'
        elif seconds < 60:
            return f'{seconds:.2f}秒'
        elif seconds < 3600:
            return f'{seconds / 60:.2f}分钟'
        elif seconds < 86400:
            return f'{seconds / 3600:.2f}小时'
        elif seconds < 31536000:
            return f'{seconds / 86400:.2f}天'
        elif seconds < 31536000 * 100:
            return f'{seconds / 31536000:.2f}年'
        elif seconds < 31536000 * 1e6:
            return f'{seconds / 31536000 / 1000:.2f}千年'
        elif seconds < 31536000 * 1e9:
            return f'{seconds / 31536000 / 1e6:.2f}百万年'
        else:
            return f'{seconds / 31536000 / 1e9:.2f}十亿年'
