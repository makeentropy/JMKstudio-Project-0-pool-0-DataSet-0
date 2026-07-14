"""
Datachain压缩算法模块

提供高效的数据链压缩和解压缩功能，支持多种压缩算法。
专为数据链（连续数据块）设计，支持增量压缩和差分压缩。
"""

import gzip
import hashlib
import json
import lzma
import struct
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import bz2

# 可选导入zstd
try:
    import zstd  # type: ignore
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class CompressionAlgorithm(Enum):
    """压缩算法枚举"""
    ZLIB = "zlib"
    GZIP = "gzip"
    LZMA = "lzma"
    BZ2 = "bz2"
    ZSTD = "zstd"
    DELTA = "delta"  # 差分压缩
    RLE = "rle"  # 游程编码
    HUFFMAN = "huffman"  # 哈夫曼编码
    NONE = "none"


class CompressionLevel(Enum):
    """压缩级别枚举"""
    FASTEST = 1
    FAST = 3
    BALANCED = 5
    BEST = 9
    ULTRA = 12


@dataclass
class CompressionMetadata:
    """压缩元数据"""
    algorithm: CompressionAlgorithm
    original_size: int
    compressed_size: int
    compression_ratio: float
    checksum_original: str
    checksum_compressed: str
    timestamp: float = field(default_factory=lambda: 0.0)
    level: int = 5
    block_count: int = 1
    is_delta: bool = False
    reference_block_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "algorithm": self.algorithm.value,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "checksum_original": self.checksum_original,
            "checksum_compressed": self.checksum_compressed,
            "timestamp": self.timestamp,
            "level": self.level,
            "block_count": self.block_count,
            "is_delta": self.is_delta,
            "reference_block_id": self.reference_block_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompressionMetadata":
        """从字典创建"""
        return cls(
            algorithm=CompressionAlgorithm(data["algorithm"]),
            original_size=data["original_size"],
            compressed_size=data["compressed_size"],
            compression_ratio=data["compression_ratio"],
            checksum_original=data["checksum_original"],
            checksum_compressed=data["checksum_compressed"],
            timestamp=data.get("timestamp", 0.0),
            level=data.get("level", 5),
            block_count=data.get("block_count", 1),
            is_delta=data.get("is_delta", False),
            reference_block_id=data.get("reference_block_id"),
        )


@dataclass
class DataBlock:
    """数据块"""
    block_id: str
    data: bytes
    sequence_number: int
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "block_id": self.block_id,
            "data": self.data.hex(),
            "sequence_number": self.sequence_number,
            "metadata": self.metadata or {},
        }


@dataclass
class CompressedDataBlock:
    """压缩数据块"""
    block_id: str
    compressed_data: bytes
    sequence_number: int
    metadata: CompressionMetadata
    is_reference: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "block_id": self.block_id,
            "compressed_data": self.compressed_data.hex(),
            "sequence_number": self.sequence_number,
            "metadata": self.metadata.to_dict(),
            "is_reference": self.is_reference,
        }


@dataclass
class DataChainHeader:
    """数据链头部"""
    chain_id: str
    version: int = 1
    total_blocks: int = 0
    total_original_size: int = 0
    total_compressed_size: int = 0
    algorithms_used: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: 0.0)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chain_id": self.chain_id,
            "version": self.version,
            "total_blocks": self.total_blocks,
            "total_original_size": self.total_original_size,
            "total_compressed_size": self.total_compressed_size,
            "algorithms_used": self.algorithms_used,
            "created_at": self.created_at,
            "checksum": self.checksum,
        }

    def serialize(self) -> bytes:
        """序列化头部"""
        header_dict = self.to_dict()
        header_json = json.dumps(header_dict, ensure_ascii=False)
        return header_json.encode("utf-8")


class BaseCompressor:
    """基础压缩器"""

    def __init__(self, level: int = 5):
        """
        初始化压缩器

        Args:
            level: 压缩级别（1-12）
        """
        self.level = max(1, min(12, level))

    def compress(self, data: bytes) -> bytes:
        """压缩数据"""
        raise NotImplementedError

    def decompress(self, data: bytes) -> bytes:
        """解压缩数据"""
        raise NotImplementedError


class ZlibCompressor(BaseCompressor):
    """Zlib压缩器"""

    def compress(self, data: bytes) -> bytes:
        return zlib.compress(data, self.level)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)


class GzipCompressor(BaseCompressor):
    """Gzip压缩器"""

    def compress(self, data: bytes) -> bytes:
        return gzip.compress(data, compresslevel=self.level)

    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)


class LZMACompressor(BaseCompressor):
    """LZMA压缩器"""

    def compress(self, data: bytes) -> bytes:
        preset = min(self.level, 9)
        return lzma.compress(data, preset=preset)

    def decompress(self, data: bytes) -> bytes:
        return lzma.decompress(data)


class BZ2Compressor(BaseCompressor):
    """BZ2压缩器"""

    def compress(self, data: bytes) -> bytes:
        return bz2.compress(data, compresslevel=self.level)

    def decompress(self, data: bytes) -> bytes:
        return bz2.decompress(data)


class ZstdCompressor(BaseCompressor):
    """Zstd压缩器"""

    def compress(self, data: bytes) -> bytes:
        if not ZSTD_AVAILABLE:
            raise ImportError("zstd库未安装，请安装pyzstd或zstd库")
        # Zstd的压缩级别范围是1-22
        level = min(self.level, 22)
        return zstd.compress(data, level)

    def decompress(self, data: bytes) -> bytes:
        if not ZSTD_AVAILABLE:
            raise ImportError("zstd库未安装，请安装pyzstd或zstd库")
        return zstd.decompress(data)


class DeltaCompressor(BaseCompressor):
    """差分压缩器"""

    def __init__(self, level: int = 5, reference_data: Optional[bytes] = None):
        """
        初始化差分压缩器

        Args:
            level: 压缩级别
            reference_data: 参考数据（用于差分计算）
        """
        super().__init__(level)
        self.reference_data = reference_data or b""
        self._zlib_compressor = ZlibCompressor(level)

    def set_reference(self, reference_data: bytes) -> None:
        """设置参考数据"""
        self.reference_data = reference_data

    def compress(self, data: bytes) -> bytes:
        """差分压缩"""
        if not self.reference_data:
            return self._zlib_compressor.compress(data)

        # 计算差分
        delta = self._calculate_delta(data, self.reference_data)

        # 对差分数据进行Zlib压缩
        return self._zlib_compressor.compress(delta)

    def decompress(self, data: bytes, reference_data: Optional[bytes] = None) -> bytes:
        """差分解压缩"""
        ref = reference_data or self.reference_data
        if not ref:
            return self._zlib_compressor.decompress(data)

        # 解压差分数据
        delta = self._zlib_compressor.decompress(data)

        # 应用差分恢复原始数据
        return self._apply_delta(delta, ref)

    def _calculate_delta(self, data: bytes, reference: bytes) -> bytes:
        """计算差分"""
        min_len = min(len(data), len(reference))
        delta = bytearray(len(data))

        # 对相同长度部分计算差值
        for i in range(min_len):
            delta[i] = data[i] - reference[i]  # 可能溢出，但bytearray会处理

        # 对于超出的部分，直接复制
        if len(data) > len(reference):
            delta[min_len:] = data[min_len:]

        # 在头部添加长度信息和差分长度
        header = struct.pack(">II", len(data), min_len)
        return header + bytes(delta[:min_len]) + bytes(delta[min_len:])

    def _apply_delta(self, delta: bytes, reference: bytes) -> bytes:
        """应用差分"""
        # 解析头部
        if len(delta) < 8:
            return reference

        original_len, diff_len = struct.unpack(">II", delta[:8])
        result = bytearray(original_len)

        # 对差分部分应用差值
        for i in range(diff_len):
            if i < len(reference):
                result[i] = (delta[8 + i] + reference[i]) % 256
            else:
                result[i] = delta[8 + i]

        # 对于超出的部分，直接复制
        if len(delta) > 8 + diff_len:
            result[diff_len:] = delta[8 + diff_len:]

        return bytes(result)


class RLECompressor(BaseCompressor):
    """游程编码压缩器"""

    def compress(self, data: bytes) -> bytes:
        """游程编码压缩"""
        if not data:
            return b""

        result = bytearray()
        i = 0
        while i < len(data):
            # 计算当前字节连续出现的次数
            byte = data[i]
            count = 1
            while i + count < len(data) and data[i + count] == byte and count < 255:
                count += 1

            # 如果连续次数>=3，使用RLE编码
            if count >= 3:
                result.append(0xFF)  # RLE标记
                result.append(byte)
                result.append(count)
                i += count
            else:
                # 直接写入字节
                for _ in range(count):
                    result.append(byte)
                    i += 1

        return bytes(result)

    def decompress(self, data: bytes) -> bytes:
        """游程编码解压缩"""
        if not data:
            return b""

        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == 0xFF and i + 2 < len(data):
                # RLE编码
                byte = data[i + 1]
                count = data[i + 2]
                result.extend([byte] * count)
                i += 3
            else:
                result.append(data[i])
                i += 1

        return bytes(result)


class DataChainCompressor:
    """
    数据链压缩器

    专门用于压缩数据链，支持多种压缩算法和增量压缩。
    """

    def __init__(
        self,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.ZSTD if ZSTD_AVAILABLE else CompressionAlgorithm.ZLIB,
        level: int = 5,
        enable_delta: bool = False,
        block_size: int = 1024 * 1024,  # 1MB
    ):
        """
        初始化数据链压缩器

        Args:
            algorithm: 主压缩算法
            level: 压缩级别
            enable_delta: 是否启用差分压缩
            block_size: 数据块大小
        """
        self.algorithm = algorithm
        self.level = level
        self.enable_delta = enable_delta
        self.block_size = block_size
        self._compressors: Dict[CompressionAlgorithm, BaseCompressor] = {}
        self._reference_blocks: Dict[str, bytes] = {}
        self._initialize_compressors()

    def _initialize_compressors(self) -> None:
        """初始化压缩器"""
        self._compressors = {
            CompressionAlgorithm.ZLIB: ZlibCompressor(self.level),
            CompressionAlgorithm.GZIP: GzipCompressor(self.level),
            CompressionAlgorithm.LZMA: LZMACompressor(self.level),
            CompressionAlgorithm.BZ2: BZ2Compressor(self.level),
            CompressionAlgorithm.RLE: RLECompressor(self.level),
        }

        # 如果zstd可用则添加
        if ZSTD_AVAILABLE:
            self._compressors[CompressionAlgorithm.ZSTD] = ZstdCompressor(self.level)

        if self.enable_delta:
            self._compressors[CompressionAlgorithm.DELTA] = DeltaCompressor(self.level)

    def get_compressor(self, algorithm: CompressionAlgorithm) -> BaseCompressor:
        """获取压缩器"""
        if algorithm not in self._compressors:
            raise ValueError(f"不支持的压缩算法: {algorithm}")
        return self._compressors[algorithm]

    def compress_block(
        self,
        block: DataBlock,
        algorithm: Optional[CompressionAlgorithm] = None,
        use_delta: Optional[bool] = None,
        reference_block_id: Optional[str] = None,
    ) -> CompressedDataBlock:
        """
        压缩数据块

        Args:
            block: 数据块
            algorithm: 压缩算法，不指定则使用默认
            use_delta: 是否使用差分压缩
            reference_block_id: 参考块ID

        Returns:
            压缩数据块
        """
        algo = algorithm or self.algorithm
        use_delta_flag = use_delta if use_delta is not None else self.enable_delta

        # 计算原始数据校验和
        checksum_original = hashlib.sha256(block.data).hexdigest()

        # 执行压缩
        compressed_data = b""
        is_reference = False

        if use_delta_flag and reference_block_id and reference_block_id in self._reference_blocks:
            # 差分压缩
            delta_compressor = DeltaCompressor(self.level)
            delta_compressor.set_reference(self._reference_blocks[reference_block_id])
            compressed_data = delta_compressor.compress(block.data)
            algo = CompressionAlgorithm.DELTA
        else:
            # 标准压缩
            compressor = self.get_compressor(algo)
            compressed_data = compressor.compress(block.data)
            is_reference = True  # 保存为参考块

        # 计算压缩数据校验和
        checksum_compressed = hashlib.sha256(compressed_data).hexdigest()

        # 创建压缩元数据
        metadata = CompressionMetadata(
            algorithm=algo,
            original_size=len(block.data),
            compressed_size=len(compressed_data),
            compression_ratio=len(compressed_data) / len(block.data) if block.data else 0,
            checksum_original=checksum_original,
            checksum_compressed=checksum_compressed,
            level=self.level,
            is_delta=use_delta_flag,
            reference_block_id=reference_block_id,
        )

        # 保存参考块
        if is_reference:
            self._reference_blocks[block.block_id] = block.data

        logger.info(
            f"压缩块 {block.block_id}: {len(block.data)} -> {len(compressed_data)} bytes "
            f"(ratio: {metadata.compression_ratio:.2f})"
        )

        return CompressedDataBlock(
            block_id=block.block_id,
            compressed_data=compressed_data,
            sequence_number=block.sequence_number,
            metadata=metadata,
            is_reference=is_reference,
        )

    def decompress_block(
        self,
        compressed_block: CompressedDataBlock,
    ) -> DataBlock:
        """
        解压缩数据块

        Args:
            compressed_block: 压缩数据块

        Returns:
            数据块
        """
        algo = compressed_block.metadata.algorithm

        # 执行解压缩
        if algo == CompressionAlgorithm.DELTA:
            # 差分解压缩
            ref_id = compressed_block.metadata.reference_block_id
            reference_data = self._reference_blocks.get(ref_id) if ref_id else None

            if reference_data:
                delta_compressor = DeltaCompressor(self.level)
                data = delta_compressor.decompress(compressed_block.compressed_data, reference_data)
            else:
                # 如果没有参考数据，尝试标准解压
                zlib_compressor = ZlibCompressor(self.level)
                data = zlib_compressor.decompress(compressed_block.compressed_data)
        else:
            # 标准解压缩
            compressor = self.get_compressor(algo)
            data = compressor.decompress(compressed_block.compressed_data)

        # 验证校验和
        checksum = hashlib.sha256(data).hexdigest()
        if checksum != compressed_block.metadata.checksum_original:
            raise ValueError(f"校验和不匹配: 期望 {compressed_block.metadata.checksum_original}, 实际 {checksum}")

        logger.info(f"解压缩块 {compressed_block.block_id}: {len(compressed_block.compressed_data)} -> {len(data)} bytes")

        return DataBlock(
            block_id=compressed_block.block_id,
            data=data,
            sequence_number=compressed_block.sequence_number,
        )

    def compress_data(
        self,
        data: bytes,
        algorithm: Optional[CompressionAlgorithm] = None,
    ) -> tuple[bytes, CompressionMetadata]:
        """
        压缩单个数据

        Args:
            data: 要压缩的数据
            algorithm: 压缩算法

        Returns:
            (压缩数据, 元数据) 元组
        """
        algo = algorithm or self.algorithm

        # 计算校验和
        checksum_original = hashlib.sha256(data).hexdigest()

        # 压缩
        compressor = self.get_compressor(algo)
        compressed_data = compressor.compress(data)

        # 计算压缩数据校验和
        checksum_compressed = hashlib.sha256(compressed_data).hexdigest()

        # 创建元数据
        metadata = CompressionMetadata(
            algorithm=algo,
            original_size=len(data),
            compressed_size=len(compressed_data),
            compression_ratio=len(compressed_data) / len(data) if data else 0,
            checksum_original=checksum_original,
            checksum_compressed=checksum_compressed,
            level=self.level,
        )

        return compressed_data, metadata

    def decompress_data(
        self,
        compressed_data: bytes,
        metadata: CompressionMetadata,
    ) -> bytes:
        """
        解压缩单个数据

        Args:
            compressed_data: 压缩数据
            metadata: 压缩元数据

        Returns:
            解压缩后的数据
        """
        compressor = self.get_compressor(metadata.algorithm)
        data = compressor.decompress(compressed_data)

        # 验证校验和
        checksum = hashlib.sha256(data).hexdigest()
        if checksum != metadata.checksum_original:
            raise ValueError(f"校验和不匹配")

        return data

    def compress_chain(
        self,
        blocks: List[DataBlock],
        chain_id: Optional[str] = None,
    ) -> tuple[List[CompressedDataBlock], DataChainHeader]:
        """
        压缩数据链

        Args:
            blocks: 数据块列表
            chain_id: 数据链ID

        Returns:
            (压缩块列表, 链头部) 元组
        """
        import time

        if chain_id is None:
            chain_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

        compressed_blocks: List[CompressedDataBlock] = []
        total_original_size = 0
        total_compressed_size = 0
        algorithms_used: List[str] = []

        # 按顺序压缩每个块
        reference_block_id = None
        for block in blocks:
            # 使用差分压缩时，参考前一个块
            if self.enable_delta and compressed_blocks:
                reference_block_id = compressed_blocks[-1].block_id

            compressed_block = self.compress_block(
                block,
                reference_block_id=reference_block_id,
            )

            compressed_blocks.append(compressed_block)
            total_original_size += compressed_block.metadata.original_size
            total_compressed_size += compressed_block.metadata.compressed_size

            algo_name = compressed_block.metadata.algorithm.value
            if algo_name not in algorithms_used:
                algorithms_used.append(algo_name)

        # 创建链头部
        header = DataChainHeader(
            chain_id=chain_id,
            total_blocks=len(compressed_blocks),
            total_original_size=total_original_size,
            total_compressed_size=total_compressed_size,
            algorithms_used=algorithms_used,
            created_at=time.time(),
        )

        # 计算整体校验和
        header.checksum = hashlib.sha256(
            json.dumps([b.to_dict() for b in compressed_blocks]).encode()
        ).hexdigest()

        logger.info(
            f"压缩链 {chain_id}: {len(blocks)} blocks, "
            f"{total_original_size} -> {total_compressed_size} bytes "
            f"(ratio: {total_compressed_size / total_original_size if total_original_size else 0:.2f})"
        )

        return compressed_blocks, header

    def decompress_chain(
        self,
        compressed_blocks: List[CompressedDataBlock],
        header: DataChainHeader,
    ) -> List[DataBlock]:
        """
        解压缩数据链

        Args:
            compressed_blocks: 压缩数据块列表
            header: 链头部

        Returns:
            数据块列表
        """
        # 按顺序解压缩每个块
        blocks: List[DataBlock] = []
        for compressed_block in compressed_blocks:
            block = self.decompress_block(compressed_block)
            blocks.append(block)

        # 验证校验和
        checksum = hashlib.sha256(
            json.dumps([b.to_dict() for b in compressed_blocks]).encode()
        ).hexdigest()
        if checksum != header.checksum:
            logger.warning(f"链校验和不匹配: 期望 {header.checksum}, 实际 {checksum}")

        logger.info(f"解压缩链 {header.chain_id}: {len(blocks)} blocks")

        return blocks

    def serialize_chain(
        self,
        compressed_blocks: List[CompressedDataBlock],
        header: DataChainHeader,
    ) -> bytes:
        """
        序列化压缩链

        Args:
            compressed_blocks: 压缩数据块列表
            header: 链头部

        Returns:
            序列化后的数据
        """
        # 序列化头部
        header_bytes = header.serialize()

        # 序列化每个块
        blocks_data = bytearray()
        for block in compressed_blocks:
            block_dict = block.to_dict()
            block_json = json.dumps(block_dict, ensure_ascii=False)
            block_bytes = block_json.encode("utf-8")
            # 添加块长度前缀
            blocks_data.extend(struct.pack(">I", len(block_bytes)))
            blocks_data.extend(block_bytes)

        # 组合：头部长度 + 头部 + 块数据
        result = bytearray()
        result.extend(struct.pack(">I", len(header_bytes)))
        result.extend(header_bytes)
        result.extend(blocks_data)

        return bytes(result)

    def deserialize_chain(
        self,
        serialized_data: bytes,
    ) -> tuple[List[CompressedDataBlock], DataChainHeader]:
        """
        反序列化压缩链

        Args:
            serialized_data: 序列化数据

        Returns:
            (压缩块列表, 链头部) 元组
        """
        # 解析头部长度
        if len(serialized_data) < 4:
            raise ValueError("数据长度不足")

        header_len = struct.unpack(">I", serialized_data[:4])[0]

        # 解析头部
        header_bytes = serialized_data[4:4 + header_len]
        header_dict = json.loads(header_bytes.decode("utf-8"))
        header = DataChainHeader(
            chain_id=header_dict["chain_id"],
            version=header_dict.get("version", 1),
            total_blocks=header_dict.get("total_blocks", 0),
            total_original_size=header_dict.get("total_original_size", 0),
            total_compressed_size=header_dict.get("total_compressed_size", 0),
            algorithms_used=header_dict.get("algorithms_used", []),
            created_at=header_dict.get("created_at", 0.0),
            checksum=header_dict.get("checksum", ""),
        )

        # 解析块数据
        compressed_blocks: List[CompressedDataBlock] = []
        offset = 4 + header_len

        for _ in range(header.total_blocks):
            if offset + 4 > len(serialized_data):
                break

            block_len = struct.unpack(">I", serialized_data[offset:offset + 4])[0]
            offset += 4

            block_bytes = serialized_data[offset:offset + block_len]
            offset += block_len

            block_dict = json.loads(block_bytes.decode("utf-8"))

            metadata_dict = block_dict["metadata"]
            metadata = CompressionMetadata.from_dict(metadata_dict)

            compressed_block = CompressedDataBlock(
                block_id=block_dict["block_id"],
                compressed_data=bytes.fromhex(block_dict["compressed_data"]),
                sequence_number=block_dict["sequence_number"],
                metadata=metadata,
                is_reference=block_dict.get("is_reference", False),
            )
            compressed_blocks.append(compressed_block)

        return compressed_blocks, header

    def clear_reference_blocks(self) -> None:
        """清除参考块缓存"""
        self._reference_blocks.clear()
        logger.info("清除参考块缓存")


class AdaptiveCompressor:
    """
    自适应压缩器

    根据数据特征自动选择最佳压缩算法。
    """

    def __init__(self, default_level: int = 5):
        """
        初始化自适应压缩器

        Args:
            default_level: 默认压缩级别
        """
        self.default_level = default_level
        self._compressor = DataChainCompressor(
            algorithm=CompressionAlgorithm.GZIP,
            level=default_level,
        )

    def analyze_data(self, data: bytes, sample_size: int = 4096) -> Dict[str, Any]:
        """
        分析数据特征

        Args:
            data: 数据
            sample_size: 样本大小

        Returns:
            数据特征字典
        """
        if len(data) == 0:
            return {"entropy": 0, "repetition": 0, "recommended": CompressionAlgorithm.NONE}

        # 使用样本进行分析
        sample = data[:sample_size] if len(data) > sample_size else data

        # 计算熵
        entropy = self._calculate_entropy(sample)

        # 计算重复率
        repetition = self._calculate_repetition(sample)

        # 推荐算法
        recommended = self._recommend_algorithm(entropy, repetition, len(data))

        return {
            "entropy": entropy,
            "repetition": repetition,
            "size": len(data),
            "recommended": recommended,
        }

    def _calculate_entropy(self, data: bytes) -> float:
        """计算数据熵"""
        if not data:
            return 0.0

        import math

        # 统计字节频率
        freq: Dict[int, int] = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1

        # 计算熵
        entropy = 0.0
        for count in freq.values():
            p = count / len(data)
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    def _calculate_repetition(self, data: bytes) -> float:
        """计算重复率"""
        if not data:
            return 0.0

        unique_bytes = len(set(data))
        return 1 - (unique_bytes / 256)

    def _recommend_algorithm(
        self,
        entropy: float,
        repetition: float,
        size: int,
    ) -> CompressionAlgorithm:
        """推荐压缩算法"""
        # 高重复率 -> RLE
        if repetition > 0.8:
            return CompressionAlgorithm.RLE

        # 低熵 -> GZIP
        if entropy < 4:
            return CompressionAlgorithm.GZIP

        # 大数据 -> LZMA
        if size > 10 * 1024 * 1024:  # 10MB
            return CompressionAlgorithm.LZMA

        # 默认 -> GZIP
        return CompressionAlgorithm.GZIP

    def compress(
        self,
        data: bytes,
        auto_select: bool = True,
    ) -> tuple[bytes, CompressionMetadata]:
        """
        自适应压缩

        Args:
            data: 要压缩的数据
            auto_select: 是否自动选择算法

        Returns:
            (压缩数据, 元数据) 元组
        """
        if auto_select:
            # 分析数据特征
            analysis = self.analyze_data(data)
            algorithm = analysis["recommended"]
        else:
            algorithm = CompressionAlgorithm.GZIP

        return self._compressor.compress_data(data, algorithm)

    def decompress(
        self,
        compressed_data: bytes,
        metadata: CompressionMetadata,
    ) -> bytes:
        """解压缩"""
        return self._compressor.decompress_data(compressed_data, metadata)