"""
熵模型模块

提供多种熵计算方法、熵场演化和熵驱动动力学功能。
"""

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.terrain.models import (
    EntropyConfig,
    EntropyField,
    EntropyType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class InformationEntropy:
    """信息熵计算器"""

    def __init__(self, base: float = 2.0, bins: int = 50):
        self.base = base
        self.bins = bins

    def shannon_entropy(self, data: np.ndarray) -> float:
        data_flat = data.flatten()
        hist, _ = np.histogram(data_flat, bins=self.bins, density=True)
        hist = hist[hist > 0]
        if len(hist) == 0:
            return 0.0
        probs = hist / hist.sum()
        return float(-np.sum(probs * np.log(probs) / np.log(self.base)))

    def renyi_entropy(self, data: np.ndarray, alpha: float = 2.0) -> float:
        if alpha == 1:
            return self.shannon_entropy(data)
        data_flat = data.flatten()
        hist, _ = np.histogram(data_flat, bins=self.bins, density=True)
        hist = hist[hist > 0]
        if len(hist) == 0:
            return 0.0
        probs = hist / hist.sum()
        return (1.0 / (1.0 - alpha)) * float(np.log(np.sum(probs ** alpha)) / np.log(self.base))

    def tsallis_entropy(self, data: np.ndarray, q: float = 1.0) -> float:
        if abs(q - 1.0) < 1e-10:
            return self.shannon_entropy(data)
        data_flat = data.flatten()
        hist, _ = np.histogram(data_flat, bins=self.bins, density=True)
        hist = hist[hist > 0]
        if len(hist) == 0:
            return 0.0
        probs = hist / hist.sum()
        return (1.0 / (q - 1.0)) * (1.0 - float(np.sum(probs ** q)))

    def permutation_entropy(self, data: np.ndarray, order: int = 3, delay: int = 1) -> float:
        if data.ndim > 1:
            data = data.flatten()
        n = len(data)
        if n < order * delay:
            return 0.0

        permutations = []
        for i in range(n - (order - 1) * delay):
            window = [data[i + j * delay] for j in range(order)]
            perm = tuple(np.argsort(window))
            permutations.append(perm)

        unique, counts = np.unique(permutations, return_counts=True, axis=0)
        probs = counts / counts.sum()
        return float(-np.sum(probs * np.log(probs) / np.log(self.base)))

    def sample_entropy(self, data: np.ndarray, m: int = 2, r: float = 0.2) -> float:
        if data.ndim > 1:
            data = data.flatten()
        n = len(data)
        if n < m + 1:
            return 0.0

        std = np.std(data)
        if std == 0:
            return 0.0
        r_std = r * std

        def _count_matches(data: np.ndarray, m: int, r: float) -> float:
            n = len(data) - m + 1
            count = 0
            for i in range(n):
                for j in range(i + 1, n):
                    if np.max(np.abs(data[i:i + m] - data[j:j + m])) < r:
                        count += 1
            return count

        A = _count_matches(data, m + 1, r_std)
        B = _count_matches(data, m, r_std)

        if B == 0 or A == 0:
            return 0.0
        return -float(np.log(A / B))


class TopologicalEntropy:
    """拓扑熵计算器"""

    def __init__(self):
        pass

    def topological_entropy(self, data: np.ndarray, threshold: float = 0.5) -> float:
        binary = data > threshold
        if binary.ndim == 1:
            return self._topological_1d(binary)
        elif binary.ndim == 2:
            return self._topological_2d(binary)
        return 0.0

    def _topological_1d(self, binary: np.ndarray) -> float:
        transitions = 0
        for i in range(1, len(binary)):
            if binary[i] != binary[i - 1]:
                transitions += 1
        return float(transitions / max(1, len(binary) - 1))

    def _topological_2d(self, binary: np.ndarray) -> float:
        h, w = binary.shape
        if h < 2 or w < 2:
            return 0.0

        components = self._count_components(binary)
        total_pixels = h * w
        return float(components / total_pixels) if total_pixels > 0 else 0.0

    def _count_components(self, binary: np.ndarray) -> int:
        h, w = binary.shape
        visited = np.zeros_like(binary, dtype=bool)
        components = 0

        for i in range(h):
            for j in range(w):
                if binary[i, j] and not visited[i, j]:
                    self._flood_fill(binary, visited, i, j)
                    components += 1
        return components

    def _flood_fill(self, binary: np.ndarray, visited: np.ndarray, i: int, j: int) -> None:
        h, w = binary.shape
        stack = [(i, j)]
        while stack:
            x, y = stack.pop()
            if x < 0 or x >= h or y < 0 or y >= w:
                continue
            if visited[x, y] or not binary[x, y]:
                continue
            visited[x, y] = True
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    def betti_numbers(self, data: np.ndarray, thresholds: List[float]) -> List[Tuple[int, int]]:
        result = []
        for t in thresholds:
            binary = data > t
            if binary.ndim == 2:
                components = self._count_components(binary)
                holes = self._count_holes(binary)
                result.append((components, holes))
        return result

    def _count_holes(self, binary: np.ndarray) -> int:
        h, w = binary.shape
        visited = np.zeros_like(binary, dtype=bool)
        holes = 0

        for i in range(1, h - 1):
            for j in range(1, w - 1):
                if not binary[i, j] and not visited[i, j]:
                    is_hole = self._check_hole(binary, visited, i, j)
                    if is_hole:
                        holes += 1
        return holes

    def _check_hole(self, binary: np.ndarray, visited: np.ndarray, i: int, j: int) -> bool:
        h, w = binary.shape
        stack = [(i, j)]
        is_enclosed = True
        while stack:
            x, y = stack.pop()
            if x <= 0 or x >= h - 1 or y <= 0 or y >= w - 1:
                is_enclosed = False
            if visited[x, y] or binary[x, y]:
                continue
            visited[x, y] = True
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
        return is_enclosed


class SpectralEntropy:
    """谱熵计算器"""

    def __init__(self, base: float = 2.0):
        self.base = base

    def spectral_entropy(self, data: np.ndarray) -> float:
        if data.ndim > 1:
            data = data.flatten()
        fft = np.fft.fft(data)
        power_spectrum = np.abs(fft) ** 2
        total_power = np.sum(power_spectrum)
        if total_power == 0:
            return 0.0
        probs = power_spectrum / total_power
        probs = probs[probs > 0]
        return float(-np.sum(probs * np.log(probs) / np.log(self.base)))

    def wavelet_entropy(self, data: np.ndarray, levels: int = 4) -> float:
        if data.ndim > 1:
            data = data.flatten()
        n = len(data)
        if n < 2:
            return 0.0

        energies = []
        current = data.copy()
        for _ in range(levels):
            half = len(current) // 2
            if half == 0:
                break
            approx = current[:half]
            detail = current[half:]
            energies.append(np.sum(detail ** 2))
            current = approx
        energies.append(np.sum(current ** 2))

        total_energy = sum(energies)
        if total_energy == 0:
            return 0.0
        probs = np.array(energies) / total_energy
        probs = probs[probs > 0]
        return float(-np.sum(probs * np.log(probs) / np.log(self.base)))

    def hilbert_spectral_entropy(self, data: np.ndarray) -> float:
        if data.ndim > 1:
            data = data.flatten()
        n = len(data)
        if n < 2:
            return 0.0

        analytic = self._hilbert_transform(data)
        amplitude = np.abs(analytic)
        total_amp = np.sum(amplitude)
        if total_amp == 0:
            return 0.0
        probs = amplitude / total_amp
        probs = probs[probs > 0]
        return float(-np.sum(probs * np.log(probs) / np.log(self.base)))

    def _hilbert_transform(self, x: np.ndarray) -> np.ndarray:
        n = len(x)
        fft = np.fft.fft(x)
        h = np.zeros(n)
        if n > 0:
            h[0] = 1
            if n % 2 == 0:
                h[1:n // 2] = 2
                h[n // 2] = 1
            else:
                h[1:(n + 1) // 2] = 2
        return np.fft.ifft(fft * h)


class EntropyCalculator:
    """熵计算器 - 整合多种熵计算方法"""

    def __init__(self, config: Optional[EntropyConfig] = None):
        self.config = config or EntropyConfig()
        self.info_entropy = InformationEntropy(base=self.config.base, bins=self.config.bins)
        self.topo_entropy = TopologicalEntropy()
        self.spectral_entropy = SpectralEntropy(base=self.config.base)

    def calculate(self, data: np.ndarray, entropy_type: Optional[EntropyType] = None) -> float:
        etype = entropy_type or self.config.entropy_type
        if etype == EntropyType.SHANNON:
            return self.info_entropy.shannon_entropy(data)
        elif etype == EntropyType.RENYI:
            return self.info_entropy.renyi_entropy(data, self.config.alpha)
        elif etype == EntropyType.TSALLIS:
            return self.info_entropy.tsallis_entropy(data, self.config.q)
        elif etype == EntropyType.PERMUTATION:
            return self.info_entropy.permutation_entropy(data)
        elif etype == EntropyType.SAMPLE:
            return self.info_entropy.sample_entropy(data)
        elif etype == EntropyType.TOPOLOGICAL:
            return self.topo_entropy.topological_entropy(data)
        elif etype == EntropyType.SPECTRAL:
            return self.spectral_entropy.spectral_entropy(data)
        elif etype == EntropyType.WAVELET:
            return self.spectral_entropy.wavelet_entropy(data)
        elif etype == EntropyType.MULTISCALE:
            return self.multiscale_entropy(data)
        else:
            return self.info_entropy.shannon_entropy(data)

    def calculate_local_entropy(
        self,
        data: np.ndarray,
        window_size: int = 16,
        stride: int = 8,
    ) -> np.ndarray:
        if data.ndim == 1:
            return self._local_entropy_1d(data, window_size, stride)
        elif data.ndim == 2:
            return self._local_entropy_2d(data, window_size, stride)
        return np.zeros_like(data)

    def _local_entropy_1d(self, data: np.ndarray, window: int, stride: int) -> np.ndarray:
        n = len(data)
        result = np.zeros(n)
        counts = np.zeros(n)
        for i in range(0, n - window + 1, stride):
            window_data = data[i:i + window]
            ent = self.info_entropy.shannon_entropy(window_data)
            result[i:i + window] += ent
            counts[i:i + window] += 1
        counts[counts == 0] = 1
        return result / counts

    def _local_entropy_2d(self, data: np.ndarray, window: int, stride: int) -> np.ndarray:
        h, w = data.shape
        result = np.zeros((h, w))
        counts = np.zeros((h, w))
        for i in range(0, h - window + 1, stride):
            for j in range(0, w - window + 1, stride):
                window_data = data[i:i + window, j:j + window]
                ent = self.info_entropy.shannon_entropy(window_data)
                result[i:i + window, j:j + window] += ent
                counts[i:i + window, j:j + window] += 1
        counts[counts == 0] = 1
        return result / counts

    def multiscale_entropy(self, data: np.ndarray, scales: Optional[List[int]] = None) -> float:
        scales = scales or self.config.scales
        entropies = []
        for scale in scales:
            coarse = self._coarse_grain(data, scale)
            if len(coarse) > 1:
                ent = self.info_entropy.shannon_entropy(coarse)
                entropies.append(ent)
        return float(np.mean(entropies)) if entropies else 0.0

    def _coarse_grain(self, data: np.ndarray, scale: int) -> np.ndarray:
        if data.ndim > 1:
            data = data.flatten()
        n = len(data)
        n_new = n // scale
        if n_new == 0:
            return data
        reshaped = data[:n_new * scale].reshape(n_new, scale)
        return np.mean(reshaped, axis=1)

    def entropy_profile(self, data: np.ndarray, scales: Optional[List[int]] = None) -> List[float]:
        scales = scales or self.config.scales
        return [self.multiscale_entropy(data, [s]) for s in scales]


class EntropyFieldEvolver:
    """熵场演化器"""

    def __init__(self, config: Optional[EntropyConfig] = None):
        self.config = config or EntropyConfig()
        self.logger = get_logger(f"{__name__}.EntropyFieldEvolver")

    def diffuse(self, field: np.ndarray, steps: int = 1, rate: Optional[float] = None) -> np.ndarray:
        rate = rate if rate is not None else self.config.diffusion_rate
        result = field.copy()
        for _ in range(steps):
            laplacian = self._laplacian(result)
            result += rate * laplacian
        return result

    def reaction_diffusion(
        self,
        field: np.ndarray,
        steps: int = 1,
        diffusion_rate: Optional[float] = None,
        reaction_rate: Optional[float] = None,
    ) -> np.ndarray:
        dr = diffusion_rate if diffusion_rate is not None else self.config.diffusion_rate
        rr = reaction_rate if reaction_rate is not None else self.config.reaction_rate
        result = field.copy()
        for _ in range(steps):
            laplacian = self._laplacian(result)
            reaction = result * (1 - result) * (result - 0.5)
            result += dr * laplacian + rr * reaction
            result = np.clip(result, 0, 1)
        return result

    def _laplacian(self, field: np.ndarray) -> np.ndarray:
        if field.ndim == 1:
            return np.roll(field, 1) + np.roll(field, -1) - 2 * field
        elif field.ndim == 2:
            return (
                np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0)
                + np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
                - 4 * field
            )
        return np.zeros_like(field)

    def entropy_growth(self, field: np.ndarray, rate: Optional[float] = None) -> np.ndarray:
        rate = rate if rate is not None else self.config.evolution_rate
        noise = np.random.randn(*field.shape) * 0.01
        growth = rate * field * (1 - field)
        return np.clip(field + growth + noise, 0, 1)

    def maximize_entropy(self, field: np.ndarray, iterations: int = 100) -> np.ndarray:
        result = field.copy()
        for _ in range(iterations):
            result = self.diffuse(result, steps=1, rate=0.1)
            current_ent = self._shannon(result)
            if current_ent >= np.log2(field.size):
                break
        return result

    def _shannon(self, data: np.ndarray) -> float:
        flat = data.flatten()
        hist, _ = np.histogram(flat, bins=50, density=True)
        hist = hist[hist > 0]
        if len(hist) == 0:
            return 0.0
        probs = hist / hist.sum()
        return float(-np.sum(probs * np.log2(probs)))

    def evolve(
        self,
        entropy_field: EntropyField,
        steps: int = 1,
        method: str = "diffusion",
    ) -> EntropyField:
        data = entropy_field.to_numpy()

        if method == "diffusion":
            new_data = self.diffuse(data, steps)
        elif method == "reaction_diffusion":
            new_data = self.reaction_diffusion(data, steps)
        elif method == "growth":
            new_data = self.entropy_growth(data)
        else:
            new_data = data

        new_field = EntropyField(
            name=entropy_field.name,
            dimensions=list(new_data.shape),
            entropy_type=entropy_field.entropy_type,
            time_step=entropy_field.time_step + steps,
            evolution_rate=self.config.evolution_rate,
        )
        new_field.from_numpy(new_data)
        return new_field


class EntropyDynamics:
    """熵动力学系统"""

    def __init__(self, n_variables: int = 3):
        self.n_variables = n_variables
        self.state = np.random.rand(n_variables)
        self.time = 0
        self.history: List[np.ndarray] = []

    def step_entropy_production(self, dt: float = 0.01) -> np.ndarray:
        state = self.state.copy()
        ds = np.zeros_like(state)
        for i in range(self.n_variables):
            interaction = 0
            for j in range(self.n_variables):
                if i != j:
                    interaction += state[j] - state[i]
            ds[i] = interaction * dt + 0.01 * np.random.randn() * np.sqrt(dt)
        self.state = np.clip(self.state + ds, 0, 1)
        self.time += dt
        self.history.append(self.state.copy())
        return self.state

    def entropy(self) -> float:
        state = self.state[self.state > 0]
        if len(state) == 0:
            return 0.0
        probs = state / state.sum()
        return float(-np.sum(probs * np.log2(probs)))

    def free_energy(self, temperature: float = 1.0) -> float:
        energy = np.sum(self.state ** 2)
        entropy = self.entropy()
        return energy - temperature * entropy

    def reset(self) -> None:
        self.state = np.random.rand(self.n_variables)
        self.time = 0
        self.history = []
