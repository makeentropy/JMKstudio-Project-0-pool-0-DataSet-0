"""
容器快照管理模块

提供Docker容器镜像导出/导入、容器状态快照、容器生命周期管理等功能。
"""

import hashlib
import os
import tarfile
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import docker
from docker import DockerClient
from docker.errors import APIError, NotFound
from pydantic import BaseModel, ConfigDict, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ContainerConfig(BaseModel):
    """
    Docker容器配置

    定义Docker守护进程连接所需的参数。
    """

    base_url: str = Field(default="unix:///var/run/docker.sock", description="Docker守护进程URL")
    timeout: int = Field(default=60, description="连接超时时间（秒）")
    tls: bool = Field(default=False, description="是否使用TLS连接")
    tls_ca_cert: Optional[str] = Field(default=None, description="TLS CA证书路径")
    tls_cert: Optional[str] = Field(default=None, description="TLS证书路径")
    tls_key: Optional[str] = Field(default=None, description="TLS密钥路径")
    max_pool_size: int = Field(default=10, description="连接池最大连接数")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ContainerStatus(str, Enum):
    """容器状态"""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"


class SnapshotStatus(str, Enum):
    """快照状态"""

    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"
    DELETED = "deleted"


class ContainerSnapshot(BaseModel):
    """
    容器快照数据类

    存储容器状态快照的完整信息。
    """

    snapshot_id: str = Field(..., description="快照ID")
    name: str = Field(..., description="快照名称")
    description: str = Field(default="", description="快照描述")
    
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    size: int = Field(default=0, description="快照大小（字节）")
    
    container_id: str = Field(..., description="关联的容器ID")
    container_name: str = Field(default="", description="容器名称")
    container_status: str = Field(default="", description="容器状态")
    
    image_id: str = Field(default="", description="镜像ID")
    image_name: str = Field(default="", description="镜像名称")
    image_tag: str = Field(default="", description="镜像标签")
    
    status: SnapshotStatus = Field(default=SnapshotStatus.COMPLETED, description="快照状态")
    snapshot_path: Path = Field(default=Path(""), description="快照文件路径")
    checksum: str = Field(default="", description="快照校验和")
    
    labels: Dict[str, str] = Field(default_factory=dict, description="标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ContainerManager:
    """
    容器管理器

    提供Docker容器镜像导出/导入、容器状态快照、容器生命周期管理等功能。
    """

    def __init__(self, config: Optional[ContainerConfig] = None):
        """
        初始化容器管理器

        Args:
            config: Docker配置，如果未提供则使用默认配置
        """
        self.config = config or ContainerConfig()
        self._client: Optional[DockerClient] = None

    @property
    def client(self) -> DockerClient:
        """获取Docker客户端"""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> DockerClient:
        """创建Docker客户端连接"""
        try:
            kwargs: Dict[str, Any] = {
                "base_url": self.config.base_url,
                "timeout": self.config.timeout,
            }

            if self.config.tls:
                kwargs["tls"] = docker.tls.TLSConfig(
                    ca_cert=self.config.tls_ca_cert,
                    cert=self.config.tls_cert,
                    key=self.config.tls_key,
                )

            client = docker.from_env(**kwargs)
            client.ping()
            logger.info(f"Docker客户端连接成功: {self.config.base_url}")
            return client

        except APIError as e:
            logger.error(f"Docker客户端连接失败: {str(e)}")
            raise RuntimeError(f"Docker客户端连接失败: {str(e)}")
        except Exception as e:
            logger.error(f"Docker客户端创建异常: {str(e)}")
            raise RuntimeError(f"Docker客户端创建异常: {str(e)}")

    def close(self) -> None:
        """关闭Docker客户端连接"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Docker客户端已关闭")

    def save_image(
        self,
        image_name: str,
        output_path: Union[str, Path],
        compression: Optional[str] = None,
    ) -> Path:
        """
        导出容器镜像为tar文件

        Args:
            image_name: 镜像名称（可包含标签）
            output_path: 输出文件路径
            compression: 压缩类型（gz, bz2, xz）

        Returns:
            输出文件的绝对路径

        Raises:
            RuntimeError: 导出失败
        """
        output_path = Path(output_path).resolve()

        try:
            logger.info(f"开始导出镜像: {image_name} -> {output_path}")

            with self.client.images.get(image_name) as image:
                with open(output_path, "wb") as f:
                    for chunk in image.save(chunk_size=2097152):
                        f.write(chunk)

            if compression:
                compressed_path = self._compress_tar(output_path, compression)
                output_path.unlink()
                output_path = compressed_path

            file_size = output_path.stat().st_size
            logger.info(f"镜像导出成功: {image_name}, 大小: {file_size} 字节")

            return output_path

        except NotFound:
            raise RuntimeError(f"镜像不存在: {image_name}")
        except APIError as e:
            logger.error(f"镜像导出失败: {str(e)}")
            raise RuntimeError(f"镜像导出失败: {str(e)}")
        except Exception as e:
            logger.error(f"镜像导出发生未知错误: {str(e)}")
            raise RuntimeError(f"镜像导出失败: {str(e)}")

    def load_image(self, tar_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        从tar文件导入容器镜像

        Args:
            tar_path: tar文件路径

        Returns:
            导入的镜像信息列表

        Raises:
            RuntimeError: 导入失败
        """
        tar_path = Path(tar_path).resolve()

        if not tar_path.exists():
            raise FileNotFoundError(f"tar文件不存在: {tar_path}")

        try:
            logger.info(f"开始导入镜像: {tar_path}")

            tar_file = self._decompress_tar(tar_path)
            images = []

            with open(tar_file, "rb") as f:
                for line in self.client.images.load(f):
                    images.append(line)

            if tar_file != tar_path:
                tar_file.unlink()

            logger.info(f"镜像导入成功，共导入 {len(images)} 个镜像")

            return images

        except APIError as e:
            logger.error(f"镜像导入失败: {str(e)}")
            raise RuntimeError(f"镜像导入失败: {str(e)}")
        except Exception as e:
            logger.error(f"镜像导入发生未知错误: {str(e)}")
            raise RuntimeError(f"镜像导入失败: {str(e)}")

    def create_container_snapshot(
        self,
        container_id: str,
        snapshot_name: str,
        description: str = "",
        output_dir: Optional[Union[str, Path]] = None,
    ) -> ContainerSnapshot:
        """
        创建容器状态快照

        Args:
            container_id: 容器ID或名称
            snapshot_name: 快照名称
            description: 快照描述
            output_dir: 输出目录，默认为当前目录

        Returns:
            容器快照对象

        Raises:
            RuntimeError: 创建快照失败
        """
        output_dir = Path(output_dir or ".").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            container = self.client.containers.get(container_id)
            container_info = container.attrs

            snapshot_id = self._generate_snapshot_id(container_id)

            snapshot = ContainerSnapshot(
                snapshot_id=snapshot_id,
                name=snapshot_name,
                description=description,
                container_id=container.id,
                container_name=container.name,
                container_status=container.status,
                image_id=container_info.get("Image", ""),
                image_name=self._get_image_name(container_info),
                image_tag=self._get_image_tag(container_info),
                status=SnapshotStatus.CREATING,
                labels=container.labels,
            )

            image_name = snapshot.image_name or container_info.get("Config", {}).get("Image", "")
            
            snapshot_path = output_dir / f"{snapshot_id}.tar"
            self.save_image(image_name, snapshot_path)

            snapshot.snapshot_path = snapshot_path
            snapshot.size = snapshot_path.stat().st_size
            snapshot.checksum = self._calculate_checksum(snapshot_path)
            snapshot.status = SnapshotStatus.COMPLETED

            logger.info(f"容器快照创建成功: {container_id} -> {snapshot_id}")

            return snapshot

        except NotFound:
            raise RuntimeError(f"容器不存在: {container_id}")
        except APIError as e:
            logger.error(f"创建容器快照失败: {str(e)}")
            raise RuntimeError(f"创建容器快照失败: {str(e)}")
        except Exception as e:
            logger.error(f"创建容器快照发生未知错误: {str(e)}")
            raise RuntimeError(f"创建容器快照失败: {str(e)}")

    def restore_container_snapshot(
        self,
        snapshot: ContainerSnapshot,
        new_container_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从快照恢复容器

        Args:
            snapshot: 容器快照对象
            new_container_name: 新容器名称

        Returns:
            恢复后的容器信息

        Raises:
            RuntimeError: 恢复失败
        """
        if not snapshot.snapshot_path.exists():
            raise FileNotFoundError(f"快照文件不存在: {snapshot.snapshot_path}")

        try:
            logger.info(f"开始恢复容器快照: {snapshot.snapshot_id}")

            snapshot.status = SnapshotStatus.RESTORING

            self.load_image(snapshot.snapshot_path)

            image_name = snapshot.image_name
            if not image_name:
                image_name = snapshot.image_id[:12]

            container = self.client.containers.run(
                image_name,
                name=new_container_name,
                detach=True,
                labels=snapshot.labels,
            )

            snapshot.status = SnapshotStatus.COMPLETED

            logger.info(f"容器快照恢复成功: {snapshot.snapshot_id} -> {container.id}")

            return container.attrs

        except APIError as e:
            logger.error(f"恢复容器快照失败: {str(e)}")
            snapshot.status = SnapshotStatus.FAILED
            raise RuntimeError(f"恢复容器快照失败: {str(e)}")
        except Exception as e:
            logger.error(f"恢复容器快照发生未知错误: {str(e)}")
            snapshot.status = SnapshotStatus.FAILED
            raise RuntimeError(f"恢复容器快照失败: {str(e)}")

    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """
        列出容器

        Args:
            all_containers: 是否包含已停止的容器

        Returns:
            容器信息列表
        """
        try:
            containers = self.client.containers.list(all=all_containers)
            result = []

            for container in containers:
                info = container.attrs
                result.append({
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "image": info.get("Config", {}).get("Image", ""),
                    "image_id": info.get("Image", ""),
                    "created_at": info.get("Created", ""),
                    "labels": container.labels,
                    "ports": info.get("NetworkSettings", {}).get("Ports", {}),
                })

            return result

        except APIError as e:
            logger.error(f"列出容器失败: {str(e)}")
            raise RuntimeError(f"列出容器失败: {str(e)}")

    def list_images(self, all_images: bool = False) -> List[Dict[str, Any]]:
        """
        列出镜像

        Args:
            all_images: 是否包含中间层镜像

        Returns:
            镜像信息列表
        """
        try:
            images = self.client.images.list(all=all_images)
            result = []

            for image in images:
                tags = image.tags or []
                result.append({
                    "id": image.id,
                    "tags": tags,
                    "created_at": image.attrs.get("Created", ""),
                    "size": image.attrs.get("Size", 0),
                    "virtual_size": image.attrs.get("VirtualSize", 0),
                })

            return result

        except APIError as e:
            logger.error(f"列出镜像失败: {str(e)}")
            raise RuntimeError(f"列出镜像失败: {str(e)}")

    def start_container(self, container_id: str) -> bool:
        """
        启动容器

        Args:
            container_id: 容器ID或名称

        Returns:
            是否启动成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.start()
            logger.info(f"容器启动成功: {container_id}")
            return True

        except NotFound:
            raise RuntimeError(f"容器不存在: {container_id}")
        except APIError as e:
            logger.error(f"启动容器失败: {str(e)}")
            raise RuntimeError(f"启动容器失败: {str(e)}")

    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        停止容器

        Args:
            container_id: 容器ID或名称
            timeout: 等待停止的超时时间（秒）

        Returns:
            是否停止成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            logger.info(f"容器停止成功: {container_id}")
            return True

        except NotFound:
            raise RuntimeError(f"容器不存在: {container_id}")
        except APIError as e:
            logger.error(f"停止容器失败: {str(e)}")
            raise RuntimeError(f"停止容器失败: {str(e)}")

    def restart_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        重启容器

        Args:
            container_id: 容器ID或名称
            timeout: 等待停止的超时时间（秒）

        Returns:
            是否重启成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.restart(timeout=timeout)
            logger.info(f"容器重启成功: {container_id}")
            return True

        except NotFound:
            raise RuntimeError(f"容器不存在: {container_id}")
        except APIError as e:
            logger.error(f"重启容器失败: {str(e)}")
            raise RuntimeError(f"重启容器失败: {str(e)}")

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """
        删除容器

        Args:
            container_id: 容器ID或名称
            force: 是否强制删除

        Returns:
            是否删除成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            logger.info(f"容器删除成功: {container_id}")
            return True

        except NotFound:
            raise RuntimeError(f"容器不存在: {container_id}")
        except APIError as e:
            logger.error(f"删除容器失败: {str(e)}")
            raise RuntimeError(f"删除容器失败: {str(e)}")

    def get_container_info(self, container_id: str) -> Dict[str, Any]:
        """
        获取容器详细信息

        Args:
            container_id: 容器ID或名称

        Returns:
            容器详细信息

        Raises:
            RuntimeError: 获取失败
        """
        try:
            container = self.client.containers.get(container_id)
            return container.attrs

        except NotFound:
            raise RuntimeError(f"容器不存在: {container_id}")
        except APIError as e:
            logger.error(f"获取容器信息失败: {str(e)}")
            raise RuntimeError(f"获取容器信息失败: {str(e)}")

    def _generate_snapshot_id(self, container_id: str) -> str:
        """生成快照ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(f"{container_id}_{timestamp}".encode()).hexdigest()[:8]
        return f"snap_{timestamp}_{hash_part}"

    def _calculate_checksum(self, file_path: Path, algorithm: str = "sha256") -> str:
        """计算文件校验和"""
        hash_func = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    def _compress_tar(self, tar_path: Path, compression: str) -> Path:
        """压缩tar文件"""
        compressed_ext = {
            "gz": ".tar.gz",
            "bz2": ".tar.bz2",
            "xz": ".tar.xz",
        }

        ext = compressed_ext.get(compression)
        if not ext:
            raise ValueError(f"不支持的压缩类型: {compression}")

        compressed_path = tar_path.parent / (tar_path.stem + ext)

        mode = f"w:{compression}"
        with tarfile.open(compressed_path, mode) as tar:
            tar.add(tar_path, arcname=tar_path.name)

        return compressed_path

    def _decompress_tar(self, tar_path: Path) -> Path:
        """解压tar文件"""
        suffix = tar_path.suffix.lower()

        if suffix in (".gz", ".bz2", ".xz") or tar_path.suffixes[-2:] == [".tar", ".gz"]:
            temp_path = tar_path.parent / f"temp_{int(time.time())}.tar"

            mode = "r:"
            if suffix == ".gz":
                mode += "gz"
            elif suffix == ".bz2":
                mode += "bz2"
            elif suffix == ".xz":
                mode += "xz"

            with tarfile.open(tar_path, mode) as tar:
                tar.extractall(temp_path.parent)

            extracted_files = list(temp_path.parent.glob("*.tar"))
            if extracted_files:
                return extracted_files[0]

            return temp_path

        return tar_path

    def _get_image_name(self, container_info: Dict[str, Any]) -> str:
        """从容器信息中提取镜像名称"""
        image = container_info.get("Config", {}).get("Image", "")
        if image:
            parts = image.split(":")
            if len(parts) > 1:
                return ":".join(parts[:-1])
            return image
        return ""

    def _get_image_tag(self, container_info: Dict[str, Any]) -> str:
        """从容器信息中提取镜像标签"""
        image = container_info.get("Config", {}).get("Image", "")
        if image and ":" in image:
            return image.split(":")[-1]
        return "latest"


__all__ = [
    "ContainerConfig",
    "ContainerStatus",
    "SnapshotStatus",
    "ContainerSnapshot",
    "ContainerManager",
]