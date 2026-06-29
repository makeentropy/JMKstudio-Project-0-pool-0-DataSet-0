"""
信号模拟器模块

提供串行信号仿真模板管理、信号模拟引擎和挂载点管理功能。
"""


class SignalTemplate:
    """
    串行信号仿真模板类

    用于定义和管理一组信号及其响应规则。
    """

    def __init__(self, name: str, signal_defs: dict = None):
        """
        初始化信号模板

        Args:
            name: 模板名称
            signal_defs: 信号定义字典，格式为 {signal_name: (response, delay)}，默认为空字典
        """
        self.name = name
        self._signals = {}
        if signal_defs:
            for signal_name, definition in signal_defs.items():
                if isinstance(definition, tuple) and len(definition) == 2:
                    response, delay = definition
                    self._signals[signal_name] = {"response": response, "delay": delay}
                else:
                    self._signals[signal_name] = {"response": definition, "delay": 0}

    def add_signal(self, signal_name: str, response: bytes, delay: float = 0):
        """
        添加信号定义

        Args:
            signal_name: 信号名称
            response: 响应数据
            delay: 响应延迟时间（秒），默认为0
        """
        self._signals[signal_name] = {"response": response, "delay": delay}

    def get_response(self, signal_name: str) -> tuple[bytes, float]:
        """
        获取信号的响应数据和延迟时间

        Args:
            signal_name: 信号名称

        Returns:
            tuple[bytes, float]: 响应数据和延迟时间组成的元组

        Raises:
            KeyError: 当信号不存在时抛出
        """
        if signal_name not in self._signals:
            raise KeyError(f"信号 '{signal_name}' 不存在于模板中")
        signal_info = self._signals[signal_name]
        return signal_info["response"], signal_info["delay"]

    def list_signals(self) -> list[str]:
        """
        列出所有已定义的信号名称

        Returns:
            list[str]: 信号名称列表
        """
        return list(self._signals.keys())


class Loadpoint:
    """
    挂载点类

    表示一个控制映射的挂载位置。
    """

    def __init__(self, name: str):
        """
        初始化挂载点

        Args:
            name: 挂载点名称
        """
        self._name = name
        self._control_mapping = {}

    @property
    def name(self) -> str:
        """
        获取挂载点名称

        Returns:
            str: 挂载点名称
        """
        return self._name

    @property
    def control_mapping(self) -> dict:
        """
        获取控制映射字典

        Returns:
            dict: 控制映射字典
        """
        return self._control_mapping


class SignalSimulator:
    """
    信号模拟器引擎类

    负责加载信号模板、管理挂载点和执行信号模拟。
    """

    def __init__(self):
        """
        初始化信号模拟器
        """
        self._template = None
        self._loadpoints = {}

    def load_template(self, template: SignalTemplate):
        """
        加载信号模板

        Args:
            template: SignalTemplate实例
        """
        self._template = template

    def simulate_signal(self, signal_name: str, input_data: bytes = None) -> bytes:
        """
        模拟信号并返回响应

        Args:
            signal_name: 信号名称
            input_data: 输入数据，默认为None

        Returns:
            bytes: 信号响应数据

        Raises:
            RuntimeError: 当未加载模板时抛出
            KeyError: 当信号不存在时抛出
        """
        if self._template is None:
            raise RuntimeError("未加载信号模板，请先调用 load_template 方法")
        response, delay = self._template.get_response(signal_name)
        return response

    def mount_loadpoint(self, loadpoint_name: str, control_mapping: dict):
        """
        将控制映射挂载到指定挂载点

        Args:
            loadpoint_name: 挂载点名称
            control_mapping: 控制映射字典
        """
        loadpoint = Loadpoint(loadpoint_name)
        loadpoint._control_mapping = control_mapping
        self._loadpoints[loadpoint_name] = loadpoint

    def unmount_loadpoint(self, loadpoint_name: str):
        """
        卸载指定挂载点

        Args:
            loadpoint_name: 挂载点名称

        Raises:
            KeyError: 当挂载点不存在时抛出
        """
        if loadpoint_name not in self._loadpoints:
            raise KeyError(f"挂载点 '{loadpoint_name}' 不存在")
        del self._loadpoints[loadpoint_name]

    def get_mounted_loadpoints(self) -> list[str]:
        """
        获取所有已挂载的挂载点名称列表

        Returns:
            list[str]: 挂载点名称列表
        """
        return list(self._loadpoints.keys())
