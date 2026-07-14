"""
Datachain压缩算法测试
"""

import pytest
from ai_llm_agent_crawler.security.datachain_compression import (
    CompressionAlgorithm,
    CompressionLevel,
    DataBlock,
    DataChainCompressor,
    ZlibCompressor,
    GzipCompressor,
    LZMACompressor,
    BZ2Compressor,
    RLECompressor,
    AdaptiveCompressor,
)


class TestCompressors:
    """测试各个压缩器"""

    def test_zlib_compress_decompress(self):
        """测试Zlib压缩和解压"""
        compressor = ZlibCompressor(level=5)
        data = b"Hello, this is a test data for compression. " * 100

        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)

        assert len(compressed) < len(data)
        assert decompressed == data

    def test_gzip_compress_decompress(self):
        """测试Gzip压缩和解压"""
        compressor = GzipCompressor(level=5)
        data = b"Hello, this is a test data for compression. " * 100

        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)

        assert len(compressed) < len(data)
        assert decompressed == data

    def test_lzma_compress_decompress(self):
        """测试LZMA压缩和解压"""
        compressor = LZMACompressor(level=5)
        data = b"Hello, this is a test data for compression. " * 100

        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)

        assert len(compressed) < len(data)
        assert decompressed == data

    def test_bz2_compress_decompress(self):
        """测试BZ2压缩和解压"""
        compressor = BZ2Compressor(level=5)
        data = b"Hello, this is a test data for compression. " * 100

        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)

        assert len(compressed) < len(data)
        assert decompressed == data

    def test_rle_compress_decompress(self):
        """测试RLE压缩和解压"""
        compressor = RLECompressor()
        data = b"AAAAABBBBCCCCCCCCCCCCCCCC" * 10  # 高重复数据

        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)

        assert decompressed == data

    def test_rle_no_compression_needed(self):
        """测试RLE对低重复数据"""
        compressor = RLECompressor()
        data = b"ABCDEFGHIJKLMNO"

        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)

        assert decompressed == data


class TestDataChainCompressor:
    """测试数据链压缩器"""

    def test_compress_decompress_data(self):
        """测试压缩和解压数据"""
        compressor = DataChainCompressor(
            algorithm=CompressionAlgorithm.ZLIB,
            level=5
        )
        data = b"Hello, this is a test data for compression. " * 100

        compressed, metadata = compressor.compress_data(data)
        decompressed = compressor.decompress_data(compressed, metadata)

        assert metadata.original_size == len(data)
        assert metadata.compressed_size < len(data)
        assert decompressed == data

    def test_compress_decompress_block(self):
        """测试压缩和解压数据块"""
        compressor = DataChainCompressor(
            algorithm=CompressionAlgorithm.GZIP,
            level=5
        )

        block = DataBlock(
            block_id="test_block",
            data=b"Hello, this is a test data for compression. " * 100,
            sequence_number=1
        )

        compressed_block = compressor.compress_block(block)
        decompressed_block = compressor.decompress_block(compressed_block)

        assert decompressed_block.block_id == block.block_id
        assert decompressed_block.data == block.data

    def test_compress_decompress_chain(self):
        """测试压缩和解压数据链"""
        compressor = DataChainCompressor(
            algorithm=CompressionAlgorithm.GZIP,
            level=5
        )

        blocks = [
            DataBlock(block_id="block1", data=b"Data block 1 content " * 50, sequence_number=1),
            DataBlock(block_id="block2", data=b"Data block 2 content " * 50, sequence_number=2),
            DataBlock(block_id="block3", data=b"Data block 3 content " * 50, sequence_number=3),
        ]

        compressed_blocks, header = compressor.compress_chain(blocks)
        decompressed_blocks = compressor.decompress_chain(compressed_blocks, header)

        assert len(decompressed_blocks) == len(blocks)
        for i, block in enumerate(blocks):
            assert decompressed_blocks[i].block_id == block.block_id
            assert decompressed_blocks[i].data == block.data

    def test_serialize_deserialize_chain(self):
        """测试序列化和反序列化数据链"""
        compressor = DataChainCompressor(
            algorithm=CompressionAlgorithm.GZIP,
            level=5
        )

        blocks = [
            DataBlock(block_id="block1", data=b"Data block 1 content " * 50, sequence_number=1),
            DataBlock(block_id="block2", data=b"Data block 2 content " * 50, sequence_number=2),
        ]

        compressed_blocks, header = compressor.compress_chain(blocks)
        serialized = compressor.serialize_chain(compressed_blocks, header)
        deserialized_blocks, deserialized_header = compressor.deserialize_chain(serialized)

        assert header.chain_id == deserialized_header.chain_id
        assert header.total_blocks == deserialized_header.total_blocks

    def test_different_compression_levels(self):
        """测试不同压缩级别"""
        data = b"Hello, this is a test data for compression. " * 100

        # 低级别（快速）
        compressor_fast = DataChainCompressor(
            algorithm=CompressionAlgorithm.GZIP,
            level=CompressionLevel.FASTEST.value
        )
        compressed_fast, metadata_fast = compressor_fast.compress_data(data)

        # 高级别（最佳压缩）
        compressor_best = DataChainCompressor(
            algorithm=CompressionAlgorithm.GZIP,
            level=CompressionLevel.BEST.value
        )
        compressed_best, metadata_best = compressor_best.compress_data(data)

        # 最佳压缩应该更小（但需要更多时间）
        assert metadata_best.compressed_size <= metadata_fast.compressed_size

    def test_empty_data(self):
        """测试空数据"""
        compressor = DataChainCompressor()
        data = b""

        compressed, metadata = compressor.compress_data(data)
        decompressed = compressor.decompress_data(compressed, metadata)

        assert decompressed == data


class TestAdaptiveCompressor:
    """测试自适应压缩器"""

    def test_analyze_data(self):
        """测试数据分析"""
        compressor = AdaptiveCompressor()

        # 高重复数据
        high_repetition = b"AAAAABBBBCCCCCCCCCCCCCCCC" * 100
        analysis = compressor.analyze_data(high_repetition)

        assert analysis["repetition"] > 0
        assert analysis["recommended"] in CompressionAlgorithm

        # 低重复数据
        low_repetition = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        analysis = compressor.analyze_data(low_repetition)

        assert analysis["entropy"] > 0

    def test_auto_compress(self):
        """测试自动选择压缩"""
        compressor = AdaptiveCompressor()
        data = b"Hello, this is a test data for compression. " * 100

        compressed, metadata = compressor.compress(data, auto_select=True)
        decompressed = compressor.decompress(compressed, metadata)

        assert decompressed == data
        assert metadata.algorithm in CompressionAlgorithm

    def test_compress_without_auto_select(self):
        """测试不自动选择压缩"""
        compressor = AdaptiveCompressor()
        data = b"Hello, this is a test data for compression. " * 100

        compressed, metadata = compressor.compress(data, auto_select=False)
        decompressed = compressor.decompress(compressed, metadata)

        assert decompressed == data
        assert metadata.algorithm == CompressionAlgorithm.GZIP


class TestCompressionMetadata:
    """测试压缩元数据"""

    def test_to_dict_from_dict(self):
        """测试元数据序列化"""
        compressor = DataChainCompressor()
        data = b"Test data for compression"

        compressed, metadata = compressor.compress_data(data)
        metadata_dict = metadata.to_dict()
        restored_metadata = type(metadata).from_dict(metadata_dict)

        assert restored_metadata.algorithm == metadata.algorithm
        assert restored_metadata.original_size == metadata.original_size
        assert restored_metadata.compressed_size == metadata.compressed_size
        assert restored_metadata.checksum_original == metadata.checksum_original