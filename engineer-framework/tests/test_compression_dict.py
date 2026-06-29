"""compression_dict 模块单元测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from src.compression_dict import CompressionDict


class TestCompressionDict(unittest.TestCase):
    """CompressionDict 类测试"""

    def test_initialization_empty(self):
        """测试初始化空字典"""
        comp = CompressionDict()
        self.assertEqual(comp.get_dict(), {})

    def test_initialization_with_dict(self):
        """测试使用字典初始化"""
        dictionary = {'a': 'alpha', 'b': 'beta'}
        comp = CompressionDict(dictionary)
        self.assertEqual(comp.get_dict(), dictionary)

    def test_load_dict(self):
        """测试加载字典"""
        dictionary = {'hello': 'world', 'foo': 'bar'}
        comp = CompressionDict()
        comp.load_dict(dictionary)
        self.assertEqual(comp.get_dict(), dictionary)

    def test_load_dict_invalid_type(self):
        """测试加载非字典类型时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(TypeError):
            comp.load_dict("not a dict")

    def test_load_dict_empty(self):
        """测试加载空字典时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(ValueError):
            comp.load_dict({})

    def test_load_dict_with_empty_key(self):
        """测试加载包含空键的字典时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(ValueError):
            comp.load_dict({'': 'value'})

    def test_load_dict_with_non_string_key(self):
        """测试加载包含非字符串键的字典时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(TypeError):
            comp.load_dict({1: 'value'})

    def test_load_dict_with_non_string_value(self):
        """测试加载包含非字符串值的字典时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(TypeError):
            comp.load_dict({'key': 123})

    def test_add_entry(self):
        """测试添加单个字典条目"""
        comp = CompressionDict({'a': 'alpha'})
        comp.add_entry('b', 'beta')
        self.assertEqual(comp.get_dict()['b'], 'beta')

    def test_add_entry_empty_key(self):
        """测试添加空键时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(ValueError):
            comp.add_entry('', 'value')

    def test_add_entry_invalid_key_type(self):
        """测试添加非字符串键时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(TypeError):
            comp.add_entry(123, 'value')

    def test_add_entry_invalid_value_type(self):
        """测试添加非字符串值时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(TypeError):
            comp.add_entry('key', 123)

    def test_compress_decompress_roundtrip(self):
        """测试压缩和解压缩的往返"""
        # 字典的键和值相同，这样压缩后解压才能还原
        dictionary = {
            'hello': 'hello',
            'foo': 'foo',
            'test': 'test',
        }
        comp = CompressionDict(dictionary)
        original = 'hellofootest'
        compressed = comp.compress(original)
        decompressed = comp.decompress(compressed)
        self.assertEqual(decompressed, original)

    def test_compress_longest_match(self):
        """测试最长匹配策略"""
        dictionary = {
            'ab': 'alpha',
            'abc': 'beta',
            'abcd': 'gamma'
        }
        comp = CompressionDict(dictionary)
        original = 'abcd'
        compressed = comp.compress(original)
        # 应该匹配最长的 'abcd'
        self.assertEqual(compressed, ['abcd'])

    def test_compress_single_char(self):
        """测试单个字符压缩"""
        dictionary = {'a': 'alpha', 'b': 'beta'}
        comp = CompressionDict(dictionary)
        original = 'ab'
        compressed = comp.compress(original)
        self.assertEqual(compressed, ['a', 'b'])

    def test_compress_no_matching_key(self):
        """测试压缩时遇到无匹配键抛出异常"""
        dictionary = {'a': 'alpha'}
        comp = CompressionDict(dictionary)
        with self.assertRaises(ValueError):
            comp.compress('bc')

    def test_compress_empty_data(self):
        """测试压缩空数据时抛出异常"""
        dictionary = {'a': 'alpha'}
        comp = CompressionDict(dictionary)
        with self.assertRaises(ValueError):
            comp.compress('')

    def test_compress_invalid_data_type(self):
        """测试压缩非字符串数据时抛出异常"""
        dictionary = {'a': 'alpha'}
        comp = CompressionDict(dictionary)
        with self.assertRaises(TypeError):
            comp.compress(123)

    def test_compress_empty_dict(self):
        """测试空字典压缩时抛出异常"""
        comp = CompressionDict()
        with self.assertRaises(ValueError):
            comp.compress('test')

    def test_decompress(self):
        """测试解压缩功能"""
        dictionary = {'hello': 'world', 'foo': 'bar'}
        comp = CompressionDict(dictionary)
        compressed = ['hello', 'foo']
        result = comp.decompress(compressed)
        self.assertEqual(result, 'worldbar')

    def test_decompress_invalid_type(self):
        """测试解压缩非列表类型时抛出异常"""
        dictionary = {'a': 'alpha'}
        comp = CompressionDict(dictionary)
        with self.assertRaises(TypeError):
            comp.decompress("not a list")

    def test_decompress_empty_list(self):
        """测试解压缩空列表时抛出异常"""
        dictionary = {'a': 'alpha'}
        comp = CompressionDict(dictionary)
        with self.assertRaises(ValueError):
            comp.decompress([])

    def test_decompress_invalid_key(self):
        """测试解压缩包含无效键时抛出异常"""
        dictionary = {'a': 'alpha'}
        comp = CompressionDict(dictionary)
        with self.assertRaises(ValueError):
            comp.decompress(['unknown_key'])

    def test_decompress_non_string_key(self):
        """测试解压缩包含非字符串键时抛出异常"""
        dictionary = {'a': 'alpha'}
        comp = CompressionDict(dictionary)
        with self.assertRaises(TypeError):
            comp.decompress([123])

    def test_get_dict(self):
        """测试获取字典副本"""
        dictionary = {'a': 'alpha', 'b': 'beta'}
        comp = CompressionDict(dictionary)
        result = comp.get_dict()
        self.assertEqual(result, dictionary)
        # 确保返回的是副本
        result['c'] = 'gamma'
        self.assertNotIn('c', comp.get_dict())


if __name__ == '__main__':
    unittest.main()
