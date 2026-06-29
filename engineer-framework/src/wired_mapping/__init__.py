"""
wired_mapping 模块 - 线路映射模拟器

该模块提供线路连接脚本解析、XOR标签池管理和数据映射模拟功能。
"""

from typing import Optional


class WireScriptParser:
    """线路脚本解析器 - 解析线路连接脚本"""

    def __init__(self):
        """初始化线路脚本解析器"""
        self.script_data = {}
        self.connections = []
        self.xor_tags = {}

    def parse(self, script: str) -> dict:
        """
        解析线路脚本字符串为结构化数据

        Args:
            script: 线路脚本字符串

        Returns:
            dict: 包含 connections 和 xortags 的字典
        """
        self.connections = []
        self.xor_tags = {}
        self.script_data = {"connections": [], "xortags": {}}

        lines = script.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('XORTAG'):
                self._parse_xortag(line)
            elif line.startswith('CONNECT'):
                self._parse_connect(line)

        self.script_data["connections"] = self.connections
        self.script_data["xortags"] = self.xor_tags
        return self.script_data

    def parse_connection(self, line: str) -> dict:
        """
        解析单条连接行

        Args:
            line: 连接行字符串，格式: CONNECT node_a -> node_b MODE mode_name

        Returns:
            dict: 包含 from_node, to_node, mode 的字典
        """
        line = line.strip()
        if not line.startswith('CONNECT'):
            return {}

        parts = line.split()
        if len(parts) < 6:
            return {}

        from_node = parts[1]
        to_node = parts[3]
        mode = parts[5] if len(parts) > 5 else "direct"

        return {
            "from_node": from_node,
            "to_node": to_node,
            "mode": mode
        }

    def validate_script(self, script: str) -> bool:
        """
        验证脚本语法

        Args:
            script: 线路脚本字符串

        Returns:
            bool: 语法是否有效
        """
        lines = script.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('XORTAG'):
                if not self._validate_xortag(line):
                    return False
            elif line.startswith('CONNECT'):
                if not self._validate_connect(line):
                    return False
            else:
                return False

        return True

    def _parse_xortag(self, line: str) -> None:
        """解析 XORTAG 行"""
        try:
            content = line[6:].strip()
            if '=' in content:
                name, value = content.split('=')
                name = name.strip()
                value = value.strip()
                self.xor_tags[name] = bytes.fromhex(value)
        except (ValueError, IndexError):
            pass

    def _parse_connect(self, line: str) -> None:
        """解析 CONNECT 行"""
        conn = self.parse_connection(line)
        if conn:
            self.connections.append(conn)

    def _validate_xortag(self, line: str) -> bool:
        """验证 XORTAG 行语法"""
        try:
            content = line[6:].strip()
            if '=' not in content:
                return False
            name, value = content.split('=')
            if not name.strip() or not value.strip():
                return False
            bytes.fromhex(value.strip())
            return True
        except (ValueError, IndexError):
            return False

    def _validate_connect(self, line: str) -> bool:
        """验证 CONNECT 行语法"""
        try:
            parts = line.split()
            if len(parts) < 6:
                return False
            if parts[0] != 'CONNECT':
                return False
            if parts[2] != '->':
                return False
            if parts[4] != 'MODE':
                return False
            return True
        except IndexError:
            return False


class XORtagPool:
    """XOR标签池 - 处理 XOR 标签宏"""

    def __init__(self):
        """初始化 XOR 标签池"""
        self.tags = {}

    def define_tag(self, tag_name: str, value: bytes) -> None:
        """
        定义 XOR 标签

        Args:
            tag_name: 标签名称
            value: 标签值（字节数据）
        """
        self.tags[tag_name] = value

    def get_tag(self, tag_name: str) -> bytes:
        """
        获取标签值

        Args:
            tag_name: 标签名称

        Returns:
            bytes: 标签值，若不存在返回空字节
        """
        return self.tags.get(tag_name, b'')

    def apply_xor_tag(self, data: bytes, tag_name: str) -> bytes:
        """
        应用 XOR 标签到数据

        Args:
            data: 原始数据
            tag_name: 标签名称

        Returns:
            bytes: XOR 运算后的数据
        """
        tag = self.get_tag(tag_name)
        if not tag:
            return data

        tag_len = len(tag)
        result = bytearray(data)
        for i in range(len(data)):
            result[i] ^= tag[i % tag_len]
        return bytes(result)

    def list_tags(self) -> list[str]:
        """
        列出所有已定义的标签

        Returns:
            list[str]: 标签名称列表
        """
        return list(self.tags.keys())

    def remove_tag(self, tag_name: str) -> None:
        """
        移除标签

        Args:
            tag_name: 标签名称
        """
        if tag_name in self.tags:
            del self.tags[tag_name]


class MappingSimulator:
    """映射模拟器 - 主要的映射模拟类"""

    def __init__(self):
        """初始化映射模拟器"""
        self.parser = WireScriptParser()
        self.xor_pool = XORtagPool()
        self.connections = {}
        self.current_script = ""

    def load_script(self, script: str) -> bool:
        """
        加载并解析线路脚本

        Args:
            script: 线路脚本字符串

        Returns:
            bool: 加载是否成功
        """
        if not self.parser.validate_script(script):
            return False

        self.current_script = script
        parsed = self.parser.parse(script)

        for tag_name, tag_value in parsed.get("xortags", {}).items():
            self.xor_pool.define_tag(tag_name, tag_value)

        for conn in parsed.get("connections", []):
            self.connect_nodes(
                conn["from_node"],
                conn["to_node"],
                conn.get("mode", "direct")
            )

        return True

    def execute_connection(self, from_node: str, to_node: str, data: bytes) -> bytes:
        """
        执行节点间的数据传输

        Args:
            from_node: 源节点名称
            to_node: 目标节点名称
            data: 传输的数据

        Returns:
            bytes: 处理后的数据
        """
        conn_key = self._make_key(from_node, to_node)
        if conn_key not in self.connections:
            return data

        mode = self.connections[conn_key]["mode"]
        return self.apply_mode(mode, data)

    def apply_mode(self, mode: str, data: bytes) -> bytes:
        """
        应用模式到数据

        Args:
            mode: 模式名称 (template, mapping, script)
            data: 原始数据

        Returns:
            bytes: 处理后的数据
        """
        if mode == "template":
            return self._apply_template_mode(data)
        elif mode == "mapping":
            return self._apply_mapping_mode(data)
        elif mode == "script":
            return self._apply_script_mode(data)
        else:
            return data

    def connect_nodes(self, node_a: str, node_b: str, mode: str = "direct") -> None:
        """
        建立节点间的连接

        Args:
            node_a: 节点A名称
            node_b: 节点B名称
            mode: 连接模式 (direct, template, mapping, script)
        """
        key = self._make_key(node_a, node_b)
        self.connections[key] = {
            "node_a": node_a,
            "node_b": node_b,
            "mode": mode,
            "active": True
        }

    def disconnect_nodes(self, node_a: str, node_b: str) -> None:
        """
        断开节点间的连接

        Args:
            node_a: 节点A名称
            node_b: 节点B名称
        """
        key = self._make_key(node_a, node_b)
        if key in self.connections:
            self.connections[key]["active"] = False

    def get_connection_status(self, node_a: str, node_b: str) -> dict:
        """
        获取连接状态

        Args:
            node_a: 节点A名称
            node_b: 节点B名称

        Returns:
            dict: 包含连接信息的字典
        """
        key = self._make_key(node_a, node_b)
        if key not in self.connections:
            return {"connected": False}

        conn = self.connections[key]
        return {
            "connected": conn["active"],
            "mode": conn["mode"],
            "node_a": conn["node_a"],
            "node_b": conn["node_b"]
        }

    def _make_key(self, node_a: str, node_b: str) -> str:
        """生成连接键"""
        return f"{node_a}->{node_b}"

    def _apply_template_mode(self, data: bytes) -> bytes:
        """应用模板模式"""
        return data

    def _apply_mapping_mode(self, data: bytes) -> bytes:
        """应用映射模式"""
        return data

    def _apply_script_mode(self, data: bytes) -> bytes:
        """应用脚本模式"""
        return data
