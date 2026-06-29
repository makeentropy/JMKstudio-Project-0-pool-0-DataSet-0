"""
component_pool_vm 模块 - 组件池虚拟机

提供种子标注、块生成、向量空间操作、尺寸编码和组件池管理功能。
"""

from typing import Any, Dict, List, Optional


class SeedAnnotator:
    """
    种子标注器 - 处理模型种子标注

    负责为种子数据添加、获取和列出元数据注解。
    """

    def __init__(self):
        """初始化种子标注器。"""
        self._annotations: Dict[bytes, Dict[str, Any]] = {}

    def annotate(self, seed: bytes, annotations: dict) -> dict:
        """
        为种子数据添加注解。

        Args:
            seed: 种子数据字节串
            annotations: 要添加的注解字典

        Returns:
            更新后的完整注解字典
        """
        if seed not in self._annotations:
            self._annotations[seed] = {}
        self._annotations[seed].update(annotations)
        return self._annotations[seed]

    def get_annotation(self, seed: bytes, key: str) -> Any:
        """
        从种子数据中获取指定注解。

        Args:
            seed: 种子数据字节串
            key: 注解键名

        Returns:
            注解值，如果不存在则返回 None
        """
        if seed not in self._annotations:
            return None
        return self._annotations[seed].get(key)

    def list_annotations(self, seed: bytes) -> List[str]:
        """
        列出种子数据的所有注解键。

        Args:
            seed: 种子数据字节串

        Returns:
            注解键列表，如果种子不存在则返回空列表
        """
        if seed not in self._annotations:
            return []
        return list(self._annotations[seed].keys())


class BlockGenerator:
    """
    块生成器 - 从种子生成完整数据块

    负责根据种子数据生成指定大小的数据块。
    """

    def __init__(self):
        """初始化块生成器。"""
        self._seed_cache: Dict[bytes, bytes] = {}

    def generate(self, seed: bytes, size: int, annotations: dict = None) -> bytes:
        """
        从种子生成指定大小的完整数据块。

        Args:
            seed: 种子数据字节串
            size: 要生成的数据块大小
            annotations: 可选的注解字典（会被添加到种子的元数据中）

        Returns:
            生成的完整数据块
        """
        if size <= 0:
            return b''

        # 使用种子初始化随机状态
        result = bytearray(size)
        seed_len = len(seed)

        if seed_len == 0:
            return bytes(result)

        # 通过种子派生数据
        for i in range(size):
            # 基于种子内容和索引派生字节
            seed_index = i % seed_len
            derived_byte = seed[seed_index] ^ ((i // seed_len) % 256)
            result[i] = derived_byte

        return bytes(result)

    def generate_with_padding(self, seed: bytes, target_size: int, padding_byte: bytes = b'\x00') -> bytes:
        """
        使用指定填充字节生成目标大小的数据块。

        Args:
            seed: 种子数据字节串
            target_size: 目标数据块大小
            padding_byte: 填充字节，默认为空字节

        Returns:
            生成的数据块，不足部分用填充字节填充
        """
        if target_size <= 0:
            return b''

        if len(padding_byte) != 1:
            padding_byte = padding_byte[:1] if padding_byte else b'\x00'

        # 首先生成基于种子的数据
        base_data = self.generate(seed, target_size)

        # 将零值字节替换为填充字节
        result = bytearray(target_size)
        for i in range(target_size):
            if base_data[i] == 0:
                result[i] = padding_byte[0]
            else:
                result[i] = base_data[i]

        return bytes(result)


class VectorSpace:
    """
    向量空间 - 处理纯维度空间运算

    负责向量加减乘除和点积运算。
    """

    def __init__(self, dimensions: int):
        """
        初始化向量空间。

        Args:
            dimensions: 空间的维度数
        """
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        """
        获取向量空间的维度数。

        Returns:
            维度数
        """
        return self._dimensions

    def create_vector(self, *coordinates) -> List[float]:
        """
        创建具有给定坐标的向量。

        Args:
            *coordinates: 向量的坐标值

        Returns:
            坐标列表

        Raises:
            ValueError: 坐标数量与维度不匹配时
        """
        if len(coordinates) != self._dimensions:
            raise ValueError(f"坐标数量({len(coordinates)})必须等于维度数({self._dimensions})")
        return list(float(c) for c in coordinates)

    def vector_add(self, v1: List[float], v2: List[float]) -> List[float]:
        """
        两个向量相加。

        Args:
            v1: 第一个向量
            v2: 第二个向量

        Returns:
            相加结果向量

        Raises:
            ValueError: 向量维度不匹配时
        """
        if len(v1) != len(v2):
            raise ValueError("向量维度必须相同才能相加")
        return [a + b for a, b in zip(v1, v2)]

    def vector_sub(self, v1: List[float], v2: List[float]) -> List[float]:
        """
        两个向量相减。

        Args:
            v1: 被减向量
            v2: 减向量

        Returns:
            相减结果向量

        Raises:
            ValueError: 向量维度不匹配时
        """
        if len(v1) != len(v2):
            raise ValueError("向量维度必须相同才能相减")
        return [a - b for a, b in zip(v1, v2)]

    def vector_mul(self, v: List[float], scalar: float) -> List[float]:
        """
        向量乘以标量。

        Args:
            v: 输入向量
            scalar: 标量值

        Returns:
            缩放后的结果向量
        """
        return [c * scalar for c in v]

    def dot_product(self, v1: List[float], v2: List[float]) -> float:
        """
        计算两个向量的点积。

        Args:
            v1: 第一个向量
            v2: 第二个向量

        Returns:
            点积结果

        Raises:
            ValueError: 向量维度不匹配时
        """
        if len(v1) != len(v2):
            raise ValueError("向量维度必须相同才能计算点积")
        return sum(a * b for a, b in zip(v1, v2))


class SizeEncoder:
    """
    尺寸编码器 - 处理尺寸数据编码

    负责整数到字节的编码和解码操作。
    """

    def __init__(self):
        """初始化尺寸编码器。"""
        pass

    def encode_size(self, size: int) -> bytes:
        """
        将尺寸编码为字节串（小端序）。

        Args:
            size: 要编码的尺寸值

        Returns:
            编码后的字节串

        Raises:
            ValueError: size 为负数时
        """
        if size < 0:
            raise ValueError("尺寸不能为负数")

        if size == 0:
            return b'\x00\x00\x00\x00'

        # 使用 4 字节无符号整数（小端序）
        return size.to_bytes(4, byteorder='little')

    def decode_size(self, encoded: bytes) -> int:
        """
        从字节串解码尺寸值（小端序）。

        Args:
            encoded: 编码后的字节串

        Returns:
            解码后的尺寸值

        Raises:
            ValueError: 字节串长度不足 4 字节时
        """
        if len(encoded) < 4:
            raise ValueError("编码字节串长度至少需要 4 字节")

        return int.from_bytes(encoded[:4], byteorder='little')

    def encode_size_varint(self, size: int) -> bytes:
        """
        使用可变长度编码尺寸值。

        使用单字节表示小尺寸，必要时使用更多字节。

        Args:
            size: 要编码的尺寸值

        Returns:
            变长编码后的字节串

        Raises:
            ValueError: size 为负数时
        """
        if size < 0:
            raise ValueError("尺寸不能为负数")

        if size < 128:
            return bytes([size])

        # 对于较大的尺寸，使用多字节编码
        result = bytearray()
        remaining = size

        while remaining > 0:
            byte = remaining & 0x7F
            remaining >>= 7

            if remaining > 0:
                byte |= 0x80

            result.append(byte)

        return bytes(result)


class ComponentPoolVM:
    """
    组件池虚拟机 - 主虚拟机类

    整合所有组件，提供池管理功能。
    """

    def __init__(self):
        """初始化组件池虚拟机。"""
        self._seed_annotator = SeedAnnotator()
        self._block_generator = BlockGenerator()
        self._vector_space = VectorSpace(dimensions=3)
        self._size_encoder = SizeEncoder()
        self._pools: Dict[str, List[Any]] = {}

    @property
    def seed_annotator(self) -> SeedAnnotator:
        """
        获取种子标注器实例。

        Returns:
            SeedAnnotator 实例
        """
        return self._seed_annotator

    @property
    def block_generator(self) -> BlockGenerator:
        """
        获取块生成器实例。

        Returns:
            BlockGenerator 实例
        """
        return self._block_generator

    @property
    def vector_space(self) -> VectorSpace:
        """
        获取向量空间实例。

        Returns:
            VectorSpace 实例
        """
        return self._vector_space

    @property
    def size_encoder(self) -> SizeEncoder:
        """
        获取尺寸编码器实例。

        Returns:
            SizeEncoder 实例
        """
        return self._size_encoder

    def create_pool(self, pool_id: str, size: int) -> None:
        """
        创建指定大小的组件池。

        Args:
            pool_id: 池的唯一标识符
            size: 池的初始大小（预留的元素数量）
        """
        self._pools[pool_id] = [None] * size

    def get_from_pool(self, pool_id: str, index: int) -> Any:
        """
        从池中获取指定索引的组件。

        Args:
            pool_id: 池的唯一标识符
            index: 组件索引

        Returns:
            组件值，如果索引无效则返回 None

        Raises:
            KeyError: 池不存在时
        """
        if pool_id not in self._pools:
            raise KeyError(f"池 '{pool_id}' 不存在")

        pool = self._pools[pool_id]
        if index < 0 or index >= len(pool):
            return None

        return pool[index]

    def add_to_pool(self, pool_id: str, component: Any) -> None:
        """
        向池中添加组件。

        Args:
            pool_id: 池的唯一标识符
            component: 要添加的组件

        Raises:
            KeyError: 池不存在时
        """
        if pool_id not in self._pools:
            raise KeyError(f"池 '{pool_id}' 不存在")

        self._pools[pool_id].append(component)

    def list_pools(self) -> List[str]:
        """
        列出所有池的标识符。

        Returns:
            池标识符列表
        """
        return list(self._pools.keys())
