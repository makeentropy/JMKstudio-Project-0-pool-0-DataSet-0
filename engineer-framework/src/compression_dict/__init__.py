"""压缩字典模块 - 使用字典进行数据压缩和解压缩"""


class CompressionDict:
    """基于字典的数据压缩类，使用最长匹配策略进行压缩和解压缩。
    
    压缩算法说明：
    - 压缩时，对输入数据的每个位置，查找字典中最长的匹配键，并输出该键
    - 解压缩时，根据键查找对应的值，还原原始数据
    
    Attributes:
        _dict: 内部存储的字典映射，键为压缩键，值为原始字符串
    """
    
    def __init__(self, dictionary: dict[str, str] = None):
        """初始化压缩字典。
        
        Args:
            dictionary: 可选的初始字典，键为压缩键，值为原始字符串
        """
        self._dict: dict[str, str] = {}
        if dictionary is not None:
            self.load_dict(dictionary)
    
    def load_dict(self, dictionary: dict[str, str]) -> None:
        """加载字典映射。
        
        Args:
            dictionary: 字典映射，键为压缩键，值为原始字符串
            
        Raises:
            TypeError: 当dictionary不是字典类型时抛出
            ValueError: 当字典为空或键值为空字符串时抛出
        """
        if not isinstance(dictionary, dict):
            raise TypeError(f"dictionary必须是字典类型，而不是 {type(dictionary).__name__}")
        
        for key, value in dictionary.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TypeError("字典的键和值都必须是字符串类型")
            if not key:
                raise ValueError("字典键不能为空字符串")
        
        if not dictionary:
            raise ValueError("字典不能为空")
        
        self._dict = dictionary.copy()
    
    def add_entry(self, key: str, value: str) -> None:
        """添加单个字典条目。
        
        Args:
            key: 压缩键，不能为空字符串
            value: 原始字符串值
            
        Raises:
            TypeError: 当key或value不是字符串类型时抛出
            ValueError: 当key为空字符串时抛出
        """
        if not isinstance(key, str):
            raise TypeError(f"key必须是字符串类型，而不是 {type(key).__name__}")
        if not isinstance(value, str):
            raise TypeError(f"value必须是字符串类型，而不是 {type(value).__name__}")
        if not key:
            raise ValueError("压缩键不能为空字符串")
        
        self._dict[key] = value
    
    def compress(self, data: str) -> list[str]:
        """压缩字符串数据。
        
        使用贪婪匹配策略，对输入数据的每个位置，查找字典中最长的匹配键。
        
        Args:
            data: 要压缩的字符串
            
        Returns:
            压缩后的键列表
            
        Raises:
            TypeError: 当data不是字符串类型时抛出
            ValueError: 当data为空或无法压缩时抛出
        """
        if not isinstance(data, str):
            raise TypeError(f"data必须是字符串类型，而不是 {type(data).__name__}")
        
        if not data:
            raise ValueError("待压缩数据不能为空")
        
        if not self._dict:
            raise ValueError("字典为空，无法进行压缩")
        
        result = []
        i = 0
        
        while i < len(data):
            # 查找从当前位置开始的最长匹配
            longest_match = None
            longest_key = None
            
            # 从最长可能匹配开始尝试
            for key_len in range(len(data) - i, 0, -1):
                substr = data[i:i + key_len]
                if substr in self._dict:
                    longest_match = substr
                    longest_key = substr
                    break
            
            # 如果没有找到任何匹配，使用单个字符
            if longest_match is None:
                # 尝试直接匹配单个字符
                if data[i] in self._dict:
                    result.append(data[i])
                else:
                    raise ValueError(f"无法压缩字符 '{data[i]}'，字典中没有对应的键")
                i += 1
            else:
                result.append(longest_key)
                i += len(longest_match)
        
        return result
    
    def decompress(self, compressed: list[str]) -> str:
        """解压缩数据。
        
        根据压缩后的键列表，通过查字典还原原始字符串。
        
        Args:
            compressed: 压缩后的键列表
            
        Returns:
            解压缩后的原始字符串
            
        Raises:
            TypeError: 当compressed不是列表类型时抛出
            ValueError: 当compressed为空或包含无效键时抛出
        """
        if not isinstance(compressed, list):
            raise TypeError(f"compressed必须是列表类型，而不是 {type(compressed).__name__}")
        
        if not compressed:
            raise ValueError("待解压缩数据不能为空")
        
        result_parts = []
        
        for key in compressed:
            if not isinstance(key, str):
                raise TypeError(f"压缩列表中的每个元素必须是字符串类型，而不是 {type(key).__name__}")
            if key not in self._dict:
                raise ValueError(f"解压缩失败：键 '{key}' 不在字典中")
            result_parts.append(self._dict[key])
        
        return ''.join(result_parts)
    
    def get_dict(self) -> dict[str, str]:
        """获取当前字典的副本。
        
        Returns:
            当前字典的浅拷贝
        """
        return self._dict.copy()
