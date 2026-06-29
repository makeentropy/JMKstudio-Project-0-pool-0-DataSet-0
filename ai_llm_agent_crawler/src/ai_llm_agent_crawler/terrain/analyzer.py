"""
地形分析模块

提供地形特征提取、梯度分析、临界点检测、地形分类等功能。
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.terrain.models import (
    TerrainFeature,
    TerrainMap,
    TerrainType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class GradientAnalyzer:
    """梯度分析器"""

    def __init__(self):
        pass

    def calculate_gradient(self, height_map: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if height_map.ndim == 2:
            gy, gx = np.gradient(height_map)
            return gx, gy
        return np.zeros_like(height_map), np.zeros_like(height_map)

    def calculate_slope(self, height_map: np.ndarray) -> np.ndarray:
        gx, gy = self.calculate_gradient(height_map)
        return np.sqrt(gx ** 2 + gy ** 2)

    def calculate_aspect(self, height_map: np.ndarray) -> np.ndarray:
        gx, gy = self.calculate_gradient(height_map)
        aspect = np.arctan2(-gy, gx)
        aspect = np.degrees(aspect)
        aspect[aspect < 0] += 360
        return aspect

    def calculate_curvature(self, height_map: np.ndarray) -> np.ndarray:
        if height_map.ndim != 2:
            return np.zeros_like(height_map)
        gy, gx = np.gradient(height_map)
        gxx, gxy = np.gradient(gx)
        gyx, gyy = np.gradient(gy)
        curvature = gxx + gyy
        return curvature

    def calculate_plan_curvature(self, height_map: np.ndarray) -> np.ndarray:
        gx, gy = self.calculate_gradient(height_map)
        gxx, gxy = np.gradient(gx)
        gyx, gyy = np.gradient(gy)
        denom = gx ** 2 + gy ** 2
        denom[denom == 0] = 1e-10
        plan_curv = (gyy * gx ** 2 - 2 * gxy * gx * gy + gxx * gy ** 2) / (denom ** 1.5)
        return plan_curv

    def calculate_profile_curvature(self, height_map: np.ndarray) -> np.ndarray:
        gx, gy = self.calculate_gradient(height_map)
        gxx, gxy = np.gradient(gx)
        gyx, gyy = np.gradient(gy)
        denom = gx ** 2 + gy ** 2
        denom[denom == 0] = 1e-10
        profile_curv = (gxx * gx ** 2 + 2 * gxy * gx * gy + gyy * gy ** 2) / (denom ** 1.5)
        return profile_curv

    def calculate_ruggedness(self, height_map: np.ndarray, window: int = 3) -> np.ndarray:
        h, w = height_map.shape
        result = np.zeros_like(height_map)
        pad = window // 2
        padded = np.pad(height_map, pad, mode="reflect")

        for i in range(h):
            for j in range(w):
                region = padded[i:i + window, j:j + window]
                center = region[pad, pad]
                diffs = np.abs(region - center)
                result[i, j] = np.mean(diffs)
        return result

    def calculate_roughness(self, height_map: np.ndarray) -> np.ndarray:
        slope = self.calculate_slope(height_map)
        return np.sin(np.radians(slope * 100))


class CriticalPointDetector:
    """临界点检测器"""

    def __init__(self):
        pass

    def find_peaks(self, height_map: np.ndarray, min_distance: int = 5) -> List[Tuple[int, int]]:
        peaks = []
        h, w = height_map.shape
        for i in range(1, h - 1):
            for j in range(1, w - 1):
                center = height_map[i, j]
                is_peak = True
                for di in [-1, 0, 1]:
                    for dj in [-1, 0, 1]:
                        if di == 0 and dj == 0:
                            continue
                        if height_map[i + di, j + dj] >= center:
                            is_peak = False
                            break
                    if not is_peak:
                        break
                if is_peak:
                    peaks.append((i, j))
        return self._suppress_non_max(height_map, peaks, min_distance)

    def find_valleys(self, height_map: np.ndarray, min_distance: int = 5) -> List[Tuple[int, int]]:
        inverted = -height_map
        return self.find_peaks(inverted, min_distance)

    def find_saddles(self, height_map: np.ndarray) -> List[Tuple[int, int]]:
        saddles = []
        h, w = height_map.shape
        gx, gy = np.gradient(height_map)
        gxx, gxy = np.gradient(gx)
        gyx, gyy = np.gradient(gy)

        for i in range(1, h - 1):
            for j in range(1, w - 1):
                hessian = np.array([
                    [gxx[i, j], gxy[i, j]],
                    [gyx[i, j], gyy[i, j]]
                ])
                eigenvalues = np.linalg.eigvalsh(hessian)
                if eigenvalues[0] < 0 and eigenvalues[1] > 0:
                    saddles.append((i, j))
        return saddles

    def find_critical_points(self, height_map: np.ndarray) -> Dict[str, List[Tuple[int, int]]]:
        return {
            "peaks": self.find_peaks(height_map),
            "valleys": self.find_valleys(height_map),
            "saddles": self.find_saddles(height_map),
        }

    def _suppress_non_max(
        self,
        height_map: np.ndarray,
        points: List[Tuple[int, int]],
        min_distance: int,
    ) -> List[Tuple[int, int]]:
        if not points:
            return []

        sorted_points = sorted(points, key=lambda p: height_map[p[0], p[1]], reverse=True)
        selected = []
        for p in sorted_points:
            too_close = False
            for s in selected:
                dist = np.sqrt((p[0] - s[0]) ** 2 + (p[1] - s[1]) ** 2)
                if dist < min_distance:
                    too_close = True
                    break
            if not too_close:
                selected.append(p)
        return selected

    def calculate_prominence(
        self,
        height_map: np.ndarray,
        peak: Tuple[int, int],
    ) -> float:
        from collections import deque
        h, w = height_map.shape
        peak_height = height_map[peak]

        visited = np.zeros((h, w), dtype=bool)
        queue = deque([peak])
        visited[peak] = True
        min_saddle = float("inf")
        found_saddle = False

        while queue:
            i, j = queue.popleft()
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < h and 0 <= nj < w and not visited[ni, nj]:
                        if height_map[ni, nj] >= peak_height:
                            continue
                        visited[ni, nj] = True
                        if height_map[ni, nj] < min_saddle:
                            min_saddle = height_map[ni, nj]
                            found_saddle = True
                        queue.append((ni, nj))
        if found_saddle:
            return peak_height - min_saddle
        return peak_height


class FeatureExtractor:
    """特征提取器"""

    def __init__(self):
        self.gradient_analyzer = GradientAnalyzer()
        self.critical_detector = CriticalPointDetector()

    def extract_statistical_features(self, height_map: np.ndarray) -> Dict[str, float]:
        flat = height_map.flatten()
        return {
            "mean": float(np.mean(flat)),
            "std": float(np.std(flat)),
            "min": float(np.min(flat)),
            "max": float(np.max(flat)),
            "range": float(np.max(flat) - np.min(flat)),
            "median": float(np.median(flat)),
            "skewness": float(self._skewness(flat)),
            "kurtosis": float(self._kurtosis(flat)),
            "percentile_25": float(np.percentile(flat, 25)),
            "percentile_75": float(np.percentile(flat, 75)),
            "iqr": float(np.percentile(flat, 75) - np.percentile(flat, 25)),
        }

    def _skewness(self, data: np.ndarray) -> float:
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return float(np.mean(((data - mean) / std) ** 3))

    def _kurtosis(self, data: np.ndarray) -> float:
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return float(np.mean(((data - mean) / std) ** 4) - 3)

    def extract_terrain_features(self, terrain_map: TerrainMap) -> List[TerrainFeature]:
        features = []
        height_arr = np.array(terrain_map.height_map)

        peaks = self.critical_detector.find_peaks(height_arr, min_distance=10)
        for idx, (y, x) in enumerate(peaks):
            prominence = self.critical_detector.calculate_prominence(height_arr, (y, x))
            size, boundary = self._find_region(height_arr, x, y, is_peak=True)
            features.append(TerrainFeature(
                name=f"peak_{idx}",
                feature_type="peak",
                center=(float(x), float(y)),
                size=size,
                height_range=(height_arr[y, x] - prominence, height_arr[y, x]),
                boundary_points=boundary,
                area=float(size * terrain_map.resolution ** 2),
                prominence=prominence,
                confidence=0.9,
            ))

        valleys = self.critical_detector.find_valleys(height_arr, min_distance=10)
        for idx, (y, x) in enumerate(valleys):
            size, boundary = self._find_region(height_arr, x, y, is_peak=False)
            features.append(TerrainFeature(
                name=f"valley_{idx}",
                feature_type="valley",
                center=(float(x), float(y)),
                size=size,
                height_range=(height_arr[y, x], height_arr[y, x] + size * 0.5),
                boundary_points=boundary,
                area=float(size * terrain_map.resolution ** 2),
                prominence=float(size * 0.1),
                confidence=0.85,
            ))

        return features

    def _find_region(
        self,
        height_map: np.ndarray,
        x: int,
        y: int,
        is_peak: bool = True,
        threshold: float = 0.5,
    ) -> Tuple[int, List[Tuple[int, int]]]:
        from collections import deque
        h, w = height_map.shape
        center_val = height_map[y, x]
        visited = set()
        queue = deque([(y, x)])
        visited.add((y, x))
        boundary = []

        while queue:
            cy, cx = queue.popleft()
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in visited:
                        val = height_map[ny, nx]
                        if is_peak:
                            if val >= center_val * (1 - threshold):
                                visited.add((ny, nx))
                                queue.append((ny, nx))
                            else:
                                boundary.append((nx, ny))
                        else:
                            if val <= center_val * (1 + threshold):
                                visited.add((ny, nx))
                                queue.append((ny, nx))
                            else:
                                boundary.append((nx, ny))

        return len(visited), boundary[:100]

    def extract_fractal_dimension(self, height_map: np.ndarray) -> float:
        h, w = height_map.shape
        sizes = [2, 4, 8, 16, 32]
        counts = []

        for size in sizes:
            if size >= min(h, w):
                break
            grid_h = h // size
            grid_w = w // size
            if grid_h == 0 or grid_w == 0:
                continue
            count = 0
            for i in range(grid_h):
                for j in range(grid_w):
                    region = height_map[i * size:(i + 1) * size, j * size:(j + 1) * size]
                    if np.max(region) - np.min(region) > 0.01:
                        count += 1
            if count > 0:
                counts.append((np.log(count), np.log(1.0 / size)))

        if len(counts) < 2:
            return 2.0
        counts_arr = np.array(counts)
        slope, _ = np.polyfit(counts_arr[:, 1], counts_arr[:, 0], 1)
        return float(slope + 1)


class TerrainClassifier:
    """地形分类器"""

    def __init__(self):
        self.gradient_analyzer = GradientAnalyzer()

    def classify_terrain_types(self, terrain_map: TerrainMap) -> np.ndarray:
        height_arr = np.array(terrain_map.height_map)
        entropy_arr = np.array(terrain_map.entropy_map) if terrain_map.entropy_map else np.zeros_like(height_arr)
        slope = self.gradient_analyzer.calculate_slope(height_arr)
        curvature = self.gradient_analyzer.calculate_curvature(height_arr)

        h, w = height_arr.shape
        type_map = np.full((h, w), TerrainType.PLAIN.value, dtype=object)

        height_norm = self._normalize(height_arr)
        slope_norm = self._normalize(slope)
        entropy_norm = self._normalize(entropy_arr)

        for i in range(h):
            for j in range(w):
                h_val = height_norm[i, j]
                s_val = slope_norm[i, j]
                e_val = entropy_norm[i, j]

                if h_val < 0.3:
                    if e_val < 0.4:
                        type_map[i, j] = TerrainType.BASIN.value
                    else:
                        type_map[i, j] = TerrainType.CANYON.value
                elif h_val < 0.6:
                    if s_val < 0.2:
                        if e_val < 0.5:
                            type_map[i, j] = TerrainType.PLAIN.value
                        else:
                            type_map[i, j] = TerrainType.HILLS.value
                    elif s_val < 0.5:
                        type_map[i, j] = TerrainType.HILLS.value
                    else:
                        if e_val > 0.6:
                            type_map[i, j] = TerrainType.CLIFF.value
                        else:
                            type_map[i, j] = TerrainType.RIDGE.value
                else:
                    if s_val < 0.2:
                        type_map[i, j] = TerrainType.PLATEAU.value
                    elif s_val < 0.5:
                        type_map[i, j] = TerrainType.MOUNTAIN.value
                    else:
                        if e_val > 0.7:
                            type_map[i, j] = TerrainType.VOLCANO.value
                        else:
                            type_map[i, j] = TerrainType.MOUNTAIN.value

                if curvature[i, j] < -0.01 and h_val > 0.5:
                    type_map[i, j] = TerrainType.VALLEY.value
                if curvature[i, j] > 0.01 and h_val > 0.7:
                    type_map[i, j] = TerrainType.RIDGE.value

        return type_map

    def _normalize(self, arr: np.ndarray) -> np.ndarray:
        min_val = arr.min()
        max_val = arr.max()
        if max_val == min_val:
            return np.zeros_like(arr)
        return (arr - min_val) / (max_val - min_val)

    def calculate_terrain_distribution(
        self,
        type_map: np.ndarray,
    ) -> Dict[str, float]:
        unique, counts = np.unique(type_map, return_counts=True)
        total = counts.sum()
        return {str(u): float(c / total) for u, c in zip(unique, counts)}


class TerrainAnalyzer:
    """地形分析器 - 整合所有分析功能"""

    def __init__(self):
        self.gradient = GradientAnalyzer()
        self.critical = CriticalPointDetector()
        self.features = FeatureExtractor()
        self.classifier = TerrainClassifier()
        self.logger = get_logger(f"{__name__}.TerrainAnalyzer")

    def full_analysis(self, terrain_map: TerrainMap) -> Dict[str, Any]:
        height_arr = np.array(terrain_map.height_map)
        entropy_arr = np.array(terrain_map.entropy_map) if terrain_map.entropy_map else None

        stats = self.features.extract_statistical_features(height_arr)
        slope = self.gradient.calculate_slope(height_arr)
        aspect = self.gradient.calculate_aspect(height_arr)
        curvature = self.gradient.calculate_curvature(height_arr)
        roughness = self.gradient.calculate_roughness(height_arr)

        critical_points = self.critical.find_critical_points(height_arr)
        terrain_features = self.features.extract_terrain_features(terrain_map)
        type_map = self.classifier.classify_terrain_types(terrain_map)
        distribution = self.classifier.calculate_terrain_distribution(type_map)
        fractal_dim = self.features.extract_fractal_dimension(height_arr)

        result = {
            "statistics": stats,
            "slope": {
                "mean": float(np.mean(slope)),
                "max": float(np.max(slope)),
                "std": float(np.std(slope)),
            },
            "curvature": {
                "mean": float(np.mean(curvature)),
                "min": float(np.min(curvature)),
                "max": float(np.max(curvature)),
            },
            "roughness": {
                "mean": float(np.mean(roughness)),
                "max": float(np.max(roughness)),
            },
            "critical_points": {
                "peaks": len(critical_points["peaks"]),
                "valleys": len(critical_points["valleys"]),
                "saddles": len(critical_points["saddles"]),
            },
            "features_count": len(terrain_features),
            "terrain_distribution": distribution,
            "fractal_dimension": fractal_dim,
        }

        if entropy_arr is not None:
            result["entropy_statistics"] = self.features.extract_statistical_features(entropy_arr)

        self.logger.info(
            f"Terrain analysis complete: {len(terrain_features)} features, "
            f"fractal dimension: {fractal_dim:.3f}"
        )
        return result

    def analyze_region(
        self,
        terrain_map: TerrainMap,
        x: int,
        y: int,
        radius: int = 20,
    ) -> Dict[str, Any]:
        height_arr = np.array(terrain_map.height_map)
        h, w = height_arr.shape

        x0 = max(0, x - radius)
        x1 = min(w, x + radius)
        y0 = max(0, y - radius)
        y1 = min(h, y + radius)

        region = height_arr[y0:y1, x0:x1]

        if region.size == 0:
            return {}

        stats = self.features.extract_statistical_features(region)
        slope = self.gradient.calculate_slope(region)
        curvature = self.gradient.calculate_curvature(region)

        return {
            "center": (x, y),
            "radius": radius,
            "size": (y1 - y0, x1 - x0),
            "statistics": stats,
            "slope_mean": float(np.mean(slope)),
            "curvature_mean": float(np.mean(curvature)),
            "local_height": height_arr[y, x] if 0 <= y < h and 0 <= x < w else 0.0,
        }
