"""
通用工具模块

提供常用的工具函数和类。
"""

import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())


def generate_short_uuid() -> str:
    """生成短UUID（8位）"""
    return uuid.uuid4().hex[:8]


def compute_hash(data: Union[str, bytes, Dict[str, Any]], algorithm: str = "sha256") -> str:
    """
    计算数据的哈希值
    
    Args:
        data: 要计算的数据
        algorithm: 哈希算法 (md5, sha1, sha256, sha512)
        
    Returns:
        哈希值的十六进制字符串
    """
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    
    hash_func = getattr(hashlib, algorithm.lower())
    return hash_func(data).hexdigest()


def clean_text(text: str) -> str:
    """
    清理文本（移除多余空格、换行等）
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    # 移除首尾空格
    text = text.strip()
    return text


def extract_urls(text: str) -> List[str]:
    """
    从文本中提取URL
    
    Args:
        text: 包含URL的文本
        
    Returns:
        URL列表
    """
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.findall(text)


def extract_emails(text: str) -> List[str]:
    """
    从文本中提取邮箱地址
    
    Args:
        text: 包含邮箱的文本
        
    Returns:
        邮箱列表
    """
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    return email_pattern.findall(text)


def extract_phone_numbers(text: str) -> List[str]:
    """
    从文本中提取电话号码（中国手机号）
    
    Args:
        text: 包含电话号码的文本
        
    Returns:
        电话号码列表
    """
    phone_pattern = re.compile(r'1[3-9]\d{9}')
    return phone_pattern.findall(text)


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """
    时间戳转datetime
    
    Args:
        timestamp: 时间戳
        
    Returns:
        datetime对象
    """
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    datetime转时间戳
    
    Args:
        dt: datetime对象
        
    Returns:
        时间戳
    """
    return int(dt.timestamp())


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    确保目录存在，不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        Path对象
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    读取JSON文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        JSON数据字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(
    file_path: Union[str, Path],
    data: Dict[str, Any],
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    写入JSON文件
    
    Args:
        file_path: 文件路径
        data: 要写入的数据
        indent: 缩进
        ensure_ascii: 是否转义非ASCII字符
    """
    path = Path(file_path)
    ensure_dir(path.parent)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)


def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典
    
    Args:
        base: 基础字典
        update: 更新字典
        
    Returns:
        合并后的字典
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块
    
    Args:
        lst: 原始列表
        chunk_size: 块大小
        
    Returns:
        分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    展平嵌套字典
    
    Args:
        d: 嵌套字典
        parent_key: 父键名
        sep: 分隔符
        
    Returns:
        展平后的字典
    """
    items: List = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)