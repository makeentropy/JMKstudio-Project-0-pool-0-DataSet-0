"""component_pool_vm 模块单元测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from src.component_pool_vm import (
    SeedAnnotator,
    BlockGenerator,
    VectorSpace,
    SizeEncoder,
    ComponentPoolVM
)


class TestSeedAnnotator(unittest.TestCase):
    """SeedAnnotator 类测试"""

    def test_initialization(self):
        """测试初始化"""
        annotator = SeedAnnotator()
        self.assertEqual(annotator._annotations, {})

    def test_annotate(self):
        """测试添加注解"""
        annotator = SeedAnnotator()
        seed = b'test_seed'
        annotations = {'key1': 'value1', 'key2': 'value2'}

        result = annotator.annotate(seed, annotations)

        self.assertEqual(result, annotations)
        self.assertEqual(annotator.get_annotation(seed, 'key1'), 'value1')
        self.assertEqual(annotator.get_annotation(seed, 'key2'), 'value2')

    def test_annotate_update_existing(self):
        """测试更新已存在的注解"""
        annotator = SeedAnnotator()
        seed = b'test_seed'
        annotator.annotate(seed, {'key1': 'value1'})
        annotator.annotate(seed, {'key2': 'value2'})

        self.assertEqual(annotator.get_annotation(seed, 'key1'), 'value1')
        self.assertEqual(annotator.get_annotation(seed, 'key2'), 'value2')

    def test_annotate_returns_full_annotation(self):
        """测试 annotate 返回完整的注解字典"""
        annotator = SeedAnnotator()
        seed = b'test_seed'
        annotator.annotate(seed, {'key1': 'value1'})
        result = annotator.annotate(seed, {'key2': 'value2'})

        self.assertEqual(result, {'key1': 'value1', 'key2': 'value2'})

    def test_get_annotation_existing(self):
        """测试获取已存在的注解"""
        annotator = SeedAnnotator()
        seed = b'test_seed'
        annotator.annotate(seed, {'key': 'value'})

        result = annotator.get_annotation(seed, 'key')

        self.assertEqual(result, 'value')

    def test_get_annotation_nonexistent_seed(self):
        """测试获取不存在的种子的注解返回 None"""
        annotator = SeedAnnotator()

        result = annotator.get_annotation(b'nonexistent', 'key')

        self.assertIsNone(result)

    def test_get_annotation_nonexistent_key(self):
        """测试获取不存在的键返回 None"""
        annotator = SeedAnnotator()
        seed = b'test_seed'
        annotator.annotate(seed, {'key1': 'value1'})

        result = annotator.get_annotation(seed, 'nonexistent')

        self.assertIsNone(result)

    def test_list_annotations(self):
        """测试列出所有注解键"""
        annotator = SeedAnnotator()
        seed = b'test_seed'
        annotator.annotate(seed, {'key1': 'value1', 'key2': 'value2'})

        result = annotator.list_annotations(seed)

        self.assertEqual(len(result), 2)
        self.assertIn('key1', result)
        self.assertIn('key2', result)

    def test_list_annotations_nonexistent_seed(self):
        """测试列出不存在种子的注解返回空列表"""
        annotator = SeedAnnotator()

        result = annotator.list_annotations(b'nonexistent')

        self.assertEqual(result, [])


class TestBlockGenerator(unittest.TestCase):
    """BlockGenerator 类测试"""

    def test_initialization(self):
        """测试初始化"""
        generator = BlockGenerator()
        self.assertEqual(generator._seed_cache, {})

    def test_generate(self):
        """测试生成指定大小的数据块"""
        generator = BlockGenerator()
        seed = b'test_seed'
        size = 10

        result = generator.generate(seed, size)

        self.assertEqual(len(result), size)
        self.assertIsInstance(result, bytes)

    def test_generate_zero_size(self):
        """测试生成零大小的数据块返回空字节"""
        generator = BlockGenerator()
        result = generator.generate(b'seed', 0)

        self.assertEqual(result, b'')

    def test_generate_negative_size(self):
        """测试生成负数大小的数据块返回空字节"""
        generator = BlockGenerator()
        result = generator.generate(b'seed', -5)

        self.assertEqual(result, b'')

    def test_generate_empty_seed(self):
        """测试使用空种子生成"""
        generator = BlockGenerator()
        result = generator.generate(b'', 10)

        self.assertEqual(len(result), 10)

    def test_generate_deterministic(self):
        """测试生成的确定性（相同输入产生相同输出）"""
        generator = BlockGenerator()
        seed = b'test_seed'
        size = 20

        result1 = generator.generate(seed, size)
        result2 = generator.generate(seed, size)

        self.assertEqual(result1, result2)

    def test_generate_different_seeds(self):
        """测试不同种子产生不同输出"""
        generator = BlockGenerator()
        size = 20

        result1 = generator.generate(b'seed1', size)
        result2 = generator.generate(b'seed2', size)

        self.assertNotEqual(result1, result2)

    def test_generate_with_padding(self):
        """测试使用填充字节生成"""
        generator = BlockGenerator()
        seed = b'test'
        target_size = 10

        result = generator.generate_with_padding(seed, target_size, b'\xff')

        self.assertEqual(len(result), target_size)

    def test_generate_with_padding_zero_size(self):
        """测试填充生成零大小返回空字节"""
        generator = BlockGenerator()
        result = generator.generate_with_padding(b'seed', 0, b'\xff')

        self.assertEqual(result, b'')

    def test_generate_with_padding_invalid_padding_byte(self):
        """测试填充字节长度不为1时使用第一个字节"""
        generator = BlockGenerator()
        result = generator.generate_with_padding(b'seed', 10, b'\xff\x00')

        self.assertEqual(len(result), 10)


class TestVectorSpace(unittest.TestCase):
    """VectorSpace 类测试"""

    def test_initialization(self):
        """测试初始化"""
        space = VectorSpace(3)
        self.assertEqual(space.dimensions, 3)

    def test_create_vector(self):
        """测试创建向量"""
        space = VectorSpace(3)
        vector = space.create_vector(1.0, 2.0, 3.0)

        self.assertEqual(vector, [1.0, 2.0, 3.0])

    def test_create_vector_wrong_dimensions(self):
        """测试创建向量维度不匹配时抛出异常"""
        space = VectorSpace(3)

        with self.assertRaises(ValueError):
            space.create_vector(1.0, 2.0)

    def test_vector_add(self):
        """测试向量加法"""
        space = VectorSpace(3)
        v1 = [1.0, 2.0, 3.0]
        v2 = [4.0, 5.0, 6.0]

        result = space.vector_add(v1, v2)

        self.assertEqual(result, [5.0, 7.0, 9.0])

    def test_vector_add_mismatched_dimensions(self):
        """测试维度不匹配时抛出异常"""
        space = VectorSpace(3)

        with self.assertRaises(ValueError):
            space.vector_add([1.0, 2.0], [3.0, 4.0, 5.0])

    def test_vector_sub(self):
        """测试向量减法"""
        space = VectorSpace(3)
        v1 = [5.0, 7.0, 9.0]
        v2 = [1.0, 2.0, 3.0]

        result = space.vector_sub(v1, v2)

        self.assertEqual(result, [4.0, 5.0, 6.0])

    def test_vector_sub_mismatched_dimensions(self):
        """测试维度不匹配时抛出异常"""
        space = VectorSpace(3)

        with self.assertRaises(ValueError):
            space.vector_sub([1.0, 2.0], [3.0, 4.0, 5.0])

    def test_vector_mul(self):
        """测试向量乘以标量"""
        space = VectorSpace(3)
        v = [1.0, 2.0, 3.0]

        result = space.vector_mul(v, 2.0)

        self.assertEqual(result, [2.0, 4.0, 6.0])

    def test_vector_mul_fraction(self):
        """测试向量乘以分数"""
        space = VectorSpace(2)
        v = [1.0, 2.0]

        result = space.vector_mul(v, 0.5)

        self.assertEqual(result, [0.5, 1.0])

    def test_dot_product(self):
        """测试向量点积"""
        space = VectorSpace(3)
        v1 = [1.0, 2.0, 3.0]
        v2 = [4.0, 5.0, 6.0]

        result = space.dot_product(v1, v2)

        self.assertEqual(result, 32.0)  # 1*4 + 2*5 + 3*6

    def test_dot_product_mismatched_dimensions(self):
        """测试点积维度不匹配时抛出异常"""
        space = VectorSpace(3)

        with self.assertRaises(ValueError):
            space.dot_product([1.0, 2.0], [3.0, 4.0, 5.0])

    def test_dot_product_zero_vectors(self):
        """测试零向量的点积"""
        space = VectorSpace(3)
        result = space.dot_product([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])

        self.assertEqual(result, 0.0)


class TestSizeEncoder(unittest.TestCase):
    """SizeEncoder 类测试"""

    def test_initialization(self):
        """测试初始化"""
        encoder = SizeEncoder()
        # 无需特殊断言，只是确保不抛出异常

    def test_encode_size_zero(self):
        """测试编码零值"""
        encoder = SizeEncoder()
        result = encoder.encode_size(0)

        self.assertEqual(result, b'\x00\x00\x00\x00')

    def test_encode_size_positive(self):
        """测试编码正数"""
        encoder = SizeEncoder()
        result = encoder.encode_size(256)

        self.assertEqual(result, b'\x00\x01\x00\x00')  # 小端序

    def test_encode_size_negative(self):
        """测试编码负数时抛出异常"""
        encoder = SizeEncoder()

        with self.assertRaises(ValueError):
            encoder.encode_size(-1)

    def test_decode_size(self):
        """测试解码"""
        encoder = SizeEncoder()
        encoded = b'\x00\x01\x00\x00'
        result = encoder.decode_size(encoded)

        self.assertEqual(result, 256)

    def test_decode_size_short_buffer(self):
        """测试解码缓冲区不足时抛出异常"""
        encoder = SizeEncoder()

        with self.assertRaises(ValueError):
            encoder.decode_size(b'\x00\x01\x00')

    def test_encode_decode_roundtrip(self):
        """测试编码解码往返"""
        encoder = SizeEncoder()
        original = 12345

        encoded = encoder.encode_size(original)
        decoded = encoder.decode_size(encoded)

        self.assertEqual(decoded, original)

    def test_encode_size_varint_small(self):
        """测试变长编码小数字"""
        encoder = SizeEncoder()
        result = encoder.encode_size_varint(50)

        self.assertEqual(result, bytes([50]))

    def test_encode_size_varint_large(self):
        """测试变长编码大数字"""
        encoder = SizeEncoder()
        result = encoder.encode_size_varint(256)

        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 1)

    def test_encode_size_varint_negative(self):
        """测试变长编码负数时抛出异常"""
        encoder = SizeEncoder()

        with self.assertRaises(ValueError):
            encoder.encode_size_varint(-1)


class TestComponentPoolVM(unittest.TestCase):
    """ComponentPoolVM 类测试"""

    def test_initialization(self):
        """测试初始化"""
        vm = ComponentPoolVM()

        self.assertIsInstance(vm.seed_annotator, SeedAnnotator)
        self.assertIsInstance(vm.block_generator, BlockGenerator)
        self.assertIsInstance(vm.vector_space, VectorSpace)
        self.assertIsInstance(vm.size_encoder, SizeEncoder)
        self.assertEqual(vm.list_pools(), [])

    def test_create_pool(self):
        """测试创建池"""
        vm = ComponentPoolVM()
        vm.create_pool('test_pool', 10)

        self.assertIn('test_pool', vm.list_pools())
        self.assertEqual(len(vm._pools['test_pool']), 10)

    def test_add_to_pool(self):
        """测试向池中添加组件"""
        vm = ComponentPoolVM()
        vm.create_pool('test_pool', 0)
        vm.add_to_pool('test_pool', 'component1')

        self.assertEqual(vm.get_from_pool('test_pool', 0), 'component1')

    def test_add_to_pool_nonexistent(self):
        """测试向不存在的池添加组件时抛出异常"""
        vm = ComponentPoolVM()

        with self.assertRaises(KeyError):
            vm.add_to_pool('nonexistent', 'component')

    def test_get_from_pool(self):
        """测试从池中获取组件"""
        vm = ComponentPoolVM()
        vm.create_pool('test_pool', 5)
        vm.add_to_pool('test_pool', 'component1')
        vm.add_to_pool('test_pool', 'component2')

        self.assertEqual(vm.get_from_pool('test_pool', 5), 'component1')
        self.assertEqual(vm.get_from_pool('test_pool', 6), 'component2')

    def test_get_from_pool_nonexistent_pool(self):
        """测试从不存在的池获取时抛出异常"""
        vm = ComponentPoolVM()

        with self.assertRaises(KeyError):
            vm.get_from_pool('nonexistent', 0)

    def test_get_from_pool_invalid_index(self):
        """测试无效索引返回 None"""
        vm = ComponentPoolVM()
        vm.create_pool('test_pool', 5)

        self.assertIsNone(vm.get_from_pool('test_pool', -1))
        self.assertIsNone(vm.get_from_pool('test_pool', 100))

    def test_list_pools(self):
        """测试列出所有池"""
        vm = ComponentPoolVM()
        vm.create_pool('pool1', 10)
        vm.create_pool('pool2', 20)
        vm.create_pool('pool3', 30)

        pools = vm.list_pools()

        self.assertEqual(len(pools), 3)
        self.assertIn('pool1', pools)
        self.assertIn('pool2', pools)
        self.assertIn('pool3', pools)


if __name__ == '__main__':
    unittest.main()
