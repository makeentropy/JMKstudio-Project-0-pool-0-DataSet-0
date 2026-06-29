"""
特征编码器模块

提供文本、数值、序列等多种数据类型的特征编码功能。
"""

import hashlib
import math
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.mind.models import (
    EmbeddingConfig,
    MindVector,
    MindVectorType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class TextEncoder:
    """文本编码器"""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self.dimensions = self.config.dimensions
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._build_default_vocab()

    def _build_default_vocab(self) -> None:
        words = [
            "entropy", "information", "system", "data", "model", "vector",
            "dimension", "space", "feature", "pattern", "structure", "dynamics",
            "probability", "distribution", "uncertainty", "measurement",
            "analysis", "learning", "optimization", "representation",
            "financial", "market", "price", "trading", "investment", "risk",
            "portfolio", "asset", "strategy", "return", "volatility",
            "terrain", "height", "gradient", "topology", "landscape",
            "mind", "cognition", "memory", "reasoning", "perception",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "of", "in", "on", "at", "to", "for", "with", "by", "from",
            "and", "or", "but", "not", "no", "yes", "all", "some", "any",
            "high", "low", "more", "less", "most", "least", "very", "much",
            "time", "state", "change", "process", "function", "value",
        ]
        for i, word in enumerate(words):
            self._vocab[word] = i

    def encode_bow(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions)
        words = self._tokenize(text)
        for word in words:
            if word in self._vocab:
                idx = self._vocab[word] % self.dimensions
                vector[idx] += 1
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def encode_tfidf(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions)
        words = self._tokenize(text)
        if not words:
            return vector

        word_counts: Dict[str, int] = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        total_words = len(words)
        for word, count in word_counts.items():
            tf = count / total_words
            idf = self._idf.get(word, 1.0)
            if word in self._vocab:
                idx = self._vocab[word] % self.dimensions
                vector[idx] = tf * idf

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def encode_hash(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions)
        words = self._tokenize(text)

        for word in words:
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = hash_val % self.dimensions
            sign = 1 if (hash_val >> 1) % 2 == 0 else -1
            vector[idx] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def encode_semantic(self, text: str) -> np.ndarray:
        hash_vec = self.encode_hash(text)
        bow_vec = self.encode_bow(text)
        combined = 0.6 * hash_vec + 0.4 * bow_vec
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        return words

    def encode(self, text: str, method: str = "semantic") -> MindVector:
        if method == "bow":
            values = self.encode_bow(text)
        elif method == "tfidf":
            values = self.encode_tfidf(text)
        elif method == "hash":
            values = self.encode_hash(text)
        else:
            values = self.encode_semantic(text)

        vector = MindVector(
            vector_type=MindVectorType.SEMANTIC,
            dimensions=self.dimensions,
        )
        vector.from_numpy(values)
        return vector


class NumericEncoder:
    """数值编码器"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    def encode_scalar(self, value: float, min_val: float = 0.0, max_val: float = 1.0) -> np.ndarray:
        vector = np.zeros(self.dimensions)
        normalized = (value - min_val) / (max_val - min_val) if max_val != min_val else 0.5
        idx = int(normalized * (self.dimensions - 1))
        idx = max(0, min(self.dimensions - 1, idx))

        if idx > 0:
            vector[idx - 1] = 0.3
        vector[idx] = 1.0
        if idx < self.dimensions - 1:
            vector[idx + 1] = 0.3

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def encode_values(self, values: List[float], method: str = "fourier") -> np.ndarray:
        if method == "fourier":
            return self._encode_fourier(values)
        elif method == "statistical":
            return self._encode_statistical(values)
        elif method == "histogram":
            return self._encode_histogram(values)
        else:
            return self._encode_fourier(values)

    def _encode_fourier(self, values: List[float]) -> np.ndarray:
        arr = np.array(values, dtype=float)
        if len(arr) == 0:
            return np.zeros(self.dimensions)

        fft = np.fft.fft(arr)
        magnitude = np.abs(fft[:len(fft) // 2])

        vector = np.zeros(self.dimensions)
        n = min(len(magnitude), self.dimensions)
        vector[:n] = magnitude[:n]

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def _encode_statistical(self, values: List[float]) -> np.ndarray:
        arr = np.array(values, dtype=float)
        vector = np.zeros(self.dimensions)

        if len(arr) == 0:
            return vector

        stats = [
            np.mean(arr),
            np.std(arr),
            np.min(arr),
            np.max(arr),
            np.median(arr),
            np.percentile(arr, 25),
            np.percentile(arr, 75),
            float(len(arr)),
        ]

        for i, stat in enumerate(stats):
            if i < self.dimensions:
                vector[i] = stat

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def _encode_histogram(self, values: List[float]) -> np.ndarray:
        arr = np.array(values, dtype=float)
        if len(arr) == 0:
            return np.zeros(self.dimensions)

        hist, _ = np.histogram(arr, bins=min(self.dimensions, 50), density=True)
        vector = np.zeros(self.dimensions)
        vector[:len(hist)] = hist

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def encode(self, values: List[float], method: str = "fourier") -> MindVector:
        data = self.encode_values(values, method)
        vector = MindVector(
            vector_type=MindVectorType.STRUCTURAL,
            dimensions=self.dimensions,
        )
        vector.from_numpy(data)
        return vector


class SequenceEncoder:
    """序列编码器"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    def encode_position(self, seq_length: int) -> np.ndarray:
        position = np.arange(seq_length)[:, np.newaxis]
        div_term = np.exp(np.arange(0, self.dimensions, 2) * -(math.log(10000.0) / self.dimensions))
        pe = np.zeros((seq_length, self.dimensions))
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)
        return pe

    def encode_sequence(self, sequence: List[float], method: str = "pooling") -> np.ndarray:
        if method == "pooling":
            return self._encode_pooling(sequence)
        elif method == "pyramid":
            return self._encode_pyramid(sequence)
        elif method == "sax":
            return self._encode_sax(sequence)
        else:
            return self._encode_pooling(sequence)

    def _encode_pooling(self, sequence: List[float]) -> np.ndarray:
        arr = np.array(sequence)
        vector = np.zeros(self.dimensions)

        if len(arr) == 0:
            return vector

        window_size = max(1, len(arr) // self.dimensions)
        for i in range(self.dimensions):
            start = i * window_size
            end = min(start + window_size, len(arr))
            if start < len(arr):
                vector[i] = np.mean(arr[start:end])

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def _encode_pyramid(self, sequence: List[float]) -> np.ndarray:
        arr = np.array(sequence)
        vector = np.zeros(self.dimensions)

        if len(arr) == 0:
            return vector

        levels = int(math.log2(min(len(arr), self.dimensions)))
        idx = 0
        for level in range(levels):
            if idx >= self.dimensions:
                break
            stride = 2 ** level
            downsampled = arr[::stride]
            n = min(len(downsampled), self.dimensions - idx)
            vector[idx:idx + n] = downsampled[:n]
            idx += n

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def _encode_sax(self, sequence: List[float], alphabet_size: int = 4) -> np.ndarray:
        arr = np.array(sequence)
        if len(arr) == 0:
            return np.zeros(self.dimensions)

        arr = (arr - np.mean(arr)) / np.std(arr) if np.std(arr) > 0 else arr
        breakpoints = [
            [],
            [],
            [-0.43, 0.43],
            [-0.67, 0, 0.67],
            [-0.84, -0.25, 0.25, 0.84],
        ]
        if alphabet_size < len(breakpoints):
            bp = breakpoints[alphabet_size]
        else:
            bp = np.percentile(arr, np.linspace(0, 100, alphabet_size + 1)[1:-1])

        symbols = np.zeros(len(arr), dtype=int)
        for i, val in enumerate(arr):
            for j, b in enumerate(bp):
                if val < b:
                    symbols[i] = j
                    break
            else:
                symbols[i] = alphabet_size - 1

        vector = np.zeros(self.dimensions)
        n = min(len(symbols), self.dimensions)
        vector[:n] = symbols[:n] / alphabet_size

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def encode(self, sequence: List[float], method: str = "pooling") -> MindVector:
        data = self.encode_sequence(sequence, method)
        vector = MindVector(
            vector_type=MindVectorType.TEMPORAL,
            dimensions=self.dimensions,
        )
        vector.from_numpy(data)
        return vector


class MultimodalEncoder:
    """多模态编码器"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self.text_encoder = TextEncoder(EmbeddingConfig(dimensions=dimensions))
        self.numeric_encoder = NumericEncoder(dimensions)
        self.sequence_encoder = SequenceEncoder(dimensions)

    def encode_text_numeric(
        self,
        text: str,
        numeric_values: List[float],
        text_weight: float = 0.5,
    ) -> np.ndarray:
        text_vec = self.text_encoder.encode_semantic(text)
        num_vec = self.numeric_encoder.encode_values(numeric_values, "statistical")
        combined = text_weight * text_vec + (1 - text_weight) * num_vec
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined

    def encode_sequence_text(
        self,
        sequence: List[float],
        text: str,
        seq_weight: float = 0.5,
    ) -> np.ndarray:
        seq_vec = self.sequence_encoder.encode_sequence(sequence)
        text_vec = self.text_encoder.encode_semantic(text)
        combined = seq_weight * seq_vec + (1 - seq_weight) * text_vec
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined

    def encode_multimodal(
        self,
        modalities: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
    ) -> np.ndarray:
        weights = weights or {}
        vectors = []
        total_weight = 0.0

        if "text" in modalities:
            w = weights.get("text", 1.0)
            vec = self.text_encoder.encode_semantic(modalities["text"])
            vectors.append((vec, w))
            total_weight += w

        if "numeric" in modalities:
            w = weights.get("numeric", 1.0)
            vec = self.numeric_encoder.encode_values(modalities["numeric"], "statistical")
            vectors.append((vec, w))
            total_weight += w

        if "sequence" in modalities:
            w = weights.get("sequence", 1.0)
            vec = self.sequence_encoder.encode_sequence(modalities["sequence"])
            vectors.append((vec, w))
            total_weight += w

        if not vectors:
            return np.zeros(self.dimensions)

        combined = np.zeros(self.dimensions)
        for vec, w in vectors:
            combined += (w / total_weight) * vec

        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined

    def encode(
        self,
        modalities: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
    ) -> MindVector:
        data = self.encode_multimodal(modalities, weights)
        vector = MindVector(
            vector_type=MindVectorType.MULTIMODAL,
            dimensions=self.dimensions,
        )
        vector.from_numpy(data)
        return vector


class FeaturePipeline:
    """特征处理管道"""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self.steps: List[Callable[[np.ndarray], np.ndarray]] = []
        self.text_encoder = TextEncoder(EmbeddingConfig(dimensions=dimensions))
        self.numeric_encoder = NumericEncoder(dimensions)
        self.logger = get_logger(f"{__name__}.FeaturePipeline")

    def add_step(self, step: Callable[[np.ndarray], np.ndarray]) -> None:
        self.steps.append(step)

    def add_normalization(self, method: str = "l2") -> None:
        def normalize(vec: np.ndarray) -> np.ndarray:
            if method == "l2":
                norm = np.linalg.norm(vec)
                if norm > 0:
                    return vec / norm
            elif method == "minmax":
                min_val = np.min(vec)
                max_val = np.max(vec)
                if max_val > min_val:
                    return (vec - min_val) / (max_val - min_val)
            elif method == "zscore":
                mean = np.mean(vec)
                std = np.std(vec)
                if std > 0:
                    return (vec - mean) / std
            return vec
        self.add_step(normalize)

    def add_pca(self, output_dim: int) -> None:
        def pca_step(vec: np.ndarray) -> np.ndarray:
            if len(vec) <= output_dim:
                return vec
            return vec[:output_dim]
        self.add_step(pca_step)

    def add_noise(self, level: float = 0.01) -> None:
        def add_noise_fn(vec: np.ndarray) -> np.ndarray:
            noise = np.random.randn(len(vec)) * level
            return vec + noise
        self.add_step(add_noise_fn)

    def transform(self, vector: np.ndarray) -> np.ndarray:
        result = vector.copy()
        for step in self.steps:
            result = step(result)
        return result

    def encode_text(self, text: str, method: str = "semantic") -> np.ndarray:
        raw = self.text_encoder.encode(text, method)
        return self.transform(raw.to_numpy())

    def encode_numeric(self, values: List[float], method: str = "fourier") -> np.ndarray:
        raw = self.numeric_encoder.encode(values, method)
        return self.transform(raw.to_numpy())
