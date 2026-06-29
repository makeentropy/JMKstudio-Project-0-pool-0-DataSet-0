"""wired_mapping 模块单元测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from src.wired_mapping import (
    WireScriptParser,
    XORtagPool,
    MappingSimulator
)


class TestWireScriptParser(unittest.TestCase):
    """WireScriptParser 类测试"""

    def test_initialization(self):
        """测试初始化"""
        parser = WireScriptParser()
        self.assertEqual(parser.script_data, {})
        self.assertEqual(parser.connections, [])
        self.assertEqual(parser.xor_tags, {})

    def test_parse_empty_script(self):
        """测试解析空脚本"""
        parser = WireScriptParser()
        result = parser.parse('')

        self.assertEqual(result, {"connections": [], "xortags": {}})

    def test_parse_comment_lines(self):
        """测试解析包含注释的脚本"""
        script = """
        # This is a comment
        XORTAG tag1 = 48656c6c6f
        CONNECT node_a -> node_b MODE direct
        """
        parser = WireScriptParser()
        result = parser.parse(script)

        self.assertEqual(len(result["connections"]), 1)
        self.assertEqual(result["connections"][0]["from_node"], "node_a")
        self.assertEqual(result["connections"][0]["to_node"], "node_b")
        self.assertEqual(result["connections"][0]["mode"], "direct")
        self.assertIn("tag1", result["xortags"])

    def test_parse_xortag(self):
        """测试解析 XORTAG"""
        script = "XORTAG mytag = deadbeef"
        parser = WireScriptParser()
        result = parser.parse(script)

        self.assertEqual(result["xortags"]["mytag"], b'\xde\xad\xbe\xef')

    def test_parse_connect(self):
        """测试解析 CONNECT"""
        script = "CONNECT node_a -> node_b MODE template"
        parser = WireScriptParser()
        result = parser.parse(script)

        self.assertEqual(len(result["connections"]), 1)
        conn = result["connections"][0]
        self.assertEqual(conn["from_node"], "node_a")
        self.assertEqual(conn["to_node"], "node_b")
        self.assertEqual(conn["mode"], "template")

    def test_parse_connect_default_mode(self):
        """测试解析 CONNECT 使用默认模式"""
        script = "CONNECT a -> b MODE direct"
        parser = WireScriptParser()
        result = parser.parse(script)

        self.assertEqual(result["connections"][0]["mode"], "direct")

    def test_parse_multiple_connections(self):
        """测试解析多条连接"""
        script = """
        CONNECT a -> b MODE direct
        CONNECT c -> d MODE template
        CONNECT e -> f MODE mapping
        """
        parser = WireScriptParser()
        result = parser.parse(script)

        self.assertEqual(len(result["connections"]), 3)

    def test_parse_connection(self):
        """测试解析单条连接行"""
        parser = WireScriptParser()
        line = "CONNECT node_a -> node_b MODE direct"
        result = parser.parse_connection(line)

        self.assertEqual(result["from_node"], "node_a")
        self.assertEqual(result["to_node"], "node_b")
        self.assertEqual(result["mode"], "direct")

    def test_parse_connection_invalid_line(self):
        """测试解析无效连接行"""
        parser = WireScriptParser()
        result = parser.parse_connection("XORTAG tag = deadbeef")

        self.assertEqual(result, {})

    def test_parse_connection_short_line(self):
        """测试解析长度不足的连接行"""
        parser = WireScriptParser()
        result = parser.parse_connection("CONNECT a -> b")

        self.assertEqual(result, {})

    def test_validate_script_valid(self):
        """测试验证有效脚本"""
        script = """
        XORTAG tag1 = deadbeef
        CONNECT node_a -> node_b MODE direct
        """
        parser = WireScriptParser()
        result = parser.validate_script(script)

        self.assertTrue(result)

    def test_validate_script_invalid_xortag(self):
        """测试验证无效 XORTAG"""
        script = "XORTAG tag1 deadbeef"
        parser = WireScriptParser()
        result = parser.validate_script(script)

        self.assertFalse(result)

    def test_validate_script_invalid_connect(self):
        """测试验证无效 CONNECT"""
        script = "CONNECT a b MODE direct"
        parser = WireScriptParser()
        result = parser.validate_script(script)

        self.assertFalse(result)

    def test_validate_script_unknown_command(self):
        """测试验证未知命令"""
        script = "UNKNOWN command"
        parser = WireScriptParser()
        result = parser.validate_script(script)

        self.assertFalse(result)

    def test_validate_script_empty(self):
        """测试验证空脚本"""
        parser = WireScriptParser()
        result = parser.validate_script("")

        self.assertTrue(result)


class TestXORtagPool(unittest.TestCase):
    """XORtagPool 类测试"""

    def test_initialization(self):
        """测试初始化"""
        pool = XORtagPool()
        self.assertEqual(pool.tags, {})

    def test_define_tag(self):
        """测试定义标签"""
        pool = XORtagPool()
        pool.define_tag('mytag', b'\xde\xad\xbe\xef')

        self.assertEqual(pool.tags['mytag'], b'\xde\xad\xbe\xef')

    def test_get_tag_existing(self):
        """测试获取已存在的标签"""
        pool = XORtagPool()
        pool.define_tag('mytag', b'\xde\xad\xbe\xef')

        result = pool.get_tag('mytag')

        self.assertEqual(result, b'\xde\xad\xbe\xef')

    def test_get_tag_nonexistent(self):
        """测试获取不存在的标签返回空字节"""
        pool = XORtagPool()

        result = pool.get_tag('nonexistent')

        self.assertEqual(result, b'')

    def test_apply_xor_tag(self):
        """测试应用 XOR 标签"""
        pool = XORtagPool()
        pool.define_tag('tag', b'\x0f\x0f\x0f\x0f')
        data = b'\x48\x65\x6c\x6c\x6f'  # 'Hello'

        result = pool.apply_xor_tag(data, 'tag')

        # 0x48 ^ 0x0f = 0x47 = 'G'
        # 0x65 ^ 0x0f = 0x6a = 'j'
        # 0x6c ^ 0x0f = 0x63 = 'c'
        # 0x6c ^ 0x0f = 0x63 = 'c'
        # 0x6f ^ 0x0f = 0x60 = '`'
        self.assertEqual(result, b'Gjcc`')

    def test_apply_xor_tag_nonexistent(self):
        """测试应用不存在的标签返回原始数据"""
        pool = XORtagPool()
        data = b'\x48\x65\x6c\x6c\x6f'

        result = pool.apply_xor_tag(data, 'nonexistent')

        self.assertEqual(result, data)

    def test_apply_xor_tag_repeating(self):
        """测试应用短标签到长数据（标签重复）"""
        pool = XORtagPool()
        pool.define_tag('tag', b'\x01')
        data = b'\xff\xff\xff\xff\xff'

        result = pool.apply_xor_tag(data, 'tag')

        self.assertEqual(result, b'\xfe\xfe\xfe\xfe\xfe')

    def test_list_tags(self):
        """测试列出所有标签"""
        pool = XORtagPool()
        pool.define_tag('tag1', b'\x01')
        pool.define_tag('tag2', b'\x02')
        pool.define_tag('tag3', b'\x03')

        result = pool.list_tags()

        self.assertEqual(len(result), 3)
        self.assertIn('tag1', result)
        self.assertIn('tag2', result)
        self.assertIn('tag3', result)

    def test_remove_tag(self):
        """测试移除标签"""
        pool = XORtagPool()
        pool.define_tag('tag', b'\x01')
        pool.remove_tag('tag')

        self.assertNotIn('tag', pool.tags)

    def test_remove_tag_nonexistent(self):
        """测试移除不存在的标签不抛出异常"""
        pool = XORtagPool()
        pool.remove_tag('nonexistent')  # 不应抛出异常


class TestMappingSimulator(unittest.TestCase):
    """MappingSimulator 类测试"""

    def test_initialization(self):
        """测试初始化"""
        simulator = MappingSimulator()

        self.assertIsInstance(simulator.parser, WireScriptParser)
        self.assertIsInstance(simulator.xor_pool, XORtagPool)
        self.assertEqual(simulator.connections, {})
        self.assertEqual(simulator.current_script, "")

    def test_load_script(self):
        """测试加载脚本"""
        script = """
        XORTAG tag1 = deadbeef
        CONNECT node_a -> node_b MODE direct
        """
        simulator = MappingSimulator()
        result = simulator.load_script(script)

        self.assertTrue(result)
        self.assertEqual(simulator.current_script, script)

    def test_load_script_invalid(self):
        """测试加载无效脚本"""
        script = "INVALID command"
        simulator = MappingSimulator()
        result = simulator.load_script(script)

        self.assertFalse(result)

    def test_connect_nodes(self):
        """测试连接节点"""
        simulator = MappingSimulator()
        simulator.connect_nodes('node_a', 'node_b', 'direct')

        key = 'node_a->node_b'
        self.assertIn(key, simulator.connections)
        self.assertEqual(simulator.connections[key]['node_a'], 'node_a')
        self.assertEqual(simulator.connections[key]['node_b'], 'node_b')
        self.assertEqual(simulator.connections[key]['mode'], 'direct')
        self.assertTrue(simulator.connections[key]['active'])

    def test_connect_nodes_default_mode(self):
        """测试连接节点使用默认模式"""
        simulator = MappingSimulator()
        simulator.connect_nodes('a', 'b')

        self.assertEqual(simulator.connections['a->b']['mode'], 'direct')

    def test_disconnect_nodes(self):
        """测试断开节点"""
        simulator = MappingSimulator()
        simulator.connect_nodes('a', 'b', 'direct')
        simulator.disconnect_nodes('a', 'b')

        self.assertFalse(simulator.connections['a->b']['active'])

    def test_get_connection_status_connected(self):
        """测试获取已连接状态"""
        simulator = MappingSimulator()
        simulator.connect_nodes('a', 'b', 'template')

        status = simulator.get_connection_status('a', 'b')

        self.assertTrue(status['connected'])
        self.assertEqual(status['mode'], 'template')
        self.assertEqual(status['node_a'], 'a')
        self.assertEqual(status['node_b'], 'b')

    def test_get_connection_status_not_connected(self):
        """测试获取未连接状态"""
        simulator = MappingSimulator()

        status = simulator.get_connection_status('a', 'b')

        self.assertFalse(status['connected'])

    def test_execute_connection(self):
        """测试执行连接数据传输"""
        simulator = MappingSimulator()
        simulator.connect_nodes('a', 'b', 'direct')
        data = b'\x48\x65\x6c\x6c\x6f'

        result = simulator.execute_connection('a', 'b', data)

        self.assertEqual(result, data)  # direct 模式不做处理

    def test_execute_connection_not_connected(self):
        """测试执行未连接节点的数据传输"""
        simulator = MappingSimulator()
        data = b'\x48\x65\x6c\x6c\x6f'

        result = simulator.execute_connection('a', 'b', data)

        self.assertEqual(result, data)  # 未连接返回原始数据

    def test_apply_mode_direct(self):
        """测试应用 direct 模式"""
        simulator = MappingSimulator()
        data = b'\x48\x65\x6c\x6c\x6f'

        result = simulator.apply_mode('direct', data)

        self.assertEqual(result, data)

    def test_apply_mode_template(self):
        """测试应用 template 模式"""
        simulator = MappingSimulator()
        data = b'\x48\x65\x6c\x6c\x6f'

        result = simulator.apply_mode('template', data)

        # template 模式目前返回原始数据
        self.assertEqual(result, data)

    def test_apply_mode_mapping(self):
        """测试应用 mapping 模式"""
        simulator = MappingSimulator()
        data = b'\x48\x65\x6c\x6c\x6f'

        result = simulator.apply_mode('mapping', data)

        # mapping 模式目前返回原始数据
        self.assertEqual(result, data)

    def test_apply_mode_script(self):
        """测试应用 script 模式"""
        simulator = MappingSimulator()
        data = b'\x48\x65\x6c\x6c\x6f'

        result = simulator.apply_mode('script', data)

        # script 模式目前返回原始数据
        self.assertEqual(result, data)

    def test_apply_mode_unknown(self):
        """测试应用未知模式"""
        simulator = MappingSimulator()
        data = b'\x48\x65\x6c\x6c\x6f'

        result = simulator.apply_mode('unknown', data)

        self.assertEqual(result, data)

    def test_load_script_with_xortags(self):
        """测试加载包含 XORTAG 的脚本"""
        script = """
        XORTAG tag1 = deadbeef
        XORTAG tag2 = beefdead
        """
        simulator = MappingSimulator()
        simulator.load_script(script)

        self.assertEqual(simulator.xor_pool.get_tag('tag1'), b'\xde\xad\xbe\xef')
        self.assertEqual(simulator.xor_pool.get_tag('tag2'), b'\xbe\xef\xde\xad')

    def test_load_script_with_connections(self):
        """测试加载包含连接的脚本"""
        script = """
        CONNECT a -> b MODE direct
        CONNECT c -> d MODE template
        """
        simulator = MappingSimulator()
        simulator.load_script(script)

        self.assertIn('a->b', simulator.connections)
        self.assertIn('c->d', simulator.connections)
        self.assertEqual(simulator.connections['c->d']['mode'], 'template')


if __name__ == '__main__':
    unittest.main()
