"""
哈希计算模块

提供多种哈希算法的实现。
"""

import hashlib
from typing import Optional, Union

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class HashCalculator:
    """
    哈希计算器
    
    支持多种哈希算法。
    """
    
    SUPPORTED_ALGORITHMS = ["md5", "sha1", "sha256", "sha512", "sha3_256", "sha3_512"]
    
    def __init__(self, algorithm: str = "sha256"):
        """
        初始化哈希计算器
        
        Args:
            algorithm: 哈希算法名称
        """
        algorithm_lower = algorithm.lower()
        if algorithm_lower not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {algorithm}. Supported: {self.SUPPORTED_ALGORITHMS}")
        self.algorithm = algorithm_lower
    
    def calculate(self, data: Union[str, bytes]) -> str:
        """
        计算哈希值
        
        Args:
            data: 输入数据
            
        Returns:
            哈希值的十六进制字符串
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        hash_func = hashlib.new(self.algorithm)
        hash_func.update(data)
        return hash_func.hexdigest()
    
    def calculate_file(self, filepath: Union[str, "os.PathLike"], chunk_size: int = 8192) -> str:
        """
        计算文件的哈希值
        
        Args:
            filepath: 文件路径
            chunk_size: 分块大小
            
        Returns:
            哈希值的十六进制字符串
        """
        import os

        filepath = os.PathLike(filepath) if isinstance(filepath, str) else filepath
        
        hash_func = hashlib.new(self.algorithm)
        
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                hash_func.update(chunk)
        
        logger.info(f"计算了文件哈希: {filepath}")
        return hash_func.hexdigest()
    
    def verify(self, data: Union[str, bytes], expected_hash: str) -> bool:
        """
        验证哈希值
        
        Args:
            data: 输入数据
            expected_hash: 预期的哈希值
            
        Returns:
            是否匹配
        """
        calculated_hash = self.calculate(data)
        return calculated_hash == expected_hash.lower()
    
    def verify_file(self, filepath: Union[str, "os.PathLike"], expected_hash: str) -> bool:
        """
        验证文件的哈希值
        
        Args:
            filepath: 文件路径
            expected_hash: 预期的哈希值
            
        Returns:
            是否匹配
        """
        calculated_hash = self.calculate_file(filepath)
        return calculated_hash == expected_hash.lower()