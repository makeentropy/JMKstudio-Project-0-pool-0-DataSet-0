"""文本语义特征提取模块。

提供从自然语言文本中提取多种特征的功能，包括字符n-gram、词频统计、
字符分布、信息熵和语义种子等，用于后续的密钥生成。
"""
from __future__ import annotations

import math
import re
import struct
import unicodedata
from collections import Counter
from typing import List, Optional

from ...core.crypto.hash import Hash


class TextFeatureExtractor:
    """文本特征提取器。

    从文本中提取多种统计和语义特征，支持中英文等多语言文本。

    Attributes:
        lang: 语言设置，默认为'auto'自动检测
    """

    _CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')
    _JAPANESE_PATTERN = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
    _ENGLISH_WORD_PATTERN = re.compile(r'[a-zA-Z]+')
    _NUMBER_PATTERN = re.compile(r'\d+')

    def __init__(self, lang: str = 'auto') -> None:
        """初始化文本特征提取器。

        Args:
            lang: 语言设置，支持'auto'、'zh'、'en'、'ja'，默认为'auto'
        """
        self.lang = lang

    def extract_features(self, text: str) -> dict:
        """提取文本的综合特征。

        Args:
            text: 输入文本

        Returns:
            包含所有特征的字典，包括：
            - length: 文本长度
            - char_distribution: 字符分布统计
            - char_unigrams: 1-gram频率
            - char_bigrams: 2-gram频率
            - char_trigrams: 3-gram频率
            - word_tokens: 分词结果
            - word_freq: 词频统计
            - entropy: 文本信息熵
            - lang: 检测到的语言
        """
        if not isinstance(text, str):
            raise TypeError("text必须是字符串类型")

        detected_lang = self._detect_lang(text) if self.lang == 'auto' else self.lang

        char_unigrams = self.char_ngrams(text, 1)
        char_bigrams = self.char_ngrams(text, 2)
        char_trigrams = self.char_ngrams(text, 3)

        word_tokens = self.word_tokens(text, detected_lang)
        word_freq = Counter(word_tokens)

        char_distribution = self._char_distribution(text)
        entropy = self.compute_entropy(text)

        return {
            'length': len(text),
            'char_distribution': char_distribution,
            'char_unigrams': dict(char_unigrams),
            'char_bigrams': dict(char_bigrams),
            'char_trigrams': dict(char_trigrams),
            'word_tokens': word_tokens,
            'word_freq': dict(word_freq),
            'entropy': entropy,
            'lang': detected_lang,
        }

    def char_ngrams(self, text: str, n: int = 2) -> Counter:
        """提取字符n-gram。

        Args:
            text: 输入文本
            n: n-gram的n值，默认为2

        Returns:
            n-gram的Counter对象

        Raises:
            ValueError: 当n小于1时
        """
        if n < 1:
            raise ValueError("n必须大于等于1")

        if len(text) < n:
            return Counter()

        ngrams = [text[i:i + n] for i in range(len(text) - n + 1)]
        return Counter(ngrams)

    def word_tokens(self, text: str, lang: Optional[str] = None) -> List[str]:
        """对文本进行分词。

        Args:
            text: 输入文本
            lang: 语言，不提供则使用实例的lang设置

        Returns:
            分词结果列表
        """
        if lang is None:
            lang = self._detect_lang(text) if self.lang == 'auto' else self.lang

        if lang == 'zh':
            return self._tokenize_chinese(text)
        elif lang == 'ja':
            return self._tokenize_japanese(text)
        elif lang == 'en':
            return self._tokenize_english(text)
        else:
            return self._tokenize_mixed(text)

    def compute_entropy(self, text: str) -> float:
        """计算文本的香农信息熵。

        Args:
            text: 输入文本

        Returns:
            信息熵值（比特/字符）
        """
        if not text:
            return 0.0

        char_counts = Counter(text)
        total = len(text)
        entropy = 0.0

        for count in char_counts.values():
            probability = count / total
            entropy -= probability * math.log2(probability)

        return entropy

    def semantic_seed(self, text: str) -> bytes:
        """生成语义种子（定长字节序列）。

        基于文本的多种特征组合生成一个32字节的语义种子，
        相同的文本会生成相同的种子。

        Args:
            text: 输入文本

        Returns:
            32字节的语义种子
        """
        features = self.extract_features(text)

        seed_material = bytearray()

        seed_material.extend(text.encode('utf-8'))
        seed_material.extend(features['length'].to_bytes(8, 'big'))
        seed_material.extend(struct.pack('>d', features['entropy']))

        char_dist = features['char_distribution']
        for key in sorted(char_dist.keys()):
            seed_material.extend(key.encode('utf-8'))
            seed_material.extend(struct.pack('>d', char_dist[key]))

        top_unigrams = sorted(
            features['char_unigrams'].items(),
            key=lambda x: (-x[1], x[0])
        )[:50]
        for char, count in top_unigrams:
            seed_material.extend(char.encode('utf-8'))
            seed_material.extend(count.to_bytes(4, 'big'))

        top_bigrams = sorted(
            features['char_bigrams'].items(),
            key=lambda x: (-x[1], x[0])
        )[:50]
        for bigram, count in top_bigrams:
            seed_material.extend(bigram.encode('utf-8'))
            seed_material.extend(count.to_bytes(4, 'big'))

        top_words = sorted(
            features['word_freq'].items(),
            key=lambda x: (-x[1], x[0])
        )[:50]
        for word, count in top_words:
            seed_material.extend(word.encode('utf-8'))
            seed_material.extend(count.to_bytes(4, 'big'))

        return Hash.sha256(bytes(seed_material))

    def _detect_lang(self, text: str) -> str:
        """检测文本的主要语言。

        Args:
            text: 输入文本

        Returns:
            语言代码：'zh'、'en'、'ja'或'mixed'
        """
        if not text:
            return 'en'

        chinese_count = len(self._CHINESE_PATTERN.findall(text))
        japanese_count = len(self._JAPANESE_PATTERN.findall(text))
        english_count = len(self._ENGLISH_WORD_PATTERN.findall(text))

        total_chars = len(text)
        if total_chars == 0:
            return 'en'

        chinese_ratio = chinese_count / total_chars
        japanese_ratio = (japanese_count - chinese_count) / total_chars
        english_ratio = sum(len(w) for w in self._ENGLISH_WORD_PATTERN.findall(text)) / total_chars

        if chinese_ratio > 0.3:
            return 'zh'
        elif japanese_ratio > 0.2:
            return 'ja'
        elif english_ratio > 0.3:
            return 'en'
        else:
            return 'mixed'

    def _tokenize_chinese(self, text: str) -> List[str]:
        """中文简单分词。

        按单个字符进行分词，同时提取连续的英文和数字串。

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        tokens = []
        current_en = []
        current_num = []

        for char in text:
            if self._CHINESE_PATTERN.match(char):
                if current_en:
                    tokens.append(''.join(current_en))
                    current_en = []
                if current_num:
                    tokens.append(''.join(current_num))
                    current_num = []
                tokens.append(char)
            elif char.isalpha():
                if current_num:
                    tokens.append(''.join(current_num))
                    current_num = []
                current_en.append(char)
            elif char.isdigit():
                if current_en:
                    tokens.append(''.join(current_en))
                    current_en = []
                current_num.append(char)
            else:
                if current_en:
                    tokens.append(''.join(current_en))
                    current_en = []
                if current_num:
                    tokens.append(''.join(current_num))
                    current_num = []

        if current_en:
            tokens.append(''.join(current_en))
        if current_num:
            tokens.append(''.join(current_num))

        return tokens

    def _tokenize_japanese(self, text: str) -> List[str]:
        """日文简单分词。

        按单个字符进行分词。

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        tokens = []
        current_en = []
        current_num = []

        for char in text:
            if (self._CHINESE_PATTERN.match(char) or
                    self._JAPANESE_PATTERN.match(char)):
                if current_en:
                    tokens.append(''.join(current_en))
                    current_en = []
                if current_num:
                    tokens.append(''.join(current_num))
                    current_num = []
                tokens.append(char)
            elif char.isalpha():
                if current_num:
                    tokens.append(''.join(current_num))
                    current_num = []
                current_en.append(char)
            elif char.isdigit():
                if current_en:
                    tokens.append(''.join(current_en))
                    current_en = []
                current_num.append(char)
            else:
                if current_en:
                    tokens.append(''.join(current_en))
                    current_en = []
                if current_num:
                    tokens.append(''.join(current_num))
                    current_num = []

        if current_en:
            tokens.append(''.join(current_en))
        if current_num:
            tokens.append(''.join(current_num))

        return tokens

    def _tokenize_english(self, text: str) -> List[str]:
        """英文分词。

        按空格和标点符号分词，提取单词和数字。

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        tokens = []
        words = re.findall(r'[a-zA-Z]+|\d+', text.lower())
        tokens.extend(words)
        return tokens

    def _tokenize_mixed(self, text: str) -> List[str]:
        """混合语言分词。

        对混合语言文本进行分词，分别处理不同语言部分。

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        tokens = []
        current_segment = []
        current_type = None

        for char in text:
            if self._CHINESE_PATTERN.match(char):
                char_type = 'cjk'
            elif char.isalpha():
                char_type = 'alpha'
            elif char.isdigit():
                char_type = 'digit'
            else:
                char_type = 'other'

            if char_type != current_type and current_segment:
                segment = ''.join(current_segment)
                if current_type == 'cjk':
                    tokens.extend(list(segment))
                elif current_type == 'alpha':
                    tokens.append(segment.lower())
                elif current_type == 'digit':
                    tokens.append(segment)
                current_segment = []

            if char_type != 'other':
                current_segment.append(char)
                current_type = char_type
            else:
                current_type = None

        if current_segment:
            segment = ''.join(current_segment)
            if current_type == 'cjk':
                tokens.extend(list(segment))
            elif current_type == 'alpha':
                tokens.append(segment.lower())
            elif current_type == 'digit':
                tokens.append(segment)

        return tokens

    def _char_distribution(self, text: str) -> dict:
        """统计字符分布。

        Args:
            text: 输入文本

        Returns:
            包含各类字符比例的字典
        """
        if not text:
            return {
                'letters': 0.0,
                'digits': 0.0,
                'symbols': 0.0,
                'spaces': 0.0,
                'cjk': 0.0,
            }

        total = len(text)
        letters = 0
        digits = 0
        symbols = 0
        spaces = 0
        cjk = 0

        for char in text:
            if char.isspace():
                spaces += 1
            elif self._CHINESE_PATTERN.match(char) or self._JAPANESE_PATTERN.match(char):
                cjk += 1
            elif char.isalpha():
                letters += 1
            elif char.isdigit():
                digits += 1
            else:
                symbols += 1

        return {
            'letters': letters / total,
            'digits': digits / total,
            'symbols': symbols / total,
            'spaces': spaces / total,
            'cjk': cjk / total,
        }
