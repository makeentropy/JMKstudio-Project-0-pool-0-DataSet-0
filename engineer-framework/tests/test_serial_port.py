"""serial_port 模块单元测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from types import ModuleType


class TestSerialConfig(unittest.TestCase):
    """SerialConfig 类测试"""

    def test_initialization_default(self):
        """测试使用默认参数初始化"""
        config = SerialPortConfig('COM1')
        self.assertEqual(config.port, 'COM1')
        self.assertEqual(config.baudrate, 9600)
        self.assertEqual(config.bytesize, 8)
        self.assertEqual(config.stopbits, 1)
        self.assertEqual(config.parity, 'N')

    def test_initialization_custom(self):
        """测试使用自定义参数初始化"""
        config = SerialPortConfig(
            port='/dev/ttyUSB0',
            baudrate=115200,
            bytesize=7,
            stopbits=2,
            parity='E'
        )
        self.assertEqual(config.port, '/dev/ttyUSB0')
        self.assertEqual(config.baudrate, 115200)
        self.assertEqual(config.bytesize, 7)
        self.assertEqual(config.stopbits, 2)
        self.assertEqual(config.parity, 'E')

    def test_properties_setters(self):
        """测试属性 getter 和 setter"""
        config = SerialPortConfig('COM1')
        config.port = 'COM2'
        config.baudrate = 57600
        config.bytesize = 5
        config.stopbits = 1.5
        config.parity = 'O'

        self.assertEqual(config.port, 'COM2')
        self.assertEqual(config.baudrate, 57600)
        self.assertEqual(config.bytesize, 5)
        self.assertEqual(config.stopbits, 1.5)
        self.assertEqual(config.parity, 'O')

    def test_to_dict(self):
        """测试转换为字典格式"""
        config = SerialPortConfig(
            port='COM1',
            baudrate=9600,
            bytesize=8,
            stopbits=1,
            parity='N'
        )
        result = config.to_dict()
        expected = {
            'port': 'COM1',
            'baudrate': 9600,
            'bytesize': 8,
            'stopbits': 1,
            'parity': 'N'
        }
        self.assertEqual(result, expected)


class TestSerialPortWithPyserialUnavailable(unittest.TestCase):
    """测试 pyserial 不可用时的行为"""

    def setUp(self):
        """设置测试环境"""
        # 保存原始值
        self._original_pyserial_available = serial_port_module.PYSCERIAL_AVAILABLE
        # 模拟 pyserial 不可用
        serial_port_module.PYSCERIAL_AVAILABLE = False

    def tearDown(self):
        """恢复原始状态"""
        serial_port_module.PYSCERIAL_AVAILABLE = self._original_pyserial_available

    def test_connect_returns_false_when_pyserial_unavailable(self):
        """测试 pyserial 不可用时连接返回 False"""
        config = SerialPortConfig('COM1')
        port = SerialPort(config)
        result = port.connect()
        self.assertFalse(result)

    def test_is_connected_false_when_pyserial_unavailable(self):
        """测试 pyserial 不可用时 is_connected 返回 False"""
        config = SerialPortConfig('COM1')
        port = SerialPort(config)
        self.assertFalse(port.is_connected())

    def test_send_returns_minus_one_when_pyserial_unavailable(self):
        """测试 pyserial 不可用时发送返回 -1"""
        config = SerialPortConfig('COM1')
        port = SerialPort(config)
        result = port.send(b'hello')
        self.assertEqual(result, -1)

    def test_receive_returns_empty_when_pyserial_unavailable(self):
        """测试 pyserial 不可用时接收返回空字节"""
        config = SerialPortConfig('COM1')
        port = SerialPort(config)
        result = port.receive()
        self.assertEqual(result, b'')


class TestSerialPortWithMockedPyserial(unittest.TestCase):
    """使用模拟 pyserial 进行测试"""

    def _setup_mock_serial(self):
        """设置模拟的 serial 模块"""
        # 创建模拟的 serial 模块
        self.mock_serial_module = ModuleType('serial')
        self.mock_serial_class = MagicMock()
        self.mock_serial_exception_class = type('SerialException', (Exception,), {})
        self.mock_serial_module.Serial = self.mock_serial_class
        self.mock_serial_module.SerialException = self.mock_serial_exception_class
        self.mock_serial_module.tools = ModuleType('serial.tools')
        self.mock_serial_module.tools.list_ports = ModuleType('serial.tools.list_ports')

        # 保存原始模块并替换
        self._original_serial = sys.modules.get('serial')
        self._original_serial_tools = sys.modules.get('serial.tools')
        self._original_serial_tools_list_ports = sys.modules.get('serial.tools.list_ports')

        sys.modules['serial'] = self.mock_serial_module
        sys.modules['serial.tools'] = self.mock_serial_module.tools
        sys.modules['serial.tools.list_ports'] = self.mock_serial_module.tools.list_ports

        # 重新加载模块
        import importlib
        import src.serial_port as sp_module
        importlib.reload(sp_module)

        # 更新 PYSCERIAL_AVAILABLE
        sp_module.PYSCERIAL_AVAILABLE = True

        return sp_module

    def _restore_original_modules(self):
        """恢复原始模块"""
        if self._original_serial is not None:
            sys.modules['serial'] = self._original_serial
        elif 'serial' in sys.modules:
            del sys.modules['serial']

        if self._original_serial_tools is not None:
            sys.modules['serial.tools'] = self._original_serial_tools
        elif 'serial.tools' in sys.modules:
            del sys.modules['serial.tools']

        if self._original_serial_tools_list_ports is not None:
            sys.modules['serial.tools.list_ports'] = self._original_serial_tools_list_ports
        elif 'serial.tools.list_ports' in sys.modules:
            del sys.modules['serial.tools.list_ports']

    def tearDown(self):
        """清理"""
        self._restore_original_modules()

    def test_connect_success(self):
        """测试成功建立连接"""
        sp_module = self._setup_mock_serial()
        mock_instance = MagicMock()
        self.mock_serial_module.Serial.return_value = mock_instance
        mock_instance.is_open = True

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        result = port.connect()

        self.assertTrue(result)
        self.mock_serial_module.Serial.assert_called_once()

    def test_connect_failure(self):
        """测试连接失败"""
        sp_module = self._setup_mock_serial()
        self.mock_serial_module.Serial.side_effect = self.mock_serial_module.SerialException("Error")

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        result = port.connect()

        self.assertFalse(result)

    def test_disconnect(self):
        """测试断开连接"""
        sp_module = self._setup_mock_serial()
        mock_instance = MagicMock()
        self.mock_serial_module.Serial.return_value = mock_instance
        mock_instance.is_open = True

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        port.connect()
        port.disconnect()

        mock_instance.close.assert_called_once()
        self.assertIsNone(port._serial_instance)

    def test_is_connected_true(self):
        """测试已连接状态返回 True"""
        sp_module = self._setup_mock_serial()
        mock_instance = MagicMock()
        self.mock_serial_module.Serial.return_value = mock_instance
        mock_instance.is_open = True

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        port.connect()

        self.assertTrue(port.is_connected())

    def test_is_connected_false(self):
        """测试未连接状态返回 False"""
        sp_module = self._setup_mock_serial()

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)

        self.assertFalse(port.is_connected())

    def test_send_success(self):
        """测试成功发送数据"""
        sp_module = self._setup_mock_serial()
        mock_instance = MagicMock()
        self.mock_serial_module.Serial.return_value = mock_instance
        mock_instance.is_open = True
        mock_instance.write.return_value = 5

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        port.connect()
        result = port.send(b'hello')

        self.assertEqual(result, 5)

    def test_send_not_connected(self):
        """测试未连接时发送返回 -1"""
        sp_module = self._setup_mock_serial()

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        result = port.send(b'hello')

        self.assertEqual(result, -1)

    def test_receive_success(self):
        """测试成功接收数据"""
        sp_module = self._setup_mock_serial()
        mock_instance = MagicMock()
        self.mock_serial_module.Serial.return_value = mock_instance
        mock_instance.is_open = True
        mock_instance.read.return_value = b'response data'

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        port.connect()
        result = port.receive(timeout=0.5)

        self.assertEqual(result, b'response data')

    def test_receive_not_connected(self):
        """测试未连接时接收返回空字节"""
        sp_module = self._setup_mock_serial()

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        result = port.receive()

        self.assertEqual(result, b'')

    def test_send_and_receive_success(self):
        """测试发送并接收成功"""
        sp_module = self._setup_mock_serial()
        mock_instance = MagicMock()
        self.mock_serial_module.Serial.return_value = mock_instance
        mock_instance.is_open = True
        mock_instance.write.return_value = 5
        mock_instance.read.return_value = b'response'

        config = sp_module.SerialConfig('COM1')
        port = sp_module.SerialPort(config)
        port.connect()
        result = port.send_and_receive(b'hello')

        self.assertEqual(result, b'response')


# 导入模块供测试使用
import src.serial_port as serial_port_module
from src.serial_port import SerialConfig as SerialPortConfig, SerialPort


if __name__ == '__main__':
    unittest.main()
