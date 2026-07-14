"""
云虚拟机快照管理模块

提供阿里云、腾讯云、AWS等云服务商的虚拟机快照管理功能，支持快照的创建、查询、删除和恢复操作。
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class CloudProvider(str, Enum):
    """云服务商枚举"""

    ALIYUN = "aliyun"
    TENCENT_CLOUD = "tencent_cloud"
    AWS = "aws"


class CloudVMConfig(BaseModel):
    """
    云虚拟机配置

    定义连接云服务商所需的参数。
    """

    provider: CloudProvider = Field(..., description="云服务商")
    region: str = Field(..., description="区域")
    access_key: str = Field(..., description="访问密钥")
    secret_key: str = Field(..., description="秘密密钥")
    security_token: Optional[str] = Field(default=None, description="安全令牌（可选）")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SnapshotStatus(str, Enum):
    """快照状态"""

    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"
    DELETED = "deleted"


class VMSnapshot(BaseModel):
    """
    虚拟机快照数据类

    存储虚拟机快照的完整信息。
    """

    snapshot_id: str = Field(..., description="快照ID")
    name: str = Field(..., description="快照名称")
    description: str = Field(default="", description="快照描述")

    created_at: str = Field(default="", description="创建时间")
    size: int = Field(default=0, description="快照大小（字节）")

    vm_id: str = Field(..., description="关联的虚拟机ID")
    vm_name: str = Field(default="", description="虚拟机名称")

    status: SnapshotStatus = Field(default=SnapshotStatus.COMPLETED, description="快照状态")
    disk_id: str = Field(default="", description="磁盘ID")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class VMInfo(BaseModel):
    """
    虚拟机信息数据类

    存储虚拟机的完整信息。
    """

    vm_id: str = Field(..., description="虚拟机ID")
    name: str = Field(default="", description="虚拟机名称")
    status: str = Field(default="", description="虚拟机状态")
    instance_type: str = Field(default="", description="实例类型")
    region: str = Field(default="", description="区域")
    zone: str = Field(default="", description="可用区")
    private_ip: str = Field(default="", description="私有IP")
    public_ip: str = Field(default="", description="公网IP")
    created_at: str = Field(default="", description="创建时间")
    disk_ids: List[str] = Field(default_factory=list, description="磁盘ID列表")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class CloudVMAdapter(ABC):
    """
    云虚拟机适配器抽象基类

    定义了所有云服务商适配器必须实现的接口。
    """

    def __init__(self, config: CloudVMConfig):
        """
        初始化云虚拟机适配器

        Args:
            config: 云虚拟机配置
        """
        self.config = config
        self._client = None
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def create_snapshot(self, vm_id: str, snapshot_name: str, description: str = "") -> VMSnapshot:
        """
        创建虚拟机快照

        Args:
            vm_id: 虚拟机ID
            snapshot_name: 快照名称
            description: 快照描述

        Returns:
            快照对象

        Raises:
            RuntimeError: 创建失败
        """
        pass

    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional[VMSnapshot]:
        """
        获取快照信息

        Args:
            snapshot_id: 快照ID

        Returns:
            快照对象，如果不存在返回None

        Raises:
            RuntimeError: 获取失败
        """
        pass

    @abstractmethod
    def list_snapshots(self, vm_id: str) -> List[VMSnapshot]:
        """
        列出虚拟机的所有快照

        Args:
            vm_id: 虚拟机ID

        Returns:
            快照列表

        Raises:
            RuntimeError: 列出失败
        """
        pass

    @abstractmethod
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        删除快照

        Args:
            snapshot_id: 快照ID

        Returns:
            是否删除成功

        Raises:
            RuntimeError: 删除失败
        """
        pass

    @abstractmethod
    def restore_snapshot(self, vm_id: str, snapshot_id: str) -> bool:
        """
        从快照恢复虚拟机

        Args:
            vm_id: 虚拟机ID
            snapshot_id: 快照ID

        Returns:
            是否恢复成功

        Raises:
            RuntimeError: 恢复失败
        """
        pass

    @abstractmethod
    def get_vm_info(self, vm_id: str) -> Optional[VMInfo]:
        """
        获取虚拟机信息

        Args:
            vm_id: 虚拟机ID

        Returns:
            虚拟机信息对象，如果不存在返回None

        Raises:
            RuntimeError: 获取失败
        """
        pass


class AliyunVMAdapter(CloudVMAdapter):
    """
    阿里云虚拟机适配器

    使用阿里云SDK（alibabacloud_ecs20140526）实现虚拟机快照管理功能。
    """

    def __init__(self, config: CloudVMConfig):
        super().__init__(config)

    @property
    def client(self):
        """获取阿里云ECS客户端"""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self):
        """创建阿里云ECS客户端"""
        try:
            from alibabacloud_ecs20140526.client import Client as Ecs20140526Client
            from alibabacloud_tea_openapi import models as open_api_models

            config = open_api_models.Config(
                access_key_id=self.config.access_key,
                access_key_secret=self.config.secret_key,
                region_id=self.config.region,
            )

            if self.config.security_token:
                config.security_token = self.config.security_token

            client = Ecs20140526Client(config)
            self.logger.info(f"阿里云ECS客户端连接成功: {self.config.region}")
            return client

        except ImportError:
            raise RuntimeError("阿里云SDK未安装，请安装 alibabacloud_ecs20140526")
        except Exception as e:
            self.logger.error(f"阿里云ECS客户端创建失败: {str(e)}")
            raise RuntimeError(f"阿里云ECS客户端创建失败: {str(e)}")

    def create_snapshot(self, vm_id: str, snapshot_name: str, description: str = "") -> VMSnapshot:
        try:
            from alibabacloud_ecs20140526 import models as ecs_20140526_models

            vm_info = self.get_vm_info(vm_id)
            if not vm_info or not vm_info.disk_ids:
                raise RuntimeError(f"虚拟机 {vm_id} 没有可用磁盘")

            disk_id = vm_info.disk_ids[0]

            request = ecs_20140526_models.CreateSnapshotRequest(
                disk_id=disk_id,
                snapshot_name=snapshot_name,
                description=description,
            )

            response = self.client.create_snapshot(request)

            if response.body.snapshot_id:
                snapshot = VMSnapshot(
                    snapshot_id=response.body.snapshot_id,
                    name=snapshot_name,
                    description=description,
                    vm_id=vm_id,
                    vm_name=vm_info.name,
                    status=SnapshotStatus.CREATING,
                    disk_id=disk_id,
                )
                self.logger.info(f"阿里云快照创建成功: {snapshot.snapshot_id}")
                return snapshot

            raise RuntimeError("创建快照失败，未返回快照ID")

        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"阿里云创建快照失败: {str(e)}")
            raise RuntimeError(f"阿里云创建快照失败: {str(e)}")

    def get_snapshot(self, snapshot_id: str) -> Optional[VMSnapshot]:
        try:
            from alibabacloud_ecs20140526 import models as ecs_20140526_models

            request = ecs_20140526_models.DescribeSnapshotsRequest(
                snapshot_id=snapshot_id,
            )

            response = self.client.describe_snapshots(request)

            if response.body.snapshots and response.body.snapshots.snapshot:
                snapshot_data = response.body.snapshots.snapshot[0]
                status_map = {
                    "progressing": SnapshotStatus.CREATING,
                    "accomplished": SnapshotStatus.COMPLETED,
                    "failed": SnapshotStatus.FAILED,
                    "deleting": SnapshotStatus.DELETED,
                }

                return VMSnapshot(
                    snapshot_id=snapshot_data.snapshot_id,
                    name=snapshot_data.snapshot_name,
                    description=snapshot_data.description or "",
                    created_at=snapshot_data.creation_time or "",
                    size=int(snapshot_data.size) * 1024 * 1024 if snapshot_data.size else 0,
                    vm_id=snapshot_data.source_disk_id or "",
                    vm_name="",
                    status=status_map.get(snapshot_data.status, SnapshotStatus.COMPLETED),
                    disk_id=snapshot_data.source_disk_id or "",
                )

            return None

        except Exception as e:
            self.logger.error(f"阿里云获取快照失败: {str(e)}")
            raise RuntimeError(f"阿里云获取快照失败: {str(e)}")

    def list_snapshots(self, vm_id: str) -> List[VMSnapshot]:
        try:
            from alibabacloud_ecs20140526 import models as ecs_20140526_models

            vm_info = self.get_vm_info(vm_id)
            if not vm_info:
                return []

            disk_ids = vm_info.disk_ids
            if not disk_ids:
                return []

            snapshots = []
            status_map = {
                "progressing": SnapshotStatus.CREATING,
                "accomplished": SnapshotStatus.COMPLETED,
                "failed": SnapshotStatus.FAILED,
                "deleting": SnapshotStatus.DELETED,
            }

            for disk_id in disk_ids:
                request = ecs_20140526_models.DescribeSnapshotsRequest(
                    source_disk_id=disk_id,
                )

                response = self.client.describe_snapshots(request)

                if response.body.snapshots and response.body.snapshots.snapshot:
                    for snapshot_data in response.body.snapshots.snapshot:
                        snapshots.append(
                            VMSnapshot(
                                snapshot_id=snapshot_data.snapshot_id,
                                name=snapshot_data.snapshot_name,
                                description=snapshot_data.description or "",
                                created_at=snapshot_data.creation_time or "",
                                size=int(snapshot_data.size) * 1024 * 1024 if snapshot_data.size else 0,
                                vm_id=vm_id,
                                vm_name=vm_info.name,
                                status=status_map.get(snapshot_data.status, SnapshotStatus.COMPLETED),
                                disk_id=disk_id,
                            )
                        )

            return snapshots

        except Exception as e:
            self.logger.error(f"阿里云列出快照失败: {str(e)}")
            raise RuntimeError(f"阿里云列出快照失败: {str(e)}")

    def delete_snapshot(self, snapshot_id: str) -> bool:
        try:
            from alibabacloud_ecs20140526 import models as ecs_20140526_models

            request = ecs_20140526_models.DeleteSnapshotRequest(
                snapshot_id=snapshot_id,
            )

            response = self.client.delete_snapshot(request)

            if response.body.code == "200":
                self.logger.info(f"阿里云快照删除成功: {snapshot_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"阿里云删除快照失败: {str(e)}")
            raise RuntimeError(f"阿里云删除快照失败: {str(e)}")

    def restore_snapshot(self, vm_id: str, snapshot_id: str) -> bool:
        try:
            from alibabacloud_ecs20140526 import models as ecs_20140526_models

            snapshot = self.get_snapshot(snapshot_id)
            if not snapshot:
                raise RuntimeError(f"快照 {snapshot_id} 不存在")

            request = ecs_20140526_models.CreateDiskRequest(
                zone_id=self.config.region,
                snapshot_id=snapshot_id,
                disk_name=f"restored_from_{snapshot_id}",
            )

            response = self.client.create_disk(request)

            if response.body.disk_id:
                attach_request = ecs_20140526_models.AttachDiskRequest(
                    instance_id=vm_id,
                    disk_id=response.body.disk_id,
                )
                self.client.attach_disk(attach_request)
                self.logger.info(f"阿里云快照恢复成功: {snapshot_id} -> {vm_id}")
                return True

            return False

        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"阿里云恢复快照失败: {str(e)}")
            raise RuntimeError(f"阿里云恢复快照失败: {str(e)}")

    def get_vm_info(self, vm_id: str) -> Optional[VMInfo]:
        try:
            from alibabacloud_ecs20140526 import models as ecs_20140526_models

            request = ecs_20140526_models.DescribeInstancesRequest(
                instance_ids=f'["{vm_id}"]',
            )

            response = self.client.describe_instances(request)

            if response.body.instances and response.body.instances.instance:
                instance_data = response.body.instances.instance[0]

                disk_ids = []
                if instance_data.disks and instance_data.disks.disk:
                    disk_ids = [disk.disk_id for disk in instance_data.disks.disk]

                return VMInfo(
                    vm_id=instance_data.instance_id,
                    name=instance_data.instance_name,
                    status=instance_data.status,
                    instance_type=instance_data.instance_type,
                    region=self.config.region,
                    zone=instance_data.zone_id,
                    private_ip=instance_data.private_ip_address.ip_address[0] if instance_data.private_ip_address and instance_data.private_ip_address.ip_address else "",
                    public_ip=instance_data.public_ip_address.ip_address[0] if instance_data.public_ip_address and instance_data.public_ip_address.ip_address else "",
                    created_at=instance_data.creation_time or "",
                    disk_ids=disk_ids,
                )

            return None

        except Exception as e:
            self.logger.error(f"阿里云获取虚拟机信息失败: {str(e)}")
            raise RuntimeError(f"阿里云获取虚拟机信息失败: {str(e)}")


class TencentCloudVMAdapter(CloudVMAdapter):
    """
    腾讯云虚拟机适配器

    使用腾讯云SDK（tencentcloud-sdk-python）实现虚拟机快照管理功能。
    """

    def __init__(self, config: CloudVMConfig):
        super().__init__(config)

    @property
    def client(self):
        """获取腾讯云CVM客户端"""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self):
        """创建腾讯云CVM客户端"""
        try:
            from tencentcloud.common import credential
            from tencentcloud.cvm.v20170312 import cvm_client, models

            cred = credential.Credential(
                self.config.access_key,
                self.config.secret_key,
            )

            client = cvm_client.CvmClient(cred, self.config.region)
            self.logger.info(f"腾讯云CVM客户端连接成功: {self.config.region}")
            return client

        except ImportError:
            raise RuntimeError("腾讯云SDK未安装，请安装 tencentcloud-sdk-python")
        except Exception as e:
            self.logger.error(f"腾讯云CVM客户端创建失败: {str(e)}")
            raise RuntimeError(f"腾讯云CVM客户端创建失败: {str(e)}")

    def _get_cbs_client(self):
        """获取腾讯云CBS客户端（用于快照操作）"""
        try:
            from tencentcloud.common import credential
            from tencentcloud.cbs.v20170312 import cbs_client

            cred = credential.Credential(
                self.config.access_key,
                self.config.secret_key,
            )

            return cbs_client.CbsClient(cred, self.config.region)

        except Exception as e:
            self.logger.error(f"腾讯云CBS客户端创建失败: {str(e)}")
            raise RuntimeError(f"腾讯云CBS客户端创建失败: {str(e)}")

    def create_snapshot(self, vm_id: str, snapshot_name: str, description: str = "") -> VMSnapshot:
        try:
            from tencentcloud.cbs.v20170312 import models as cbs_models

            vm_info = self.get_vm_info(vm_id)
            if not vm_info or not vm_info.disk_ids:
                raise RuntimeError(f"虚拟机 {vm_id} 没有可用磁盘")

            disk_id = vm_info.disk_ids[0]

            client = self._get_cbs_client()
            request = cbs_models.CreateSnapshotRequest(
                DiskId=disk_id,
                SnapshotName=snapshot_name,
                SnapshotDescription=description,
            )

            response = client.CreateSnapshot(request)

            if response.SnapshotId:
                snapshot = VMSnapshot(
                    snapshot_id=response.SnapshotId,
                    name=snapshot_name,
                    description=description,
                    vm_id=vm_id,
                    vm_name=vm_info.name,
                    status=SnapshotStatus.CREATING,
                    disk_id=disk_id,
                )
                self.logger.info(f"腾讯云快照创建成功: {snapshot.snapshot_id}")
                return snapshot

            raise RuntimeError("创建快照失败，未返回快照ID")

        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"腾讯云创建快照失败: {str(e)}")
            raise RuntimeError(f"腾讯云创建快照失败: {str(e)}")

    def get_snapshot(self, snapshot_id: str) -> Optional[VMSnapshot]:
        try:
            from tencentcloud.cbs.v20170312 import models as cbs_models

            client = self._get_cbs_client()
            request = cbs_models.DescribeSnapshotsRequest(
                SnapshotIds=[snapshot_id],
            )

            response = client.DescribeSnapshots(request)

            if response.SnapshotSet:
                snapshot_data = response.SnapshotSet[0]
                status_map = {
                    "CREATING": SnapshotStatus.CREATING,
                    "NORMAL": SnapshotStatus.COMPLETED,
                    "ROLLBACKING": SnapshotStatus.RESTORING,
                    "DELETING": SnapshotStatus.DELETED,
                }

                return VMSnapshot(
                    snapshot_id=snapshot_data.SnapshotId,
                    name=snapshot_data.SnapshotName,
                    description=snapshot_data.SnapshotDescription or "",
                    created_at=snapshot_data.CreateTime or "",
                    size=int(snapshot_data.Size) * 1024 * 1024 if snapshot_data.Size else 0,
                    vm_id=snapshot_data.DiskId or "",
                    vm_name="",
                    status=status_map.get(snapshot_data.Status, SnapshotStatus.COMPLETED),
                    disk_id=snapshot_data.DiskId or "",
                )

            return None

        except Exception as e:
            self.logger.error(f"腾讯云获取快照失败: {str(e)}")
            raise RuntimeError(f"腾讯云获取快照失败: {str(e)}")

    def list_snapshots(self, vm_id: str) -> List[VMSnapshot]:
        try:
            from tencentcloud.cbs.v20170312 import models as cbs_models

            vm_info = self.get_vm_info(vm_id)
            if not vm_info:
                return []

            disk_ids = vm_info.disk_ids
            if not disk_ids:
                return []

            client = self._get_cbs_client()
            request = cbs_models.DescribeSnapshotsRequest(
                DiskIds=disk_ids,
            )

            response = client.DescribeSnapshots(request)

            snapshots = []
            status_map = {
                "CREATING": SnapshotStatus.CREATING,
                "NORMAL": SnapshotStatus.COMPLETED,
                "ROLLBACKING": SnapshotStatus.RESTORING,
                "DELETING": SnapshotStatus.DELETED,
            }

            if response.SnapshotSet:
                for snapshot_data in response.SnapshotSet:
                    snapshots.append(
                        VMSnapshot(
                            snapshot_id=snapshot_data.SnapshotId,
                            name=snapshot_data.SnapshotName,
                            description=snapshot_data.SnapshotDescription or "",
                            created_at=snapshot_data.CreateTime or "",
                            size=int(snapshot_data.Size) * 1024 * 1024 if snapshot_data.Size else 0,
                            vm_id=vm_id,
                            vm_name=vm_info.name,
                            status=status_map.get(snapshot_data.Status, SnapshotStatus.COMPLETED),
                            disk_id=snapshot_data.DiskId or "",
                        )
                    )

            return snapshots

        except Exception as e:
            self.logger.error(f"腾讯云列出快照失败: {str(e)}")
            raise RuntimeError(f"腾讯云列出快照失败: {str(e)}")

    def delete_snapshot(self, snapshot_id: str) -> bool:
        try:
            from tencentcloud.cbs.v20170312 import models as cbs_models

            client = self._get_cbs_client()
            request = cbs_models.DeleteSnapshotsRequest(
                SnapshotIds=[snapshot_id],
            )

            response = client.DeleteSnapshots(request)

            if response.RequestId:
                self.logger.info(f"腾讯云快照删除成功: {snapshot_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"腾讯云删除快照失败: {str(e)}")
            raise RuntimeError(f"腾讯云删除快照失败: {str(e)}")

    def restore_snapshot(self, vm_id: str, snapshot_id: str) -> bool:
        try:
            from tencentcloud.cbs.v20170312 import models as cbs_models
            from tencentcloud.cvm.v20170312 import models as cvm_models

            snapshot = self.get_snapshot(snapshot_id)
            if not snapshot:
                raise RuntimeError(f"快照 {snapshot_id} 不存在")

            client = self._get_cbs_client()
            request = cbs_models.CreateDisksRequest(
                Placement={"Zone": self.config.region},
                DiskType="CLOUD_PREMIUM",
                DiskSize=100,
                SnapshotId=snapshot_id,
            )

            response = client.CreateDisks(request)

            if response.DiskIds and response.DiskIds[0]:
                disk_id = response.DiskIds[0]
                cvm_request = cvm_models.AttachDisksRequest(
                    InstanceId=vm_id,
                    DiskIds=[disk_id],
                )
                self.client.AttachDisks(cvm_request)
                self.logger.info(f"腾讯云快照恢复成功: {snapshot_id} -> {vm_id}")
                return True

            return False

        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"腾讯云恢复快照失败: {str(e)}")
            raise RuntimeError(f"腾讯云恢复快照失败: {str(e)}")

    def get_vm_info(self, vm_id: str) -> Optional[VMInfo]:
        try:
            from tencentcloud.cvm.v20170312 import models as cvm_models

            request = cvm_models.DescribeInstancesRequest(
                InstanceIds=[vm_id],
            )

            response = self.client.DescribeInstances(request)

            if response.InstanceSet:
                instance_data = response.InstanceSet[0]

                disk_ids = []
                if instance_data.DataDisks:
                    disk_ids = [disk.DiskId for disk in instance_data.DataDisks]
                if instance_data.SystemDisk:
                    disk_ids.insert(0, instance_data.SystemDisk.DiskId)

                return VMInfo(
                    vm_id=instance_data.InstanceId,
                    name=instance_data.InstanceName,
                    status=instance_data.InstanceState,
                    instance_type=instance_data.InstanceType,
                    region=self.config.region,
                    zone=instance_data.Placement.Zone,
                    private_ip=instance_data.PrivateIpAddresses[0] if instance_data.PrivateIpAddresses else "",
                    public_ip=instance_data.PublicIpAddresses[0] if instance_data.PublicIpAddresses else "",
                    created_at=instance_data.CreatedTime or "",
                    disk_ids=disk_ids,
                )

            return None

        except Exception as e:
            self.logger.error(f"腾讯云获取虚拟机信息失败: {str(e)}")
            raise RuntimeError(f"腾讯云获取虚拟机信息失败: {str(e)}")


class AWSVMAdapter(CloudVMAdapter):
    """
    AWS虚拟机适配器

    使用AWS SDK（boto3）实现虚拟机快照管理功能。
    """

    def __init__(self, config: CloudVMConfig):
        super().__init__(config)

    @property
    def client(self):
        """获取AWS EC2客户端"""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self):
        """创建AWS EC2客户端"""
        try:
            import boto3

            kwargs = {
                "aws_access_key_id": self.config.access_key,
                "aws_secret_access_key": self.config.secret_key,
                "region_name": self.config.region,
            }

            if self.config.security_token:
                kwargs["aws_session_token"] = self.config.security_token

            client = boto3.client("ec2", **kwargs)
            self.logger.info(f"AWS EC2客户端连接成功: {self.config.region}")
            return client

        except ImportError:
            raise RuntimeError("AWS SDK未安装，请安装 boto3")
        except Exception as e:
            self.logger.error(f"AWS EC2客户端创建失败: {str(e)}")
            raise RuntimeError(f"AWS EC2客户端创建失败: {str(e)}")

    def create_snapshot(self, vm_id: str, snapshot_name: str, description: str = "") -> VMSnapshot:
        try:
            vm_info = self.get_vm_info(vm_id)
            if not vm_info or not vm_info.disk_ids:
                raise RuntimeError(f"虚拟机 {vm_id} 没有可用磁盘")

            volume_id = vm_info.disk_ids[0]

            response = self.client.create_snapshot(
                VolumeId=volume_id,
                Description=description,
                TagSpecifications=[
                    {
                        "ResourceType": "snapshot",
                        "Tags": [
                            {"Key": "Name", "Value": snapshot_name},
                        ],
                    }
                ],
            )

            if response["SnapshotId"]:
                snapshot = VMSnapshot(
                    snapshot_id=response["SnapshotId"],
                    name=snapshot_name,
                    description=description,
                    vm_id=vm_id,
                    vm_name=vm_info.name,
                    status=SnapshotStatus.CREATING,
                    disk_id=volume_id,
                )
                self.logger.info(f"AWS快照创建成功: {snapshot.snapshot_id}")
                return snapshot

            raise RuntimeError("创建快照失败，未返回快照ID")

        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"AWS创建快照失败: {str(e)}")
            raise RuntimeError(f"AWS创建快照失败: {str(e)}")

    def get_snapshot(self, snapshot_id: str) -> Optional[VMSnapshot]:
        try:
            response = self.client.describe_snapshots(
                SnapshotIds=[snapshot_id],
            )

            if response["Snapshots"]:
                snapshot_data = response["Snapshots"][0]
                status_map = {
                    "pending": SnapshotStatus.CREATING,
                    "completed": SnapshotStatus.COMPLETED,
                    "error": SnapshotStatus.FAILED,
                }

                name = ""
                for tag in snapshot_data.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                return VMSnapshot(
                    snapshot_id=snapshot_data["SnapshotId"],
                    name=name,
                    description=snapshot_data.get("Description", ""),
                    created_at=snapshot_data["StartTime"].isoformat() if snapshot_data.get("StartTime") else "",
                    size=int(snapshot_data.get("VolumeSize", 0)) * 1024 * 1024,
                    vm_id=snapshot_data.get("VolumeId", ""),
                    vm_name="",
                    status=status_map.get(snapshot_data["State"], SnapshotStatus.COMPLETED),
                    disk_id=snapshot_data.get("VolumeId", ""),
                )

            return None

        except Exception as e:
            self.logger.error(f"AWS获取快照失败: {str(e)}")
            raise RuntimeError(f"AWS获取快照失败: {str(e)}")

    def list_snapshots(self, vm_id: str) -> List[VMSnapshot]:
        try:
            vm_info = self.get_vm_info(vm_id)
            if not vm_info:
                return []

            volume_ids = vm_info.disk_ids
            if not volume_ids:
                return []

            response = self.client.describe_snapshots(
                Filters=[
                    {"Name": "volume-id", "Values": volume_ids},
                ],
            )

            snapshots = []
            status_map = {
                "pending": SnapshotStatus.CREATING,
                "completed": SnapshotStatus.COMPLETED,
                "error": SnapshotStatus.FAILED,
            }

            for snapshot_data in response["Snapshots"]:
                name = ""
                for tag in snapshot_data.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                snapshots.append(
                    VMSnapshot(
                        snapshot_id=snapshot_data["SnapshotId"],
                        name=name,
                        description=snapshot_data.get("Description", ""),
                        created_at=snapshot_data["StartTime"].isoformat() if snapshot_data.get("StartTime") else "",
                        size=int(snapshot_data.get("VolumeSize", 0)) * 1024 * 1024,
                        vm_id=vm_id,
                        vm_name=vm_info.name,
                        status=status_map.get(snapshot_data["State"], SnapshotStatus.COMPLETED),
                        disk_id=snapshot_data.get("VolumeId", ""),
                    )
                )

            return snapshots

        except Exception as e:
            self.logger.error(f"AWS列出快照失败: {str(e)}")
            raise RuntimeError(f"AWS列出快照失败: {str(e)}")

    def delete_snapshot(self, snapshot_id: str) -> bool:
        try:
            response = self.client.delete_snapshot(
                SnapshotId=snapshot_id,
            )

            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                self.logger.info(f"AWS快照删除成功: {snapshot_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"AWS删除快照失败: {str(e)}")
            raise RuntimeError(f"AWS删除快照失败: {str(e)}")

    def restore_snapshot(self, vm_id: str, snapshot_id: str) -> bool:
        try:
            snapshot = self.get_snapshot(snapshot_id)
            if not snapshot:
                raise RuntimeError(f"快照 {snapshot_id} 不存在")

            vm_info = self.get_vm_info(vm_id)
            if not vm_info:
                raise RuntimeError(f"虚拟机 {vm_id} 不存在")

            response = self.client.create_volume(
                AvailabilityZone=vm_info.zone,
                SnapshotId=snapshot_id,
            )

            if response["VolumeId"]:
                volume_id = response["VolumeId"]
                self.client.attach_volume(
                    Device="/dev/sdf",
                    InstanceId=vm_id,
                    VolumeId=volume_id,
                )
                self.logger.info(f"AWS快照恢复成功: {snapshot_id} -> {vm_id}")
                return True

            return False

        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"AWS恢复快照失败: {str(e)}")
            raise RuntimeError(f"AWS恢复快照失败: {str(e)}")

    def get_vm_info(self, vm_id: str) -> Optional[VMInfo]:
        try:
            response = self.client.describe_instances(
                InstanceIds=[vm_id],
            )

            if response["Reservations"]:
                instance_data = response["Reservations"][0]["Instances"][0]

                volume_ids = []
                for mapping in instance_data.get("BlockDeviceMappings", []):
                    ebs = mapping.get("Ebs", {})
                    if ebs.get("VolumeId"):
                        volume_ids.append(ebs["VolumeId"])

                name = ""
                for tag in instance_data.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                return VMInfo(
                    vm_id=instance_data["InstanceId"],
                    name=name,
                    status=instance_data["State"]["Name"],
                    instance_type=instance_data["InstanceType"],
                    region=self.config.region,
                    zone=instance_data["Placement"]["AvailabilityZone"],
                    private_ip=instance_data.get("PrivateIpAddress", ""),
                    public_ip=instance_data.get("PublicIpAddress", ""),
                    created_at=instance_data["LaunchTime"].isoformat() if instance_data.get("LaunchTime") else "",
                    disk_ids=volume_ids,
                )

            return None

        except Exception as e:
            self.logger.error(f"AWS获取虚拟机信息失败: {str(e)}")
            raise RuntimeError(f"AWS获取虚拟机信息失败: {str(e)}")


class CloudVMManager:
    """
    云虚拟机管理器

    根据配置选择合适的适配器，提供统一的云虚拟机快照管理API。
    """

    def __init__(self, config: CloudVMConfig):
        """
        初始化云虚拟机管理器

        Args:
            config: 云虚拟机配置
        """
        self.config = config
        self._adapter = self._create_adapter()

    def _create_adapter(self) -> CloudVMAdapter:
        """根据配置创建适配器"""
        adapter_map = {
            CloudProvider.ALIYUN: AliyunVMAdapter,
            CloudProvider.TENCENT_CLOUD: TencentCloudVMAdapter,
            CloudProvider.AWS: AWSVMAdapter,
        }

        adapter_class = adapter_map.get(self.config.provider)
        if not adapter_class:
            raise ValueError(f"不支持的云服务商: {self.config.provider}")

        return adapter_class(self.config)

    @property
    def adapter(self) -> CloudVMAdapter:
        """获取当前适配器"""
        return self._adapter

    def create_snapshot(self, vm_id: str, snapshot_name: str, description: str = "") -> VMSnapshot:
        """
        创建虚拟机快照

        Args:
            vm_id: 虚拟机ID
            snapshot_name: 快照名称
            description: 快照描述

        Returns:
            快照对象
        """
        return self._adapter.create_snapshot(vm_id, snapshot_name, description)

    def get_snapshot(self, snapshot_id: str) -> Optional[VMSnapshot]:
        """
        获取快照信息

        Args:
            snapshot_id: 快照ID

        Returns:
            快照对象，如果不存在返回None
        """
        return self._adapter.get_snapshot(snapshot_id)

    def list_snapshots(self, vm_id: str) -> List[VMSnapshot]:
        """
        列出虚拟机的所有快照

        Args:
            vm_id: 虚拟机ID

        Returns:
            快照列表
        """
        return self._adapter.list_snapshots(vm_id)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        删除快照

        Args:
            snapshot_id: 快照ID

        Returns:
            是否删除成功
        """
        return self._adapter.delete_snapshot(snapshot_id)

    def restore_snapshot(self, vm_id: str, snapshot_id: str) -> bool:
        """
        从快照恢复虚拟机

        Args:
            vm_id: 虚拟机ID
            snapshot_id: 快照ID

        Returns:
            是否恢复成功
        """
        return self._adapter.restore_snapshot(vm_id, snapshot_id)

    def get_vm_info(self, vm_id: str) -> Optional[VMInfo]:
        """
        获取虚拟机信息

        Args:
            vm_id: 虚拟机ID

        Returns:
            虚拟机信息对象，如果不存在返回None
        """
        return self._adapter.get_vm_info(vm_id)


__all__ = [
    "CloudProvider",
    "CloudVMConfig",
    "SnapshotStatus",
    "VMSnapshot",
    "VMInfo",
    "CloudVMAdapter",
    "AliyunVMAdapter",
    "TencentCloudVMAdapter",
    "AWSVMAdapter",
    "CloudVMManager",
]