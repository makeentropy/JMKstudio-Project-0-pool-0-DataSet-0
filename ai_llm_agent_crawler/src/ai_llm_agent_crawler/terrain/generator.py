"""
地形生成模块

提供基于噪声、分形、熵驱动的多维地形生成功能。
"""

import math
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.terrain.models import (
    EntropyField,
    TerrainCell,
    TerrainConfig,
    TerrainMap,
    TerrainPoint,
    TerrainType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class NoiseGenerator:
    """噪声生成器"""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = np.random.RandomState(seed)
        self._permutation = self._generate_permutation()

    def _generate_permutation(self) -> np.ndarray:
        p = np.arange(256, dtype=int)
        self._rng.shuffle(p)
        return np.concatenate([p, p])

    def set_seed(self, seed: int) -> None:
        self.seed = seed
        self._rng = np.random.RandomState(seed)
        self._permutation = self._generate_permutation()

    def _fade(self, t: np.ndarray) -> np.ndarray:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
        return a + t * (b - a)

    def _grad(self, hash_value: int, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        h = hash_value & 3
        u = np.where(h < 2, x, y)
        v = np.where(h < 2, y, x)
        return np.where((h & 1) == 0, u, -u) + np.where((h & 2) == 0, v, -v)

    def perlin_2d(self, width: int, height: int, scale: float = 50.0) -> np.ndarray:
        x = np.linspace(0, width / scale, width)
        y = np.linspace(0, height / scale, height)
        xv, yv = np.meshgrid(x, y)

        xi = xv.astype(int) & 255
        yi = yv.astype(int) & 255
        xf = xv - xi
        yf = yv - yi

        u = self._fade(xf)
        v = self._fade(yf)

        p = self._permutation
        aa = p[p[xi] + yi]
        ab = p[p[xi] + yi + 1]
        ba = p[p[xi + 1] + yi]
        bb = p[p[xi + 1] + yi + 1]

        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1), self._grad(bb, xf - 1, yf - 1), u)

        result = self._lerp(x1, x2, v)
        return (result + 1) / 2

    def simplex_2d(self, width: int, height: int, scale: float = 50.0) -> np.ndarray:
        noise = np.zeros((height, width))
        for y in range(height):
            for x in range(width):
                nx = x / scale
                ny = y / scale
                noise[y, x] = self._simplex_point(nx, ny)
        return (noise + 1) / 2

    def _simplex_point(self, x: float, y: float) -> float:
        F2 = 0.5 * (math.sqrt(3.0) - 1.0)
        G2 = (3.0 - math.sqrt(3.0)) / 6.0

        s = (x + y) * F2
        i = int(math.floor(x + s))
        j = int(math.floor(y + s))

        t = (i + j) * G2
        X0 = i - t
        Y0 = j - t
        x0 = x - X0
        y0 = y - Y0

        if x0 > y0:
            i1, j1 = 1, 0
        else:
            i1, j1 = 0, 1

        x1 = x0 - i1 + G2
        y1 = y0 - j1 + G2
        x2 = x0 - 1.0 + 2.0 * G2
        y2 = y0 - 1.0 + 2.0 * G2

        ii = i & 255
        jj = j & 255

        n0 = n1 = n2 = 0.0

        t0 = 0.5 - x0 * x0 - y0 * y0
        if t0 >= 0:
            t0 *= t0
            n0 = t0 * t0 * self._dot_grid_gradient(ii, jj, x0, y0)

        t1 = 0.5 - x1 * x1 - y1 * y1
        if t1 >= 0:
            t1 *= t1
            n1 = t1 * t1 * self._dot_grid_gradient(ii + i1, jj + j1, x1, y1)

        t2 = 0.5 - x2 * x2 - y2 * y2
        if t2 >= 0:
            t2 *= t2
            n2 = t2 * t2 * self._dot_grid_gradient(ii + 1, jj + 1, x2, y2)

        return 70.0 * (n0 + n1 + n2)

    def _dot_grid_gradient(self, ix: int, iy: int, x: float, y: float) -> float:
        p = self._permutation
        gradient_vectors = [
            [1, 1], [-1, 1], [1, -1], [-1, -1],
            [1, 0], [-1, 0], [0, 1], [0, -1],
        ]
        idx = p[(ix + p[iy]) & 7]
        g = gradient_vectors[idx & 7]
        return g[0] * x + g[1] * y

    def value_noise_2d(self, width: int, height: int, scale: float = 50.0) -> np.ndarray:
        grid_w = max(2, int(width / scale) + 2)
        grid_h = max(2, int(height / scale) + 2)
        grid = self._rng.rand(grid_h, grid_w)

        x_coords = np.linspace(0, grid_w - 1, width)
        y_coords = np.linspace(0, grid_h - 1, height)
        xv, yv = np.meshgrid(x_coords, y_coords)

        x0 = np.floor(xv).astype(int)
        x1 = x0 + 1
        y0 = np.floor(yv).astype(int)
        y1 = y0 + 1

        x1 = np.clip(x1, 0, grid_w - 1)
        y1 = np.clip(y1, 0, grid_h - 1)

        sx = xv - x0
        sy = yv - y0
        sx = self._fade(sx)
        sy = self._fade(sy)

        v00 = grid[y0, x0]
        v10 = grid[y0, x1]
        v01 = grid[y1, x0]
        v11 = grid[y1, x1]

        a = self._lerp(v00, v10, sx)
        b = self._lerp(v01, v11, sx)
        return self._lerp(a, b, sy)

    def white_noise(self, width: int, height: int) -> np.ndarray:
        return self._rng.rand(height, width)


class FractalGenerator:
    """分形地形生成器"""

    def __init__(self, seed: int = 42, noise_generator: Optional[NoiseGenerator] = None):
        self.noise_generator = noise_generator or NoiseGenerator(seed)
        self.logger = get_logger(f"{__name__}.FractalGenerator")

    def fbm(
        self,
        width: int,
        height: int,
        octaves: int = 6,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        scale: float = 50.0,
        noise_type: str = "perlin",
    ) -> np.ndarray:
        result = np.zeros((height, width))
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            if noise_type == "perlin":
                noise = self.noise_generator.perlin_2d(width, height, scale / frequency)
            elif noise_type == "simplex":
                noise = self.noise_generator.simplex_2d(width, height, scale / frequency)
            else:
                noise = self.noise_generator.value_noise_2d(width, height, scale / frequency)

            result += noise * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return result / max_value if max_value > 0 else result

    def ridged_multi(
        self,
        width: int,
        height: int,
        octaves: int = 6,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        scale: float = 50.0,
        offset: float = 1.0,
        gain: float = 2.0,
    ) -> np.ndarray:
        result = np.zeros((height, width))
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0
        prev = np.ones((height, width))

        for _ in range(octaves):
            noise = self.noise_generator.perlin_2d(width, height, scale / frequency)
            noise = offset - np.abs(noise * 2 - offset)
            noise = noise * noise * prev
            prev = noise * gain
            result += noise * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return result / max_value if max_value > 0 else result

    def billow(
        self,
        width: int,
        height: int,
        octaves: int = 6,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        scale: float = 50.0,
    ) -> np.ndarray:
        result = np.zeros((height, width))
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            noise = self.noise_generator.perlin_2d(width, height, scale / frequency)
            noise = np.abs(noise * 2 - 1)
            result += noise * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return result / max_value if max_value > 0 else result


class EntropyDrivenGenerator:
    """熵驱动地形生成器"""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = np.random.RandomState(seed)
        self.logger = get_logger(f"{__name__}.EntropyDrivenGenerator")

    def generate_from_entropy_field(
        self,
        entropy_field: np.ndarray,
        base_height: float = 0.5,
        height_multiplier: float = 1.0,
        coupling: float = 0.5,
    ) -> np.ndarray:
        height_map = np.zeros_like(entropy_field)

        gradient_x, gradient_y = np.gradient(entropy_field)
        gradient_magnitude = np.sqrt(gradient_x ** 2 + gradient_y ** 2)

        normalized_entropy = self._normalize(entropy_field)
        normalized_gradient = self._normalize(gradient_magnitude)

        height_map = (
            base_height
            + coupling * normalized_entropy * height_multiplier
            + (1 - coupling) * normalized_gradient * height_multiplier * 0.5
        )

        smooth = self._gaussian_blur(height_map, 2)
        detail = (height_map - smooth) * 0.3
        height_map = smooth + detail

        return np.clip(height_map, 0, 1)

    def entropic_displacement(
        self,
        base_terrain: np.ndarray,
        entropy_field: np.ndarray,
        strength: float = 0.3,
    ) -> np.ndarray:
        normalized_entropy = self._normalize(entropy_field)
        displacement = self._rng.randn(*base_terrain.shape) * 0.1
        weighted_displacement = displacement * normalized_entropy * strength
        return np.clip(base_terrain + weighted_displacement, 0, 1)

    def entropy_biome_mapping(
        self,
        height_map: np.ndarray,
        entropy_map: np.ndarray,
        water_level: float = 0.3,
        mountain_level: float = 0.7,
    ) -> np.ndarray:
        terrain_types = np.zeros_like(height_map, dtype=int)

        for i in range(height_map.shape[0]):
            for j in range(height_map.shape[1]):
                h = height_map[i, j]
                e = entropy_map[i, j]

                if h < water_level:
                    if e < 0.3:
                        terrain_types[i, j] = 0
                    elif e < 0.6:
                        terrain_types[i, j] = 1
                    else:
                        terrain_types[i, j] = 2
                elif h < mountain_level:
                    if e < 0.3:
                        terrain_types[i, j] = 3
                    elif e < 0.6:
                        terrain_types[i, j] = 4
                    else:
                        terrain_types[i, j] = 5
                else:
                    if e < 0.3:
                        terrain_types[i, j] = 6
                    elif e < 0.6:
                        terrain_types[i, j] = 7
                    else:
                        terrain_types[i, j] = 8

        return terrain_types

    def _normalize(self, arr: np.ndarray) -> np.ndarray:
        min_val = arr.min()
        max_val = arr.max()
        if max_val == min_val:
            return np.zeros_like(arr)
        return (arr - min_val) / (max_val - min_val)

    def _gaussian_blur(self, arr: np.ndarray, sigma: float = 1.0) -> np.ndarray:
        size = int(sigma * 3) * 2 + 1
        x = np.arange(size) - size // 2
        g = np.exp(-x ** 2 / (2 * sigma ** 2))
        kernel = np.outer(g, g)
        kernel /= kernel.sum()

        padded = np.pad(arr, size // 2, mode="reflect")
        result = np.zeros_like(arr)
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                result[i, j] = np.sum(padded[i:i + size, j:j + size] * kernel)
        return result


class TerrainGenerator:
    """地形生成器 - 整合多种生成方法"""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()
        self.noise_gen = NoiseGenerator(self.config.seed)
        self.fractal_gen = FractalGenerator(self.config.seed, self.noise_gen)
        self.entropy_gen = EntropyDrivenGenerator(self.config.seed)
        self.logger = get_logger(f"{__name__}.TerrainGenerator")

    def generate(self, config: Optional[TerrainConfig] = None) -> TerrainMap:
        if config:
            self.config = config
            self.noise_gen.set_seed(config.seed)

        method = self.config.generation_method.lower()
        if method == "fractal":
            height_map = self._generate_fractal()
        elif method == "ridged":
            height_map = self._generate_ridged()
        elif method == "entropy":
            height_map = self._generate_entropy_driven()
        else:
            height_map = self._generate_fractal()

        height_map = height_map * self.config.height_multiplier + self.config.base_height

        entropy_map = self._generate_entropy_map(height_map)
        gradient_map = self._calculate_gradient(height_map)
        type_map = self._classify_terrain(height_map, entropy_map)

        terrain_map = TerrainMap(
            width=self.config.width,
            height=self.config.height,
            resolution=self.config.resolution,
            height_map=height_map.tolist(),
            entropy_map=entropy_map.tolist(),
            gradient_map=gradient_map.tolist(),
            terrain_type_map=type_map.tolist(),
            seed=self.config.seed,
            generation_method=self.config.generation_method,
        )
        terrain_map.calculate_statistics()

        self.logger.info(
            f"Terrain generated: {self.config.width}x{self.config.height}, "
            f"method={self.config.generation_method}"
        )
        return terrain_map

    def _generate_fractal(self) -> np.ndarray:
        return self.fractal_gen.fbm(
            width=self.config.width,
            height=self.config.height,
            octaves=self.config.octaves,
            persistence=self.config.persistence,
            lacunarity=self.config.lacunarity,
            scale=self.config.scale,
            noise_type=self.config.noise_type,
        )

    def _generate_ridged(self) -> np.ndarray:
        return self.fractal_gen.ridged_multi(
            width=self.config.width,
            height=self.config.height,
            octaves=self.config.octaves,
            persistence=self.config.persistence,
            lacunarity=self.config.lacunarity,
            scale=self.config.scale,
        )

    def _generate_entropy_driven(self) -> np.ndarray:
        base = self._generate_fractal()
        entropy_field = self.noise_gen.perlin_2d(
            self.config.width, self.config.height, self.config.scale * 0.5
        )
        return self.entropy_gen.generate_from_entropy_field(
            entropy_field,
            base_height=base.mean(),
            height_multiplier=0.5,
            coupling=self.config.entropy_coupling,
        )

    def _generate_entropy_map(self, height_map: np.ndarray) -> np.ndarray:
        from ai_llm_agent_crawler.terrain.entropy import EntropyCalculator
        calc = EntropyCalculator()
        return calc.calculate_local_entropy(height_map, window_size=16)

    def _calculate_gradient(self, height_map: np.ndarray) -> np.ndarray:
        gy, gx = np.gradient(height_map)
        return np.sqrt(gx ** 2 + gy ** 2)

    def _classify_terrain(self, height_map: np.ndarray, entropy_map: np.ndarray) -> np.ndarray:
        type_map = np.full_like(height_map, TerrainType.PLAIN.value, dtype=object)
        water = self.config.water_level * self.config.height_multiplier
        mountain = self.config.mountain_level * self.config.height_multiplier

        for i in range(height_map.shape[0]):
            for j in range(height_map.shape[1]):
                h = height_map[i, j]
                e = entropy_map[i, j]
                g = 0
                if i > 0 and j > 0 and i < height_map.shape[0] - 1 and j < height_map.shape[1] - 1:
                    gx = height_map[i, j + 1] - height_map[i, j - 1]
                    gy = height_map[i + 1, j] - height_map[i - 1, j]
                    g = np.sqrt(gx ** 2 + gy ** 2)

                if h < water:
                    type_map[i, j] = TerrainType.BASIN.value
                elif g > 0.1 and h < mountain:
                    if e > 0.7:
                        type_map[i, j] = TerrainType.CANYON.value
                    else:
                        type_map[i, j] = TerrainType.HILLS.value
                elif h >= mountain:
                    if e > 0.7:
                        type_map[i, j] = TerrainType.VOLCANO.value
                    elif g > 0.15:
                        type_map[i, j] = TerrainType.MOUNTAIN.value
                    else:
                        type_map[i, j] = TerrainType.PLATEAU.value
                elif e > 0.6:
                    type_map[i, j] = TerrainType.RIDGE.value
                else:
                    type_map[i, j] = TerrainType.PLAIN.value

        return type_map

    def regenerate_region(
        self,
        terrain: TerrainMap,
        x: int,
        y: int,
        radius: int,
        new_seed: Optional[int] = None,
    ) -> TerrainMap:
        if new_seed is not None:
            self.noise_gen.set_seed(new_seed)

        x0 = max(0, x - radius)
        x1 = min(terrain.width, x + radius)
        y0 = max(0, y - radius)
        y1 = min(terrain.height, y + radius)

        region_w = x1 - x0
        region_h = y1 - y0

        if region_w <= 0 or region_h <= 0:
            return terrain

        new_region = self.fractal_gen.fbm(
            region_w, region_h,
            octaves=self.config.octaves,
            scale=self.config.scale * 0.5,
        )

        height_arr = np.array(terrain.height_map)
        mask = np.zeros_like(height_arr)
        for i in range(y0, y1):
            for j in range(x0, x1):
                dx = (j - x) / radius
                dy = (i - y) / radius
                dist = np.sqrt(dx * dx + dy * dy)
                if dist <= 1:
                    mask[i, j] = 0.5 * (1 + np.cos(np.pi * dist))

        new_height = self.config.base_height + new_region * self.config.height_multiplier
        height_arr[y0:y1, x0:x1] = (
            height_arr[y0:y1, x0:x1] * (1 - mask[y0:y1, x0:x1])
            + new_height * mask[y0:y1, x0:x1]
        )

        terrain.height_map = height_arr.tolist()
        terrain.calculate_statistics()
        return terrain


class MultiScaleTerrainGenerator:
    """多尺度地形生成器"""

    def __init__(self, config: Optional[TerrainConfig] = None):
        self.config = config or TerrainConfig()
        self.terrain_gen = TerrainGenerator(config)
        self._lod_maps: Dict[int, TerrainMap] = {}
        self.logger = get_logger(f"{__name__}.MultiScaleTerrainGenerator")

    def generate_multi_scale(self) -> Dict[int, TerrainMap]:
        maps = {}
        base_width = self.config.width
        base_height = self.config.height

        for level in range(self.config.detail_levels):
            factor = 2 ** level
            w = max(1, base_width // factor)
            h = max(1, base_height // factor)

            level_config = TerrainConfig(
                width=w,
                height=h,
                seed=self.config.seed + level * 1000,
                octaves=max(1, self.config.octaves - level),
                scale=self.config.scale / factor,
                height_multiplier=self.config.height_multiplier,
                base_height=self.config.base_height,
                noise_type=self.config.noise_type,
                generation_method=self.config.generation_method,
            )
            gen = TerrainGenerator(level_config)
            maps[level] = gen.generate(level_config)

        self._lod_maps = maps
        self.logger.info(f"Generated {len(maps)} LOD levels")
        return maps

    def get_lod(self, level: int) -> Optional[TerrainMap]:
        return self._lod_maps.get(level)

    def get_terrain_at_resolution(self, target_width: int, target_height: int) -> TerrainMap:
        best_level = 0
        best_diff = float("inf")

        for level, tmap in self._lod_maps.items():
            diff = abs(tmap.width - target_width) + abs(tmap.height - target_height)
            if diff < best_diff:
                best_diff = diff
                best_level = level

        return self._lod_maps[best_level]
