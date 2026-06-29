"""
串口模块 - 提供串口通信功能

该模块提供SerialConfig配置类和SerialPort通信类，用于串口通信管理。
支持pyserial库，当pyserial不可用时会提供友好的错误处理。
"""

try:
    import serial
    import serial.tools.list_ports
    PYSCERIAL_AVAILABLE = True
except ImportError:
    PYSCERIAL_AVAILABLE = False


class SerialConfig:
    """
    串口配置类 - 用于存储和管理串口通信参数
    
    Attributes:
        port (str): 串口名称，如'COM1'、'/dev/ttyUSB0'等
        baudrate (int): 波特率，默认为9600
        bytesize (int): 数据位长度，默认为8
        stopbits (int): 停止位长度，默认为1
        parity (str): 校验位，默认为'N'（无校验）
            可选值: 'N'（无校验）, 'E'（偶校验）, 'O'（奇校验）
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        bytesize: int = 8,
        stopbits: int = 1,
        parity: str = 'N'
    ):
        """
        初始化串口配置
        
        Args:
            port: 串口名称
            baudrate: 波特率，默认为9600
            bytesize: 数据位长度，默认为8
            stopbits: 停止位长度，默认为1
            parity: 校验位，默认为'N'（无校验）
        """
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._stopbits = stopbits
        self._parity = parity
    
    @property
    def port(self) -> str:
        """获取串口名称"""
        return self._port
    
    @port.setter
    def port(self, value: str):
        """设置串口名称"""
        self._port = value
    
    @property
    def baudrate(self) -> int:
        """获取波特率"""
        return self._baudrate
    
    @baudrate.setter
    def baudrate(self, value: int):
        """设置波特率"""
        self._baudrate = value
    
    @property
    def bytesize(self) -> int:
        """获取数据位长度"""
        return self._bytesize
    
    @bytesize.setter
    def bytesize(self, value: int):
        """设置数据位长度"""
        self._bytesize = value
    
    @property
    def stopbits(self) -> int:
        """获取停止位长度"""
        return self._stopbits
    
    @stopbits.setter
    def stopbits(self, value: int):
        """设置停止位长度"""
        self._stopbits = value
    
    @property
    def parity(self) -> str:
        """获取校验位"""
        return self._parity
    
    @parity.setter
    def parity(self, value: str):
        """设置校验位"""
        self._parity = value
    
    def to_dict(self) -> dict:
        """
        将配置转换为字典格式
        
        Returns:
            dict: 包含所有配置参数的字典
        """
        return {
            'port': self._port,
            'baudrate': self._baudrate,
            'bytesize': self._bytesize,
            'stopbits': self._stopbits,
            'parity': self._parity
        }


class SerialPort:
    """
    串口通信类 - 提供串口连接和数据收发功能
    
    该类封装了pyserial库的功能，提供连接、断开、发送、接收等操作。
    当pyserial库不可用时，所有方法会返回适当的错误响应。
    
    Attributes:
        config (SerialConfig): 串口配置对象
        _serial_instance: pyserial Serial实例，用于内部管理
    """
    
    def __init__(self, config: SerialConfig):
        """
        初始化串口通信对象
        
        Args:
            config: 串口配置对象（SerialConfig实例）
        """
        self.config = config
        self._serial_instance = None
    
    def connect(self) -> bool:
        """
        建立串口连接
        
        根据配置参数打开串口并建立通信连接。
        如果pyserial库不可用，返回False。
        如果已经连接，先断开再重新连接。
        
        Returns:
            bool: 连接成功返回True，失败返回False
        """
        if not PYSCERIAL_AVAILABLE:
            return False
        
        if self._serial_instance is not None:
            self.disconnect()
        
        try:
            self._serial_instance = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                stopbits=self.config.stopbits,
                parity=self.config.parity,
                timeout=1.0
            )
            return True
        except (serial.SerialException, OSError):
            self._serial_instance = None
            return False
    
    def disconnect(self) -> None:
        """
        关闭串口连接
        
        如果尚未连接或pyserial不可用，此方法不做任何操作。
        """
        if self._serial_instance is not None:
            try:
                self._serial_instance.close()
            except Exception:
                pass
            finally:
                self._serial_instance = None
    
    def is_connected(self) -> bool:
        """
        检查串口连接状态
        
        Returns:
            bool: 已连接返回True，未连接或pyserial不可用返回False
        """
        if not PYSCERIAL_AVAILABLE:
            return False
        return self._serial_instance is not None and self._serial_instance.is_open
    
    def send(self, data: bytes) -> int:
        """
        发送数据
        
        通过串口发送原始字节数据。
        
        Args:
            data: 要发送的字节数据
            
        Returns:
            int: 成功发送的字节数，未连接或失败返回-1
        """
        if not self.is_connected():
            return -1
        
        try:
            return self._serial_instance.write(data)
        except Exception:
            return -1
    
    def receive(self, timeout: float = 1.0) -> bytes:
        """
        接收数据
        
        从串口接收数据，支持自定义超时时间。
        
        Args:
            timeout: 接收超时时间（秒），默认为1.0秒
            
        Returns:
            bytes: 接收到的字节数据，超时或失败返回空字节串b''
        """
        if not self.is_connected():
            return b''
        
        old_timeout = self._serial_instance.timeout
        self._serial_instance.timeout = timeout
        
        try:
            data = self._serial_instance.read(1024)
            return data
        except Exception:
            return b''
        finally:
            self._serial_instance.timeout = old_timeout
    
    def send_and_receive(self, data: bytes, timeout: float = 1.0) -> bytes:
        """
        发送数据并等待响应
        
        发送数据后立即等待接收响应数据。
        
        Args:
            data: 要发送的字节数据
            timeout: 接收超时时间（秒），默认为1.0秒
            
        Returns:
            bytes: 接收到的响应字节数据，超时或失败返回空字节串b''
        """
        if not self.is_connected():
            return b''
        
        sent = self.send(data)
        if sent <= 0:
            return b''
        
        return self.receive(timeout)
    
    def __del__(self):
        """析构函数，确保串口连接被正确关闭"""
        self.disconnect()
