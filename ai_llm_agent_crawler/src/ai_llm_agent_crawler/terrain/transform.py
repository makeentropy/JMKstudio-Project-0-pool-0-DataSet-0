"""
维度变换模块

提供维度投影、降维、升维变换和空间扭曲功能。
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.terrain.models import (
    DimensionAxis,
    DimensionSpace,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ProjectionEngine:
    """投影引擎"""

    def __init__(self):
        pass

    def project_2d(self, points: np.ndarray, dims: Tuple[int, int] = (0, 1)) -> np.ndarray:
        if points.ndim == 1:
            points = points.reshape(-1, 1)
        return points[:, list(dims)]

    def project_orthographic(self, points: np.ndarray, view_angle: Tuple[float, float]) -> np.ndarray:
        theta, phi = view_angle
        rot_x = np.array([
            [1, 0, 0],
            [0, np.cos(theta), -np.sin(theta)],
            [0, np.sin(theta), np.cos(theta)],
        ])
        rot_y = np.array([
            [np.cos(phi), 0, np.sin(phi)],
            [0, 1, 0],
            [-np.sin(phi), 0, np.cos(phi)],
        ])

        if points.shape[1] == 2:
            points = np.hstack([points, np.zeros((len(points), 1))])

        rotated = points @ rot_x @ rot_y
        return rotated[:, :2]

    def project_perspective(
        self,
        points: np.ndarray,
        camera_distance: float = 10.0,
        fov: float = np.pi / 4,
    ) -> np.ndarray:
        if points.shape[1] == 2:
            points = np.hstack([points, np.zeros((len(points), 1))])

        z = points[:, 2] + camera_distance
        z[z == 0] = 1e-10
        scale = 1.0 / (np.tan(fov / 2) * z)

        projected = np.zeros((len(points), 2))
        projected[:, 0] = points[:, 0] * scale
        projected[:, 1] = points[:, 1] * scale
        return projected

    def project_isometric(self, points: np.ndarray) -> np.ndarray:
        return self.project_orthographic(points, (np.pi / 6, np.pi / 4))

    def project_to_entropy_map(
        self,
        points: np.ndarray,
        values: np.ndarray,
        grid_size: Tuple[int, int] = (128, 128),
    ) -> np.ndarray:
        if len(points) == 0:
            return np.zeros(grid_size)

        min_vals = np.min(points, axis=0)
        max_vals = np.max(points, axis=0)
        ranges = max_vals - min_vals
        ranges[ranges == 0] = 1

        grid = np.zeros(grid_size)
        counts = np.zeros(grid_size)

        for i, point in enumerate(points):
            x = int((point[0] - min_vals[0]) / ranges[0] * (grid_size[0] - 1))
            y = int((point[1] - min_vals[1]) / ranges[1] * (grid_size[1] - 1))
            x = max(0, min(grid_size[0] - 1, x))
            y = max(0, min(grid_size[1] - 1, y))
            grid[y, x] += values[i] if i < len(values) else 0
            counts[y, x] += 1

        counts[counts == 0] = 1
        return grid / counts


class DimensionalityReducer:
    """降维器"""

    def __init__(self):
        pass

    def pca(self, data: np.ndarray, n_components: int = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        mean = np.mean(data, axis=0)
        centered = data - mean
        cov_matrix = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        components = eigenvectors[:, :n_components]
        transformed = centered @ components
        explained_variance_ratio = eigenvalues[:n_components] / np.sum(eigenvalues)
        return transformed, components, explained_variance_ratio

    def mds(self, data: np.ndarray, n_components: int = 2) -> np.ndarray:
        n = len(data)
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                distances[i, j] = np.linalg.norm(data[i] - data[j])

        J = np.eye(n) - np.ones((n, n)) / n
        B = -0.5 * J @ (distances ** 2) @ J

        eigenvalues, eigenvectors = np.linalg.eigh(B)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx][:n_components]
        eigenvectors = eigenvectors[:, idx][:, :n_components]

        eigenvalues[eigenvalues < 0] = 0
        return eigenvectors @ np.diag(np.sqrt(eigenvalues))

    def t_sne(
        self,
        data: np.ndarray,
        n_components: int = 2,
        perplexity: float = 30.0,
        learning_rate: float = 200.0,
        n_iter: int = 1000,
    ) -> np.ndarray:
        n = len(data)
        if n == 0:
            return np.array([])

        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                distances[i, j] = np.linalg.norm(data[i] - data[j])

        P = self._compute_p_values(distances, perplexity)
        Y = np.random.randn(n, n_components) * 1e-4

        momentum = 0.5
        final_momentum = 0.8
        momentum_switch_iter = 250
        dY = np.zeros_like(Y)
        iY = np.zeros_like(Y)
        gains = np.ones_like(Y)

        for iteration in range(n_iter):
            Q = self._compute_q_values(Y)
            grad = self._compute_gradient(P, Q, Y)

            if iteration < momentum_switch_iter:
                mom = momentum
            else:
                mom = final_momentum

            gains = (gains + 0.2) * (np.sign(grad) != np.sign(dY)) + (gains * 0.8) * (np.sign(grad) == np.sign(dY))
            gains[gains < 0.01] = 0.01

            dY = mom * dY - learning_rate * (gains * grad)
            iY += dY
            Y = iY - np.mean(iY, axis=0)

        return Y

    def _compute_p_values(self, distances: np.ndarray, perplexity: float) -> np.ndarray:
        n = distances.shape[0]
        P = np.zeros((n, n))
        target_entropy = np.log2(perplexity)

        for i in range(n):
            beta = 1.0
            betamin = -np.inf
            betamax = np.inf

            for _ in range(50):
                diff = distances[i, :] ** 2
                exp_vals = np.exp(-diff * beta)
                exp_vals[i] = 0
                sum_exp = np.sum(exp_vals)
                if sum_exp == 0:
                    sum_exp = 1e-10

                P_i = exp_vals / sum_exp
                entropy = -np.sum(P_i * np.log2(P_i + 1e-10))

                entropy_diff = entropy - target_entropy
                if abs(entropy_diff) < 1e-5:
                    break

                if entropy_diff > 0:
                    betamin = beta
                    if betamax == np.inf:
                        beta *= 2
                    else:
                        beta = (beta + betamax) / 2
                else:
                    betamax = beta
                    if betamin == -np.inf:
                        beta /= 2
                    else:
                        beta = (beta + betamin) / 2

            P[i, :] = P_i

        P = (P + P.T) / (2 * n)
        return P

    def _compute_q_values(self, Y: np.ndarray) -> np.ndarray:
        n = len(Y)
        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                distances[i, j] = np.linalg.norm(Y[i] - Y[j])

        Q = 1.0 / (1.0 + distances ** 2)
        np.fill_diagonal(Q, 0)
        sum_Q = np.sum(Q)
        if sum_Q == 0:
            sum_Q = 1e-10
        Q /= sum_Q
        return Q

    def _compute_gradient(self, P: np.ndarray, Q: np.ndarray, Y: np.ndarray) -> np.ndarray:
        n = len(Y)
        grad = np.zeros_like(Y)

        distances = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                distances[i, j] = np.linalg.norm(Y[i] - Y[j])

        q_dist = 1.0 / (1.0 + distances ** 2)

        for i in range(n):
            diff = Y[i] - Y
            factor = (P[i, :] - Q[i, :]) * q_dist[i, :]
            grad[i] = 4 * np.sum(factor[:, np.newaxis] * diff, axis=0)

        return grad


class DimensionalityExpander:
    """升维器"""

    def __init__(self):
        pass

    def add_noise_dimension(self, data: np.ndarray, noise_level: float = 0.1) -> np.ndarray:
        noise = np.random.randn(len(data), 1) * noise_level
        return np.hstack([data, noise])

    def add_polynomial_features(
        self,
        data: np.ndarray,
        degree: int = 2,
        interaction_only: bool = False,
    ) -> np.ndarray:
        n_features = data.shape[1] if data.ndim > 1 else 1
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        features = [data]
        for d in range(2, degree + 1):
            if interaction_only:
                for i in range(n_features):
                    for j in range(i + 1, n_features):
                        features.append((data[:, i] * data[:, j]).reshape(-1, 1))
            else:
                for i in range(n_features):
                    features.append((data[:, i] ** d).reshape(-1, 1))
                for i in range(n_features):
                    for j in range(i + 1, n_features):
                        features.append((data[:, i] * data[:, j]).reshape(-1, 1))

        return np.hstack(features)

    def manifold_lifting(
        self,
        data: np.ndarray,
        target_dim: int = 3,
        method: str = "height_function",
    ) -> np.ndarray:
        n = len(data)
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        if method == "height_function":
            height = np.sum(data ** 2, axis=1).reshape(-1, 1)
            extra = np.zeros((n, target_dim - data.shape[1] - 1))
            return np.hstack([data, height, extra])
        elif method == "momentum":
            velocities = np.gradient(data, axis=0)
            return np.hstack([data, velocities])
        else:
            extra = np.zeros((n, target_dim - data.shape[1]))
            return np.hstack([data, extra])

    def kernel_lift(
        self,
        data: np.ndarray,
        n_components: int = 10,
        kernel: str = "rbf",
        gamma: float = 1.0,
    ) -> np.ndarray:
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        n = len(data)
        landmarks = data[np.random.choice(n, min(n, n_components), replace=False)]

        if kernel == "rbf":
            K = np.zeros((n, len(landmarks)))
            for i, point in enumerate(data):
                for j, lm in enumerate(landmarks):
                    K[i, j] = np.exp(-gamma * np.sum((point - lm) ** 2))
        elif kernel == "polynomial":
            K = (data @ landmarks.T + 1) ** 2
        else:
            K = data @ landmarks.T

        return K


class SpaceWarper:
    """空间扭曲器"""

    def __init__(self):
        pass

    def warp_radial(
        self,
        points: np.ndarray,
        center: Optional[np.ndarray] = None,
        strength: float = 0.5,
        radius: float = 1.0,
    ) -> np.ndarray:
        if center is None:
            center = np.mean(points, axis=0)

        result = points.copy()
        for i, point in enumerate(points):
            diff = point - center
            dist = np.linalg.norm(diff)
            if dist < radius and dist > 0:
                factor = 1.0 + strength * (1.0 - dist / radius)
                result[i] = center + diff * factor
        return result

    def twist(
        self,
        points: np.ndarray,
        axis: int = 2,
        strength: float = 0.1,
    ) -> np.ndarray:
        result = points.copy()
        n_dims = points.shape[1]

        for i, point in enumerate(points):
            angle = strength * point[axis]
            rot_axes = [j for j in range(n_dims) if j != axis]
            if len(rot_axes) >= 2:
                a, b = rot_axes[0], rot_axes[1]
                cos_a = np.cos(angle)
                sin_a = np.sin(angle)
                new_a = result[i, a] * cos_a - result[i, b] * sin_a
                new_b = result[i, a] * sin_a + result[i, b] * cos_a
                result[i, a] = new_a
                result[i, b] = new_b
        return result

    def bend(
        self,
        points: np.ndarray,
        axis: int = 0,
        bend_axis: int = 1,
        strength: float = 0.1,
    ) -> np.ndarray:
        result = points.copy()
        bend_center = np.mean(points[:, bend_axis])
        for i, point in enumerate(points):
            offset = point[bend_axis] - bend_center
            result[i, axis] += strength * offset ** 2
        return result

    def entropy_warp(
        self,
        points: np.ndarray,
        entropies: np.ndarray,
        strength: float = 0.3,
    ) -> np.ndarray:
        if len(entropies) != len(points):
            return points

        result = points.copy()
        center = np.mean(points, axis=0)
        max_ent = np.max(entropies) if np.max(entropies) > 0 else 1.0

        for i, point in enumerate(points):
            factor = 1.0 + strength * (entropies[i] / max_ent)
            diff = point - center
            result[i] = center + diff * factor
        return result

    def noise_warp(
        self,
        points: np.ndarray,
        noise_level: float = 0.1,
        scale: float = 1.0,
    ) -> np.ndarray:
        noise = np.random.randn(*points.shape) * noise_level
        from scipy.ndimage import gaussian_filter
        for d in range(points.shape[1]):
            noise[:, d] = gaussian_filter(noise[:, d], sigma=scale)
        return points + noise


class DimensionTransformer:
    """维度变换器 - 整合所有变换功能"""

    def __init__(self):
        self.projection = ProjectionEngine()
        self.reducer = DimensionalityReducer()
        self.expander = DimensionalityExpander()
        self.warper = SpaceWarper()
        self.logger = get_logger(f"{__name__}.DimensionTransformer")

    def transform_space(
        self,
        space: DimensionSpace,
        transform_type: str = "pca",
        **kwargs: Any,
    ) -> DimensionSpace:
        points = np.array(space.points)
        if len(points) == 0:
            return space

        if transform_type == "pca":
            n_components = kwargs.get("n_components", 2)
            transformed, _, _ = self.reducer.pca(points, n_components)
        elif transform_type == "mds":
            n_components = kwargs.get("n_components", 2)
            transformed = self.reducer.mds(points, n_components)
        elif transform_type == "project_2d":
            dims = kwargs.get("dims", (0, 1))
            transformed = self.projection.project_2d(points, dims)
        elif transform_type == "warp_radial":
            center = kwargs.get("center")
            strength = kwargs.get("strength", 0.5)
            radius = kwargs.get("radius", 1.0)
            transformed = self.warper.warp_radial(points, center, strength, radius)
        else:
            transformed = points

        new_space = DimensionSpace(
            name=f"{space.name}_{transform_type}",
            n_dimensions=transformed.shape[1],
            points=transformed.tolist(),
            point_values=space.point_values,
            point_entropies=space.point_entropies,
            metric=space.metric,
        )
        return new_space

    def create_entropy_landscape(
        self,
        points: np.ndarray,
        entropies: np.ndarray,
        grid_size: Tuple[int, int] = (128, 128),
    ) -> np.ndarray:
        return self.projection.project_to_entropy_map(points, entropies, grid_size)

    def reduce_and_expand(
        self,
        data: np.ndarray,
        reduce_dim: int = 2,
        expand_dim: int = 10,
    ) -> Tuple[np.ndarray, np.ndarray]:
        reduced, components, _ = self.reducer.pca(data, reduce_dim)
        expanded = self.expander.kernel_lift(reduced, expand_dim)
        return reduced, expanded

    def warp_by_entropy(
        self,
        space: DimensionSpace,
        strength: float = 0.3,
    ) -> DimensionSpace:
        points = np.array(space.points)
        entropies = np.array(space.point_entropies)
        warped = self.warper.entropy_warp(points, entropies, strength)
        new_space = DimensionSpace(
            name=f"{space.name}_entropy_warped",
            n_dimensions=warped.shape[1],
            points=warped.tolist(),
            point_values=space.point_values,
            point_entropies=space.point_entropies,
            metric=space.metric,
        )
        return new_space
