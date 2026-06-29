"""signal_simulator 模块单元测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from src.signal_simulator import SignalTemplate, Loadpoint, SignalSimulator


class TestSignalTemplate(unittest.TestCase):
    """SignalTemplate 类测试"""

    def test_initialization_with_name(self):
        """测试使用名称初始化"""
        template = SignalTemplate('test_template')
        self.assertEqual(template.name, 'test_template')
        self.assertEqual(template.list_signals(), [])

    def test_initialization_with_signal_defs_tuple(self):
        """测试使用元组格式的信号定义初始化"""
        signal_defs = {
            'signal1': (b'response1', 0.5),
            'signal2': (b'response2', 1.0)
        }
        template = SignalTemplate('test', signal_defs)
        self.assertEqual(template.name, 'test')
        self.assertIn('signal1', template.list_signals())
        self.assertIn('signal2', template.list_signals())

    def test_initialization_with_signal_defs_single_value(self):
        """测试使用单个值的信号定义初始化"""
        signal_defs = {
            'signal1': b'response1'
        }
        template = SignalTemplate('test', signal_defs)
        response, delay = template.get_response('signal1')
        self.assertEqual(response, b'response1')
        self.assertEqual(delay, 0)

    def test_add_signal(self):
        """测试添加信号定义"""
        template = SignalTemplate('test')
        template.add_signal('test_signal', b'test_response', 0.5)

        self.assertIn('test_signal', template.list_signals())
        response, delay = template.get_response('test_signal')
        self.assertEqual(response, b'test_response')
        self.assertEqual(delay, 0.5)

    def test_add_signal_default_delay(self):
        """测试添加信号时使用默认延迟"""
        template = SignalTemplate('test')
        template.add_signal('signal1', b'response')

        response, delay = template.get_response('signal1')
        self.assertEqual(response, b'response')
        self.assertEqual(delay, 0)

    def test_get_response(self):
        """测试获取信号响应"""
        template = SignalTemplate('test')
        template.add_signal('sig', b'response_data', 1.5)

        response, delay = template.get_response('sig')
        self.assertEqual(response, b'response_data')
        self.assertEqual(delay, 1.5)

    def test_get_response_not_found(self):
        """测试获取不存在的信号时抛出异常"""
        template = SignalTemplate('test')

        with self.assertRaises(KeyError):
            template.get_response('nonexistent')

    def test_list_signals(self):
        """测试列出所有信号"""
        signal_defs = {
            'sig1': (b'res1', 0.1),
            'sig2': (b'res2', 0.2),
            'sig3': (b'res3', 0.3)
        }
        template = SignalTemplate('test', signal_defs)
        signals = template.list_signals()

        self.assertEqual(len(signals), 3)
        self.assertIn('sig1', signals)
        self.assertIn('sig2', signals)
        self.assertIn('sig3', signals)


class TestLoadpoint(unittest.TestCase):
    """Loadpoint 类测试"""

    def test_initialization(self):
        """测试初始化"""
        loadpoint = Loadpoint('test_loadpoint')
        self.assertEqual(loadpoint.name, 'test_loadpoint')
        self.assertEqual(loadpoint.control_mapping, {})

    def test_initialization_with_mapping(self):
        """测试使用控制映射初始化"""
        mapping = {'key1': 'value1', 'key2': 'value2'}
        loadpoint = Loadpoint('test')
        loadpoint._control_mapping = mapping

        self.assertEqual(loadpoint.control_mapping, mapping)

    def test_control_mapping_property(self):
        """测试 control_mapping 属性"""
        loadpoint = Loadpoint('test')
        self.assertEqual(loadpoint.control_mapping, {})


class TestSignalSimulator(unittest.TestCase):
    """SignalSimulator 类测试"""

    def test_initialization(self):
        """测试初始化"""
        simulator = SignalSimulator()
        self.assertIsNone(simulator._template)
        self.assertEqual(simulator.get_mounted_loadpoints(), [])

    def test_load_template(self):
        """测试加载信号模板"""
        simulator = SignalSimulator()
        template = SignalTemplate('test')
        template.add_signal('sig', b'response', 0.5)

        simulator.load_template(template)
        self.assertEqual(simulator._template, template)

    def test_simulate_signal(self):
        """测试模拟信号"""
        simulator = SignalSimulator()
        template = SignalTemplate('test')
        template.add_signal('sig', b'response_data', 0.5)
        simulator.load_template(template)

        result = simulator.simulate_signal('sig')
        self.assertEqual(result, b'response_data')

    def test_simulate_signal_no_template(self):
        """测试未加载模板时模拟信号抛出异常"""
        simulator = SignalSimulator()

        with self.assertRaises(RuntimeError):
            simulator.simulate_signal('sig')

    def test_simulate_signal_not_found(self):
        """测试模拟不存在的信号抛出异常"""
        simulator = SignalSimulator()
        template = SignalTemplate('test')
        simulator.load_template(template)

        with self.assertRaises(KeyError):
            simulator.simulate_signal('nonexistent')

    def test_mount_loadpoint(self):
        """测试挂载加载点"""
        simulator = SignalSimulator()
        control_mapping = {'key1': 'value1', 'key2': 'value2'}

        simulator.mount_loadpoint('test_loadpoint', control_mapping)

        self.assertIn('test_loadpoint', simulator.get_mounted_loadpoints())
        loadpoint = simulator._loadpoints['test_loadpoint']
        self.assertEqual(loadpoint.name, 'test_loadpoint')
        self.assertEqual(loadpoint.control_mapping, control_mapping)

    def test_unmount_loadpoint(self):
        """测试卸载加载点"""
        simulator = SignalSimulator()
        simulator.mount_loadpoint('test_lp', {})

        simulator.unmount_loadpoint('test_lp')

        self.assertNotIn('test_lp', simulator.get_mounted_loadpoints())

    def test_unmount_loadpoint_not_found(self):
        """测试卸载不存在的加载点抛出异常"""
        simulator = SignalSimulator()

        with self.assertRaises(KeyError):
            simulator.unmount_loadpoint('nonexistent')

    def test_get_mounted_loadpoints(self):
        """测试获取已挂载的加载点列表"""
        simulator = SignalSimulator()
        simulator.mount_loadpoint('lp1', {})
        simulator.mount_loadpoint('lp2', {})
        simulator.mount_loadpoint('lp3', {})

        loadpoints = simulator.get_mounted_loadpoints()

        self.assertEqual(len(loadpoints), 3)
        self.assertIn('lp1', loadpoints)
        self.assertIn('lp2', loadpoints)
        self.assertIn('lp3', loadpoints)

    def test_unmount_and_remount(self):
        """测试卸载后重新挂载"""
        simulator = SignalSimulator()
        simulator.mount_loadpoint('lp', {'key': 'value'})
        simulator.unmount_loadpoint('lp')
        simulator.mount_loadpoint('lp', {'new_key': 'new_value'})

        self.assertIn('lp', simulator.get_mounted_loadpoints())
        self.assertEqual(
            simulator._loadpoints['lp'].control_mapping,
            {'new_key': 'new_value'}
        )


if __name__ == '__main__':
    unittest.main()
