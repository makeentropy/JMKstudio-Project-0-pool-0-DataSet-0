"""
存储后端模块

提供多种存储后端的抽象基类和具体实现，包括本地存储、网络存储(NFS/SMB)、对象存储(S3/MinIO)等。
"""

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class StorageBackendType(Enum):
    """存储后端类型枚举"""
    LOCAL = "local"
    NFS = "nfs"
    SMB = "smb"
    S3 = "s3"
    MINIO = "minio"
    FTP = "ftp"


@dataclass
class StorageInfo:
    """存储信息数据类"""
    total_size: int  # 总容量（字节）
    used_size: int  # 已使用容量（字节）
    available_size: int  # 可用容量（字节）
    usage_percent: float  # 使用百分比
    file_count: int  # 文件数量
    directory_count: int  # 目录数量


@dataclass
class StorageBackendConfig:
    """存储后端配置"""
    backend_type: StorageBackendType
    name: str
    root_path: str
    max_size: Optional[int] = None  # 最大容量限制（字节）
    read_only: bool = False
    priority: int = 0  # 优先级，用于分配策略
    tags: Optional[Dict[str, str]] = None  # 标签，用于分类和筛选

    # 网络存储配置
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    share_name: Optional[str] = None  # SMB共享名
    bucket: Optional[str] = None  # S3/MinIO bucket名
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    secure: bool = False  # 是否使用HTTPS
    region: Optional[str] = None


class StorageBackend(ABC):
    """
    存储后端抽象基类
    
    定义了所有存储后端必须实现的接口。
    """
    
    def __init__(self, config: StorageBackendConfig):
        """
        初始化存储后端
        
        Args:
            config: 存储后端配置
        """
        self.config = config
        self._connected = False
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        连接到存储后端
        
        Returns:
            连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开与存储后端的连接
        
        Returns:
            断开是否成功
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查是否已连接
        
        Returns:
            是否已连接
        """
        pass
    
    @abstractmethod
    def write(self, path: str, data: Union[bytes, str], overwrite: bool = False) -> bool:
        """
        写入数据到存储
        
        Args:
            path: 相对路径
            data: 要写入的数据
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            写入是否成功
        """
        pass
    
    @abstractmethod
    def read(self, path: str) -> Optional[bytes]:
        """
        从存储读取数据
        
        Args:
            path: 相对路径
            
        Returns:
            读取的数据，如果文件不存在返回None
        """
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """
        删除文件
        
        Args:
            path: 相对路径
            
        Returns:
            删除是否成功
        """
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            path: 相对路径
            
        Returns:
            文件是否存在
        """
        pass
    
    @abstractmethod
    def list_files(self, path: str = "", recursive: bool = False) -> List[str]:
        """
        列出文件
        
        Args:
            path: 相对路径
            recursive: 是否递归列出
            
        Returns:
            文件路径列表
        """
        pass
    
    @abstractmethod
    def list_directories(self, path: str = "") -> List[str]:
        """
        列出目录
        
        Args:
            path: 相对路径
            
        Returns:
            目录路径列表
        """
        pass
    
    @abstractmethod
    def create_directory(self, path: str) -> bool:
        """
        创建目录
        
        Args:
            path: 相对路径
            
        Returns:
            创建是否成功
        """
        pass
    
    @abstractmethod
    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """
        删除目录
        
        Args:
            path: 相对路径
            recursive: 是否递归删除
            
        Returns:
            删除是否成功
        """
        pass
    
    @abstractmethod
    def get_info(self) -> StorageInfo:
        """
        获取存储信息
        
        Returns:
            存储信息
        """
        pass
    
    @abstractmethod
    def get_file_size(self, path: str) -> Optional[int]:
        """
        获取文件大小
        
        Args:
            path: 相对路径
            
        Returns:
            文件大小（字节），如果文件不存在返回None
        """
        pass
    
    @abstractmethod
    def get_file_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件元数据
        
        Args:
            path: 相对路径
            
        Returns:
            文件元数据字典，如果文件不存在返回None
        """
        pass
    
    @abstractmethod
    def copy(self, src: str, dst: str) -> bool:
        """
        复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            复制是否成功
        """
        pass
    
    @abstractmethod
    def move(self, src: str, dst: str) -> bool:
        """
        移动文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            移动是否成功
        """
        pass
    
    def get_absolute_path(self, path: str) -> str:
        """
        获取绝对路径
        
        Args:
            path: 相对路径
            
        Returns:
            绝对路径
        """
        return str(Path(self.config.root_path) / path)
    
    def get_available_space(self) -> int:
        """
        获取可用空间
        
        Returns:
            可用空间（字节）
        """
        info = self.get_info()
        return info.available_size
    
    def can_write(self, size: int) -> bool:
        """
        检查是否可以写入指定大小的数据
        
        Args:
            size: 数据大小（字节）
            
        Returns:
            是否可以写入
        """
        if self.config.read_only:
            return False
        return self.get_available_space() >= size


class LocalStorageBackend(StorageBackend):
    """
    本地存储后端
    
    使用本地文件系统作为存储后端。
    """
    
    def __init__(self, config: StorageBackendConfig):
        """
        初始化本地存储后端
        
        Args:
            config: 存储后端配置
        """
        super().__init__(config)
        self._root_path = Path(config.root_path).resolve()
    
    def connect(self) -> bool:
        """连接到本地存储（确保目录存在）"""
        try:
            if not self._root_path.exists():
                self._root_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"创建存储目录: {self._root_path}")
            self._connected = True
            self.logger.info(f"已连接到本地存储: {self._root_path}")
            return True
        except Exception as e:
            self.logger.error(f"连接本地存储失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开连接"""
        self._connected = False
        self.logger.info(f"已断开本地存储连接: {self._root_path}")
        return True
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._root_path.exists()
    
    def write(self, path: str, data: Union[bytes, str], overwrite: bool = False) -> bool:
        """写入数据到本地文件系统"""
        if not self.is_connected():
            self.logger.error("存储未连接")
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            full_path = self._root_path / path
            
            if full_path.exists() and not overwrite:
                self.logger.warning(f"文件已存在: {path}")
                return False
            
            # 确保父目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入数据
            mode = "wb" if isinstance(data, bytes) else "w"
            encoding = None if isinstance(data, bytes) else "utf-8"
            with open(full_path, mode, encoding=encoding) as f:
                f.write(data)
            
            self.logger.debug(f"写入文件成功: {path}")
            return True
        except Exception as e:
            self.logger.error(f"写入文件失败 {path}: {e}")
            return False
    
    def read(self, path: str) -> Optional[bytes]:
        """从本地文件系统读取数据"""
        if not self.is_connected():
            self.logger.error("存储未连接")
            return None
        
        try:
            full_path = self._root_path / path
            
            if not full_path.exists():
                self.logger.debug(f"文件不存在: {path}")
                return None
            
            with open(full_path, "rb") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"读取文件失败 {path}: {e}")
            return None
    
    def delete(self, path: str) -> bool:
        """删除本地文件"""
        if not self.is_connected():
            self.logger.error("存储未连接")
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            full_path = self._root_path / path
            
            if not full_path.exists():
                self.logger.warning(f"文件不存在: {path}")
                return False
            
            full_path.unlink()
            self.logger.debug(f"删除文件成功: {path}")
            return True
        except Exception as e:
            self.logger.error(f"删除文件失败 {path}: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        if not self.is_connected():
            return False
        return (self._root_path / path).exists()
    
    def list_files(self, path: str = "", recursive: bool = False) -> List[str]:
        """列出文件"""
        if not self.is_connected():
            return []
        
        try:
            full_path = self._root_path / path
            if not full_path.exists():
                return []
            
            files = []
            if recursive:
                for item in full_path.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(self._root_path)
                        files.append(str(rel_path))
            else:
                for item in full_path.iterdir():
                    if item.is_file():
                        files.append(str(item.relative_to(self._root_path)))
            
            return files
        except Exception as e:
            self.logger.error(f"列出文件失败 {path}: {e}")
            return []
    
    def list_directories(self, path: str = "") -> List[str]:
        """列出目录"""
        if not self.is_connected():
            return []
        
        try:
            full_path = self._root_path / path
            if not full_path.exists():
                return []
            
            dirs = []
            for item in full_path.iterdir():
                if item.is_dir():
                    dirs.append(str(item.relative_to(self._root_path)))
            
            return dirs
        except Exception as e:
            self.logger.error(f"列出目录失败 {path}: {e}")
            return []
    
    def create_directory(self, path: str) -> bool:
        """创建目录"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            full_path = self._root_path / path
            full_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"创建目录失败 {path}: {e}")
            return False
    
    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """删除目录"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            full_path = self._root_path / path
            
            if not full_path.exists():
                return False
            
            if recursive:
                shutil.rmtree(full_path)
            else:
                full_path.rmdir()
            
            return True
        except Exception as e:
            self.logger.error(f"删除目录失败 {path}: {e}")
            return False
    
    def get_info(self) -> StorageInfo:
        """获取存储信息"""
        if not self.is_connected():
            return StorageInfo(0, 0, 0, 0.0, 0, 0)
        
        try:
            stat = shutil.disk_usage(self._root_path)
            
            # 统计文件和目录数量
            file_count = 0
            dir_count = 0
            used_size = 0
            
            for item in self._root_path.rglob("*"):
                if item.is_file():
                    file_count += 1
                    try:
                        used_size += item.stat().st_size
                    except:
                        pass
                elif item.is_dir():
                    dir_count += 1
            
            # 应用容量限制
            if self.config.max_size:
                available = min(stat.free, self.config.max_size - used_size)
            else:
                available = stat.free
            
            usage_percent = (used_size / stat.total * 100) if stat.total > 0 else 0.0
            
            return StorageInfo(
                total_size=stat.total,
                used_size=used_size,
                available_size=max(0, available),
                usage_percent=usage_percent,
                file_count=file_count,
                directory_count=dir_count
            )
        except Exception as e:
            self.logger.error(f"获取存储信息失败: {e}")
            return StorageInfo(0, 0, 0, 0.0, 0, 0)
    
    def get_file_size(self, path: str) -> Optional[int]:
        """获取文件大小"""
        if not self.is_connected():
            return None
        
        try:
            full_path = self._root_path / path
            if not full_path.exists():
                return None
            return full_path.stat().st_size
        except Exception as e:
            self.logger.error(f"获取文件大小失败 {path}: {e}")
            return None
    
    def get_file_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """获取文件元数据"""
        if not self.is_connected():
            return None
        
        try:
            full_path = self._root_path / path
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            return {
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "accessed_at": stat.st_atime,
                "is_file": full_path.is_file(),
                "is_directory": full_path.is_dir(),
                "path": str(full_path),
                "relative_path": path,
            }
        except Exception as e:
            self.logger.error(f"获取文件元数据失败 {path}: {e}")
            return None
    
    def copy(self, src: str, dst: str) -> bool:
        """复制文件"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            src_path = self._root_path / src
            dst_path = self._root_path / dst
            
            if not src_path.exists():
                self.logger.error(f"源文件不存在: {src}")
                return False
            
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            
            return True
        except Exception as e:
            self.logger.error(f"复制文件失败 {src} -> {dst}: {e}")
            return False
    
    def move(self, src: str, dst: str) -> bool:
        """移动文件"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            src_path = self._root_path / src
            dst_path = self._root_path / dst
            
            if not src_path.exists():
                self.logger.error(f"源文件不存在: {src}")
                return False
            
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            
            return True
        except Exception as e:
            self.logger.error(f"移动文件失败 {src} -> {dst}: {e}")
            return False


class S3StorageBackend(StorageBackend):
    """
    S3/MinIO对象存储后端
    
    使用S3兼容的对象存储服务作为存储后端。
    """
    
    def __init__(self, config: StorageBackendConfig):
        """
        初始化S3存储后端
        
        Args:
            config: 存储后端配置
        """
        super().__init__(config)
        self._client = None
        self._bucket = config.bucket
    
    def connect(self) -> bool:
        """连接到S3/MinIO"""
        try:
            import boto3
            from botocore.config import Config
            
            # 构建endpoint_url
            endpoint_url = None
            if self.config.backend_type == StorageBackendType.MINIO:
                if self.config.host:
                    protocol = "https" if self.config.secure else "http"
                    port = self.config.port or 9000
                    endpoint_url = f"{protocol}://{self.config.host}:{port}"
            
            # 创建S3客户端
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                region_name=self.config.region or "us-east-1",
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"}
                )
            )
            
            # 确保bucket存在
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except:
                if not self.config.read_only:
                    self._client.create_bucket(Bucket=self._bucket)
                    self.logger.info(f"创建bucket: {self._bucket}")
            
            self._connected = True
            self.logger.info(f"已连接到对象存储: {self._bucket}")
            return True
        except Exception as e:
            self.logger.error(f"连接对象存储失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开连接"""
        self._client = None
        self._connected = False
        self.logger.info(f"已断开对象存储连接: {self._bucket}")
        return True
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._client is not None
    
    def write(self, path: str, data: Union[bytes, str], overwrite: bool = False) -> bool:
        """写入数据到对象存储"""
        if not self.is_connected():
            self.logger.error("存储未连接")
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            # 检查文件是否存在
            if not overwrite and self.exists(path):
                self.logger.warning(f"文件已存在: {path}")
                return False
            
            # 转换数据类型
            if isinstance(data, str):
                data = data.encode("utf-8")
            
            self._client.put_object(Bucket=self._bucket, Key=path, Body=data)
            self.logger.debug(f"写入对象成功: {path}")
            return True
        except Exception as e:
            self.logger.error(f"写入对象失败 {path}: {e}")
            return False
    
    def read(self, path: str) -> Optional[bytes]:
        """从对象存储读取数据"""
        if not self.is_connected():
            self.logger.error("存储未连接")
            return None
        
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=path)
            return response["Body"].read()
        except self._client.exceptions.NoSuchKey:
            self.logger.debug(f"对象不存在: {path}")
            return None
        except Exception as e:
            self.logger.error(f"读取对象失败 {path}: {e}")
            return None
    
    def delete(self, path: str) -> bool:
        """删除对象"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            self.logger.error("存储为只读模式")
            return False
        
        try:
            self._client.delete_object(Bucket=self._bucket, Key=path)
            return True
        except Exception as e:
            self.logger.error(f"删除对象失败 {path}: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        """检查对象是否存在"""
        if not self.is_connected():
            return False
        
        try:
            self._client.head_object(Bucket=self._bucket, Key=path)
            return True
        except:
            return False
    
    def list_files(self, path: str = "", recursive: bool = False) -> List[str]:
        """列出对象"""
        if not self.is_connected():
            return []
        
        try:
            files = []
            prefix = path.rstrip("/") + "/" if path else ""
            
            paginator = self._client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self._bucket, Prefix=prefix)
            
            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not recursive and "/" in key[len(prefix):]:
                        continue
                    files.append(key)
            
            return files
        except Exception as e:
            self.logger.error(f"列出对象失败 {path}: {e}")
            return []
    
    def list_directories(self, path: str = "") -> List[str]:
        """列出目录（前缀）"""
        if not self.is_connected():
            return []
        
        try:
            dirs = set()
            prefix = path.rstrip("/") + "/" if path else ""
            
            paginator = self._client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self._bucket, Prefix=prefix, Delimiter="/")
            
            for page in pages:
                for prefix_obj in page.get("CommonPrefixes", []):
                    dirs.add(prefix_obj["Prefix"].rstrip("/"))
            
            return list(dirs)
        except Exception as e:
            self.logger.error(f"列出目录失败 {path}: {e}")
            return []
    
    def create_directory(self, path: str) -> bool:
        """创建目录（在S3中只需创建一个以/结尾的空对象）"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            return False
        
        try:
            dir_path = path.rstrip("/") + "/"
            self._client.put_object(Bucket=self._bucket, Key=dir_path, Body=b"")
            return True
        except Exception as e:
            self.logger.error(f"创建目录失败 {path}: {e}")
            return False
    
    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """删除目录"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            return False
        
        try:
            dir_path = path.rstrip("/") + "/"
            
            if recursive:
                # 删除所有以该前缀开头的对象
                objects = self.list_files(path, recursive=True)
                for obj in objects:
                    self._client.delete_object(Bucket=self._bucket, Key=obj)
            else:
                # 只删除目录标记对象
                self._client.delete_object(Bucket=self._bucket, Key=dir_path)
            
            return True
        except Exception as e:
            self.logger.error(f"删除目录失败 {path}: {e}")
            return False
    
    def get_info(self) -> StorageInfo:
        """获取存储信息"""
        if not self.is_connected():
            return StorageInfo(0, 0, 0, 0.0, 0, 0)
        
        try:
            # 统计对象数量和大小
            file_count = 0
            total_size = 0
            
            paginator = self._client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self._bucket)
            
            for page in pages:
                for obj in page.get("Contents", []):
                    if not obj["Key"].endswith("/"):
                        file_count += 1
                        total_size += obj["Size"]
            
            # S3通常没有容量限制，使用配置的限制
            if self.config.max_size:
                available = self.config.max_size - total_size
                total = self.config.max_size
            else:
                # 默认认为有无限空间
                available = 1e18  # 1 EB
                total = 1e18
            
            usage_percent = (total_size / total * 100) if total > 0 else 0.0
            
            return StorageInfo(
                total_size=int(total),
                used_size=total_size,
                available_size=int(max(0, available)),
                usage_percent=usage_percent,
                file_count=file_count,
                directory_count=0  # S3没有真正的目录概念
            )
        except Exception as e:
            self.logger.error(f"获取存储信息失败: {e}")
            return StorageInfo(0, 0, 0, 0.0, 0, 0)
    
    def get_file_size(self, path: str) -> Optional[int]:
        """获取对象大小"""
        if not self.is_connected():
            return None
        
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=path)
            return response["ContentLength"]
        except:
            return None
    
    def get_file_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """获取对象元数据"""
        if not self.is_connected():
            return None
        
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=path)
            return {
                "size": response["ContentLength"],
                "modified_at": response["LastModified"].timestamp(),
                "etag": response.get("ETag", ""),
                "content_type": response.get("ContentType", ""),
                "metadata": response.get("Metadata", {}),
                "path": path,
            }
        except:
            return None
    
    def copy(self, src: str, dst: str) -> bool:
        """复制对象"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            return False
        
        try:
            from botocore.exceptions import ClientError
            
            copy_source = {"Bucket": self._bucket, "Key": src}
            self._client.copy_object(Bucket=self._bucket, CopySource=copy_source, Key=dst)
            return True
        except Exception as e:
            self.logger.error(f"复制对象失败 {src} -> {dst}: {e}")
            return False
    
    def move(self, src: str, dst: str) -> bool:
        """移动对象"""
        if not self.is_connected():
            return False
        
        if self.config.read_only:
            return False
        
        try:
            if self.copy(src, dst):
                return self.delete(src)
            return False
        except Exception as e:
            self.logger.error(f"移动对象失败 {src} -> {dst}: {e}")
            return False