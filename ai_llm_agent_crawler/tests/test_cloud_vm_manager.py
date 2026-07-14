"""
云虚拟机快照管理模块单元测试

使用mock测试阿里云、腾讯云、AWS适配器的接口调用，验证返回正确结构。
"""

import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

from ai_llm_agent_crawler.cloud_vm_manager import (
    CloudProvider,
    CloudVMConfig,
    SnapshotStatus,
    VMSnapshot,
    VMInfo,
    CloudVMAdapter,
    AliyunVMAdapter,
    TencentCloudVMAdapter,
    AWSVMAdapter,
    CloudVMManager,
)


class MockModule:
    """Mock模块"""
    pass


class TestCloudVMAdapterInterface:
    """CloudVMAdapter接口定义测试"""

    def test_interface_defined_correctly(self):
        """测试适配器接口定义正确"""
        assert hasattr(CloudVMAdapter, "create_snapshot")
        assert hasattr(CloudVMAdapter, "get_snapshot")
        assert hasattr(CloudVMAdapter, "list_snapshots")
        assert hasattr(CloudVMAdapter, "delete_snapshot")
        assert hasattr(CloudVMAdapter, "restore_snapshot")
        assert hasattr(CloudVMAdapter, "get_vm_info")

    def test_methods_are_abstract(self):
        """测试接口方法都是抽象方法"""
        methods = [
            "create_snapshot",
            "get_snapshot",
            "list_snapshots",
            "delete_snapshot",
            "restore_snapshot",
            "get_vm_info",
        ]

        for method_name in methods:
            method = getattr(CloudVMAdapter, method_name)
            assert getattr(method, "__isabstractmethod__", False), f"{method_name} 应该是抽象方法"

    def test_concrete_adapters_implement_all_methods(self):
        """测试所有具体适配器实现了所有接口方法"""
        adapters = [AliyunVMAdapter, TencentCloudVMAdapter, AWSVMAdapter]

        for adapter_class in adapters:
            adapter = adapter_class(
                CloudVMConfig(
                    provider=CloudProvider.ALIYUN,
                    region="test-region",
                    access_key="test-key",
                    secret_key="test-secret",
                )
            )
            assert callable(adapter.create_snapshot)
            assert callable(adapter.get_snapshot)
            assert callable(adapter.list_snapshots)
            assert callable(adapter.delete_snapshot)
            assert callable(adapter.restore_snapshot)
            assert callable(adapter.get_vm_info)


class TestAliyunVMAdapter:
    """阿里云适配器测试"""

    @pytest.fixture
    def aliyun_config(self):
        """阿里云配置fixture"""
        return CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test-access-key",
            secret_key="test-secret-key",
        )

    @pytest.fixture(autouse=True)
    def setup_aliyun_mocks(self):
        """设置阿里云mock模块"""
        alibabacloud_tea_openapi = MockModule()
        alibabacloud_tea_openapi.models = MockModule()
        alibabacloud_tea_openapi.models.Config = Mock

        alibabacloud_ecs20140526 = MockModule()
        alibabacloud_ecs20140526.client = MockModule()
        alibabacloud_ecs20140526.client.Client = Mock
        alibabacloud_ecs20140526.models = MockModule()
        alibabacloud_ecs20140526.models.CreateSnapshotRequest = Mock
        alibabacloud_ecs20140526.models.DescribeSnapshotsRequest = Mock
        alibabacloud_ecs20140526.models.DeleteSnapshotRequest = Mock
        alibabacloud_ecs20140526.models.CreateDiskRequest = Mock
        alibabacloud_ecs20140526.models.AttachDiskRequest = Mock
        alibabacloud_ecs20140526.models.DescribeInstancesRequest = Mock

        sys.modules["alibabacloud_tea_openapi"] = alibabacloud_tea_openapi
        sys.modules["alibabacloud_tea_openapi.models"] = alibabacloud_tea_openapi.models
        sys.modules["alibabacloud_ecs20140526"] = alibabacloud_ecs20140526
        sys.modules["alibabacloud_ecs20140526.client"] = alibabacloud_ecs20140526.client
        sys.modules["alibabacloud_ecs20140526.models"] = alibabacloud_ecs20140526.models

        yield

        for mod in [
            "alibabacloud_tea_openapi",
            "alibabacloud_tea_openapi.models",
            "alibabacloud_ecs20140526",
            "alibabacloud_ecs20140526.client",
            "alibabacloud_ecs20140526.models",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_create_snapshot_returns_correct_structure(self, aliyun_config):
        """测试阿里云创建快照返回正确结构"""
        mock_client = Mock()

        mock_vm_response = Mock()
        mock_vm_response.body.instances = Mock()
        mock_vm_response.body.instances.instance = [
            Mock(
                instance_id="i-test123",
                instance_name="test-vm",
                status="Running",
                instance_type="ecs.g6.large",
                zone_id="cn-beijing-a",
                private_ip_address=Mock(ip_address=["10.0.0.1"]),
                public_ip_address=Mock(ip_address=["1.2.3.4"]),
                creation_time="2024-01-01T00:00:00Z",
                disks=Mock(disk=[Mock(disk_id="d-test123")]),
            )
        ]
        mock_client.describe_instances.return_value = mock_vm_response

        mock_snapshot_response = Mock()
        mock_snapshot_response.body.snapshot_id = "snap-test123"
        mock_client.create_snapshot.return_value = mock_snapshot_response

        with patch("alibabacloud_ecs20140526.client.Client", return_value=mock_client):
            adapter = AliyunVMAdapter(aliyun_config)
            snapshot = adapter.create_snapshot("i-test123", "test-snapshot", "测试快照")

        assert isinstance(snapshot, VMSnapshot)
        assert snapshot.snapshot_id == "snap-test123"
        assert snapshot.name == "test-snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.vm_id == "i-test123"
        assert snapshot.vm_name == "test-vm"
        assert snapshot.status == SnapshotStatus.CREATING
        assert snapshot.disk_id == "d-test123"

    def test_get_snapshot_returns_correct_structure(self, aliyun_config):
        """测试阿里云获取快照返回正确结构"""
        mock_client = Mock()

        mock_response = Mock()
        mock_response.body.snapshots = Mock()
        mock_response.body.snapshots.snapshot = [
            Mock(
                snapshot_id="snap-test123",
                snapshot_name="test-snapshot",
                description="测试快照",
                creation_time="2024-01-01T00:00:00Z",
                size="40",
                source_disk_id="d-test123",
                status="accomplished",
            )
        ]
        mock_client.describe_snapshots.return_value = mock_response

        with patch("alibabacloud_ecs20140526.client.Client", return_value=mock_client):
            adapter = AliyunVMAdapter(aliyun_config)
            snapshot = adapter.get_snapshot("snap-test123")

        assert isinstance(snapshot, VMSnapshot)
        assert snapshot.snapshot_id == "snap-test123"
        assert snapshot.name == "test-snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.created_at == "2024-01-01T00:00:00Z"
        assert snapshot.size == 40 * 1024 * 1024
        assert snapshot.disk_id == "d-test123"
        assert snapshot.status == SnapshotStatus.COMPLETED

    def test_list_snapshots_returns_correct_structure(self, aliyun_config):
        """测试阿里云列出快照返回正确结构"""
        mock_client = Mock()

        mock_vm_response = Mock()
        mock_vm_response.body.instances = Mock()
        mock_vm_response.body.instances.instance = [
            Mock(
                instance_id="i-test123",
                instance_name="test-vm",
                status="Running",
                instance_type="ecs.g6.large",
                zone_id="cn-beijing-a",
                private_ip_address=Mock(ip_address=["10.0.0.1"]),
                public_ip_address=Mock(ip_address=["1.2.3.4"]),
                creation_time="2024-01-01T00:00:00Z",
                disks=Mock(disk=[Mock(disk_id="d-test123")]),
            )
        ]
        mock_client.describe_instances.return_value = mock_vm_response

        mock_snapshot_response = Mock()
        mock_snapshot_response.body.snapshots = Mock()
        mock_snapshot_response.body.snapshots.snapshot = [
            Mock(
                snapshot_id="snap-test123",
                snapshot_name="test-snapshot",
                description="测试快照",
                creation_time="2024-01-01T00:00:00Z",
                size="40",
                source_disk_id="d-test123",
                status="accomplished",
            )
        ]
        mock_client.describe_snapshots.return_value = mock_snapshot_response

        with patch("alibabacloud_ecs20140526.client.Client", return_value=mock_client):
            adapter = AliyunVMAdapter(aliyun_config)
            snapshots = adapter.list_snapshots("i-test123")

        assert isinstance(snapshots, list)
        assert len(snapshots) == 1
        assert isinstance(snapshots[0], VMSnapshot)
        assert snapshots[0].snapshot_id == "snap-test123"
        assert snapshots[0].vm_id == "i-test123"
        assert snapshots[0].vm_name == "test-vm"

    def test_delete_snapshot_returns_correct_structure(self, aliyun_config):
        """测试阿里云删除快照返回正确结构"""
        mock_client = Mock()

        mock_response = Mock()
        mock_response.body.code = "200"
        mock_client.delete_snapshot.return_value = mock_response

        with patch("alibabacloud_ecs20140526.client.Client", return_value=mock_client):
            adapter = AliyunVMAdapter(aliyun_config)
            result = adapter.delete_snapshot("snap-test123")

        assert isinstance(result, bool)
        assert result is True

    def test_restore_snapshot_returns_correct_structure(self, aliyun_config):
        """测试阿里云恢复快照返回正确结构"""
        mock_client = Mock()

        mock_snapshot_response = Mock()
        mock_snapshot_response.body.snapshots = Mock()
        mock_snapshot_response.body.snapshots.snapshot = [
            Mock(
                snapshot_id="snap-test123",
                snapshot_name="test-snapshot",
                description="测试快照",
                creation_time="2024-01-01T00:00:00Z",
                size="40",
                source_disk_id="d-test123",
                status="accomplished",
            )
        ]
        mock_client.describe_snapshots.return_value = mock_snapshot_response

        mock_disk_response = Mock()
        mock_disk_response.body.disk_id = "d-restored123"
        mock_client.create_disk.return_value = mock_disk_response

        mock_attach_response = Mock()
        mock_client.attach_disk.return_value = mock_attach_response

        with patch("alibabacloud_ecs20140526.client.Client", return_value=mock_client):
            adapter = AliyunVMAdapter(aliyun_config)
            result = adapter.restore_snapshot("i-test123", "snap-test123")

        assert isinstance(result, bool)
        assert result is True

    def test_get_vm_info_returns_correct_structure(self, aliyun_config):
        """测试阿里云获取虚拟机信息返回正确结构"""
        mock_client = Mock()

        mock_response = Mock()
        mock_response.body.instances = Mock()
        mock_response.body.instances.instance = [
            Mock(
                instance_id="i-test123",
                instance_name="test-vm",
                status="Running",
                instance_type="ecs.g6.large",
                zone_id="cn-beijing-a",
                private_ip_address=Mock(ip_address=["10.0.0.1"]),
                public_ip_address=Mock(ip_address=["1.2.3.4"]),
                creation_time="2024-01-01T00:00:00Z",
                disks=Mock(disk=[Mock(disk_id="d-test123")]),
            )
        ]
        mock_client.describe_instances.return_value = mock_response

        with patch("alibabacloud_ecs20140526.client.Client", return_value=mock_client):
            adapter = AliyunVMAdapter(aliyun_config)
            vm_info = adapter.get_vm_info("i-test123")

        assert isinstance(vm_info, VMInfo)
        assert vm_info.vm_id == "i-test123"
        assert vm_info.name == "test-vm"
        assert vm_info.status == "Running"
        assert vm_info.instance_type == "ecs.g6.large"
        assert vm_info.region == "cn-beijing"
        assert vm_info.zone == "cn-beijing-a"
        assert vm_info.private_ip == "10.0.0.1"
        assert vm_info.public_ip == "1.2.3.4"
        assert vm_info.created_at == "2024-01-01T00:00:00Z"
        assert vm_info.disk_ids == ["d-test123"]


class TestTencentCloudVMAdapter:
    """腾讯云适配器测试"""

    @pytest.fixture
    def tencent_config(self):
        """腾讯云配置fixture"""
        return CloudVMConfig(
            provider=CloudProvider.TENCENT_CLOUD,
            region="ap-beijing",
            access_key="test-access-key",
            secret_key="test-secret-key",
        )

    @pytest.fixture(autouse=True)
    def setup_tencent_mocks(self):
        """设置腾讯云mock模块"""
        tencentcloud = MockModule()
        tencentcloud.common = MockModule()
        tencentcloud.common.credential = MockModule()
        tencentcloud.common.credential.Credential = Mock

        tencentcloud.cvm = MockModule()
        tencentcloud.cvm.v20170312 = MockModule()
        tencentcloud.cvm.v20170312.cvm_client = MockModule()
        tencentcloud.cvm.v20170312.cvm_client.CvmClient = Mock
        tencentcloud.cvm.v20170312.models = MockModule()
        tencentcloud.cvm.v20170312.models.DescribeInstancesRequest = Mock
        tencentcloud.cvm.v20170312.models.AttachDisksRequest = Mock

        tencentcloud.cbs = MockModule()
        tencentcloud.cbs.v20170312 = MockModule()
        tencentcloud.cbs.v20170312.cbs_client = MockModule()
        tencentcloud.cbs.v20170312.cbs_client.CbsClient = Mock
        tencentcloud.cbs.v20170312.models = MockModule()
        tencentcloud.cbs.v20170312.models.CreateSnapshotRequest = Mock
        tencentcloud.cbs.v20170312.models.DescribeSnapshotsRequest = Mock
        tencentcloud.cbs.v20170312.models.DeleteSnapshotsRequest = Mock
        tencentcloud.cbs.v20170312.models.CreateDisksRequest = Mock

        sys.modules["tencentcloud"] = tencentcloud
        sys.modules["tencentcloud.common"] = tencentcloud.common
        sys.modules["tencentcloud.common.credential"] = tencentcloud.common.credential
        sys.modules["tencentcloud.cvm"] = tencentcloud.cvm
        sys.modules["tencentcloud.cvm.v20170312"] = tencentcloud.cvm.v20170312
        sys.modules["tencentcloud.cvm.v20170312.cvm_client"] = tencentcloud.cvm.v20170312.cvm_client
        sys.modules["tencentcloud.cvm.v20170312.models"] = tencentcloud.cvm.v20170312.models
        sys.modules["tencentcloud.cbs"] = tencentcloud.cbs
        sys.modules["tencentcloud.cbs.v20170312"] = tencentcloud.cbs.v20170312
        sys.modules["tencentcloud.cbs.v20170312.cbs_client"] = tencentcloud.cbs.v20170312.cbs_client
        sys.modules["tencentcloud.cbs.v20170312.models"] = tencentcloud.cbs.v20170312.models

        yield

        for mod in [
            "tencentcloud",
            "tencentcloud.common",
            "tencentcloud.common.credential",
            "tencentcloud.cvm",
            "tencentcloud.cvm.v20170312",
            "tencentcloud.cvm.v20170312.cvm_client",
            "tencentcloud.cvm.v20170312.models",
            "tencentcloud.cbs",
            "tencentcloud.cbs.v20170312",
            "tencentcloud.cbs.v20170312.cbs_client",
            "tencentcloud.cbs.v20170312.models",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_create_snapshot_returns_correct_structure(self, tencent_config):
        """测试腾讯云创建快照返回正确结构"""
        mock_client = Mock()
        mock_cbs_client = Mock()

        mock_vm_response = Mock()
        instance_data = Mock()
        instance_data.InstanceId = "ins-test123"
        instance_data.InstanceName = "test-vm"
        instance_data.InstanceState = "RUNNING"
        instance_data.InstanceType = "S6.LARGE8"
        instance_data.Placement = Mock(Zone="ap-beijing-1")
        instance_data.PrivateIpAddresses = ["10.0.0.1"]
        instance_data.PublicIpAddresses = ["1.2.3.4"]
        instance_data.CreatedTime = "2024-01-01T00:00:00Z"
        instance_data.SystemDisk = Mock(DiskId="disk-test123")
        instance_data.DataDisks = []
        mock_vm_response.InstanceSet = [instance_data]
        mock_client.DescribeInstances.return_value = mock_vm_response

        mock_snapshot_response = Mock()
        mock_snapshot_response.SnapshotId = "snap-test123"
        mock_cbs_client.CreateSnapshot.return_value = mock_snapshot_response

        with patch("tencentcloud.cvm.v20170312.cvm_client.CvmClient", return_value=mock_client):
            with patch("tencentcloud.cbs.v20170312.cbs_client.CbsClient", return_value=mock_cbs_client):
                adapter = TencentCloudVMAdapter(tencent_config)
                snapshot = adapter.create_snapshot("ins-test123", "test-snapshot", "测试快照")

        assert isinstance(snapshot, VMSnapshot)
        assert snapshot.snapshot_id == "snap-test123"
        assert snapshot.name == "test-snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.vm_id == "ins-test123"
        assert snapshot.vm_name == "test-vm"
        assert snapshot.status == SnapshotStatus.CREATING
        assert snapshot.disk_id == "disk-test123"

    def test_get_snapshot_returns_correct_structure(self, tencent_config):
        """测试腾讯云获取快照返回正确结构"""
        mock_client = Mock()
        mock_cbs_client = Mock()

        mock_response = Mock()
        snapshot_data = Mock()
        snapshot_data.SnapshotId = "snap-test123"
        snapshot_data.SnapshotName = "test-snapshot"
        snapshot_data.SnapshotDescription = "测试快照"
        snapshot_data.CreateTime = "2024-01-01T00:00:00Z"
        snapshot_data.Size = 40
        snapshot_data.DiskId = "disk-test123"
        snapshot_data.Status = "NORMAL"
        mock_response.SnapshotSet = [snapshot_data]
        mock_cbs_client.DescribeSnapshots.return_value = mock_response

        with patch("tencentcloud.cvm.v20170312.cvm_client.CvmClient", return_value=mock_client):
            with patch("tencentcloud.cbs.v20170312.cbs_client.CbsClient", return_value=mock_cbs_client):
                adapter = TencentCloudVMAdapter(tencent_config)
                snapshot = adapter.get_snapshot("snap-test123")

        assert isinstance(snapshot, VMSnapshot)
        assert snapshot.snapshot_id == "snap-test123"
        assert snapshot.name == "test-snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.created_at == "2024-01-01T00:00:00Z"
        assert snapshot.size == 40 * 1024 * 1024
        assert snapshot.disk_id == "disk-test123"
        assert snapshot.status == SnapshotStatus.COMPLETED

    def test_list_snapshots_returns_correct_structure(self, tencent_config):
        """测试腾讯云列出快照返回正确结构"""
        mock_client = Mock()
        mock_cbs_client = Mock()

        mock_vm_response = Mock()
        instance_data = Mock()
        instance_data.InstanceId = "ins-test123"
        instance_data.InstanceName = "test-vm"
        instance_data.SystemDisk = Mock(DiskId="disk-test123")
        instance_data.DataDisks = []
        instance_data.PrivateIpAddresses = ["10.0.0.1"]
        instance_data.PublicIpAddresses = ["1.2.3.4"]
        instance_data.InstanceState = "RUNNING"
        instance_data.InstanceType = "S6.LARGE8"
        instance_data.Placement = Mock(Zone="ap-beijing-1")
        instance_data.CreatedTime = "2024-01-01T00:00:00Z"
        mock_vm_response.InstanceSet = [instance_data]
        mock_client.DescribeInstances.return_value = mock_vm_response

        mock_snapshot_response = Mock()
        snapshot_data = Mock()
        snapshot_data.SnapshotId = "snap-test123"
        snapshot_data.SnapshotName = "test-snapshot"
        snapshot_data.SnapshotDescription = "测试快照"
        snapshot_data.CreateTime = "2024-01-01T00:00:00Z"
        snapshot_data.Size = 40
        snapshot_data.DiskId = "disk-test123"
        snapshot_data.Status = "NORMAL"
        mock_snapshot_response.SnapshotSet = [snapshot_data]
        mock_cbs_client.DescribeSnapshots.return_value = mock_snapshot_response

        with patch("tencentcloud.cvm.v20170312.cvm_client.CvmClient", return_value=mock_client):
            with patch("tencentcloud.cbs.v20170312.cbs_client.CbsClient", return_value=mock_cbs_client):
                adapter = TencentCloudVMAdapter(tencent_config)
                snapshots = adapter.list_snapshots("ins-test123")

        assert isinstance(snapshots, list)
        assert len(snapshots) == 1
        assert isinstance(snapshots[0], VMSnapshot)
        assert snapshots[0].snapshot_id == "snap-test123"
        assert snapshots[0].vm_id == "ins-test123"
        assert snapshots[0].vm_name == "test-vm"

    def test_delete_snapshot_returns_correct_structure(self, tencent_config):
        """测试腾讯云删除快照返回正确结构"""
        mock_client = Mock()
        mock_cbs_client = Mock()

        mock_response = Mock()
        mock_response.RequestId = "req-test123"
        mock_cbs_client.DeleteSnapshots.return_value = mock_response

        with patch("tencentcloud.cvm.v20170312.cvm_client.CvmClient", return_value=mock_client):
            with patch("tencentcloud.cbs.v20170312.cbs_client.CbsClient", return_value=mock_cbs_client):
                adapter = TencentCloudVMAdapter(tencent_config)
                result = adapter.delete_snapshot("snap-test123")

        assert isinstance(result, bool)
        assert result is True

    def test_restore_snapshot_returns_correct_structure(self, tencent_config):
        """测试腾讯云恢复快照返回正确结构"""
        mock_client = Mock()
        mock_cbs_client = Mock()

        mock_snapshot_response = Mock()
        snapshot_data = Mock()
        snapshot_data.SnapshotId = "snap-test123"
        snapshot_data.DiskId = "disk-test123"
        snapshot_data.Status = "NORMAL"
        snapshot_data.SnapshotName = "test-snapshot"
        snapshot_data.SnapshotDescription = "测试快照"
        snapshot_data.CreateTime = "2024-01-01T00:00:00Z"
        snapshot_data.Size = 40
        mock_snapshot_response.SnapshotSet = [snapshot_data]
        mock_cbs_client.DescribeSnapshots.return_value = mock_snapshot_response

        mock_disk_response = Mock()
        mock_disk_response.DiskIds = ["disk-restored123"]
        mock_cbs_client.CreateDisks.return_value = mock_disk_response

        mock_attach_response = Mock()
        mock_client.AttachDisks.return_value = mock_attach_response

        with patch("tencentcloud.cvm.v20170312.cvm_client.CvmClient", return_value=mock_client):
            with patch("tencentcloud.cbs.v20170312.cbs_client.CbsClient", return_value=mock_cbs_client):
                adapter = TencentCloudVMAdapter(tencent_config)
                result = adapter.restore_snapshot("ins-test123", "snap-test123")

        assert isinstance(result, bool)
        assert result is True

    def test_get_vm_info_returns_correct_structure(self, tencent_config):
        """测试腾讯云获取虚拟机信息返回正确结构"""
        mock_client = Mock()

        mock_response = Mock()
        instance_data = Mock()
        instance_data.InstanceId = "ins-test123"
        instance_data.InstanceName = "test-vm"
        instance_data.InstanceState = "RUNNING"
        instance_data.InstanceType = "S6.LARGE8"
        instance_data.Placement = Mock(Zone="ap-beijing-1")
        instance_data.PrivateIpAddresses = ["10.0.0.1"]
        instance_data.PublicIpAddresses = ["1.2.3.4"]
        instance_data.CreatedTime = "2024-01-01T00:00:00Z"
        instance_data.SystemDisk = Mock(DiskId="disk-test123")
        instance_data.DataDisks = []
        mock_response.InstanceSet = [instance_data]
        mock_client.DescribeInstances.return_value = mock_response

        with patch("tencentcloud.cvm.v20170312.cvm_client.CvmClient", return_value=mock_client):
            adapter = TencentCloudVMAdapter(tencent_config)
            vm_info = adapter.get_vm_info("ins-test123")

        assert isinstance(vm_info, VMInfo)
        assert vm_info.vm_id == "ins-test123"
        assert vm_info.name == "test-vm"
        assert vm_info.status == "RUNNING"
        assert vm_info.instance_type == "S6.LARGE8"
        assert vm_info.region == "ap-beijing"
        assert vm_info.zone == "ap-beijing-1"
        assert vm_info.private_ip == "10.0.0.1"
        assert vm_info.public_ip == "1.2.3.4"
        assert vm_info.created_at == "2024-01-01T00:00:00Z"
        assert vm_info.disk_ids == ["disk-test123"]


class TestAWSVMAdapter:
    """AWS适配器测试"""

    @pytest.fixture
    def aws_config(self):
        """AWS配置fixture"""
        return CloudVMConfig(
            provider=CloudProvider.AWS,
            region="us-east-1",
            access_key="test-access-key",
            secret_key="test-secret-key",
        )

    @patch("boto3.client")
    def test_create_snapshot_returns_correct_structure(self, mock_boto3_client, aws_config):
        """测试AWS创建快照返回正确结构"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        mock_vm_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-test123",
                            "InstanceType": "t3.large",
                            "State": {"Name": "running"},
                            "Placement": {"AvailabilityZone": "us-east-1a"},
                            "PrivateIpAddress": "10.0.0.1",
                            "PublicIpAddress": "1.2.3.4",
                            "LaunchTime": Mock(isoformat=Mock(return_value="2024-01-01T00:00:00Z")),
                            "BlockDeviceMappings": [
                                {"Ebs": {"VolumeId": "vol-test123"}}
                            ],
                            "Tags": [{"Key": "Name", "Value": "test-vm"}],
                        }
                    ]
                }
            ]
        }
        mock_client.describe_instances.return_value = mock_vm_response

        mock_snapshot_response = {
            "SnapshotId": "snap-test123",
        }
        mock_client.create_snapshot.return_value = mock_snapshot_response

        adapter = AWSVMAdapter(aws_config)
        snapshot = adapter.create_snapshot("i-test123", "test-snapshot", "测试快照")

        assert isinstance(snapshot, VMSnapshot)
        assert snapshot.snapshot_id == "snap-test123"
        assert snapshot.name == "test-snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.vm_id == "i-test123"
        assert snapshot.vm_name == "test-vm"
        assert snapshot.status == SnapshotStatus.CREATING
        assert snapshot.disk_id == "vol-test123"

    @patch("boto3.client")
    def test_get_snapshot_returns_correct_structure(self, mock_boto3_client, aws_config):
        """测试AWS获取快照返回正确结构"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        mock_response = {
            "Snapshots": [
                {
                    "SnapshotId": "snap-test123",
                    "Description": "测试快照",
                    "StartTime": Mock(isoformat=Mock(return_value="2024-01-01T00:00:00Z")),
                    "VolumeSize": 40,
                    "VolumeId": "vol-test123",
                    "State": "completed",
                    "Tags": [{"Key": "Name", "Value": "test-snapshot"}],
                }
            ]
        }
        mock_client.describe_snapshots.return_value = mock_response

        adapter = AWSVMAdapter(aws_config)
        snapshot = adapter.get_snapshot("snap-test123")

        assert isinstance(snapshot, VMSnapshot)
        assert snapshot.snapshot_id == "snap-test123"
        assert snapshot.name == "test-snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.created_at == "2024-01-01T00:00:00Z"
        assert snapshot.size == 40 * 1024 * 1024
        assert snapshot.disk_id == "vol-test123"
        assert snapshot.status == SnapshotStatus.COMPLETED

    @patch("boto3.client")
    def test_list_snapshots_returns_correct_structure(self, mock_boto3_client, aws_config):
        """测试AWS列出快照返回正确结构"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        mock_vm_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-test123",
                            "InstanceType": "t3.large",
                            "State": {"Name": "running"},
                            "Placement": {"AvailabilityZone": "us-east-1a"},
                            "BlockDeviceMappings": [
                                {"Ebs": {"VolumeId": "vol-test123"}}
                            ],
                            "Tags": [{"Key": "Name", "Value": "test-vm"}],
                        }
                    ]
                }
            ]
        }
        mock_client.describe_instances.return_value = mock_vm_response

        mock_snapshot_response = {
            "Snapshots": [
                {
                    "SnapshotId": "snap-test123",
                    "Description": "测试快照",
                    "StartTime": Mock(isoformat=Mock(return_value="2024-01-01T00:00:00Z")),
                    "VolumeSize": 40,
                    "VolumeId": "vol-test123",
                    "State": "completed",
                    "Tags": [{"Key": "Name", "Value": "test-snapshot"}],
                }
            ]
        }
        mock_client.describe_snapshots.return_value = mock_snapshot_response

        adapter = AWSVMAdapter(aws_config)
        snapshots = adapter.list_snapshots("i-test123")

        assert isinstance(snapshots, list)
        assert len(snapshots) == 1
        assert isinstance(snapshots[0], VMSnapshot)
        assert snapshots[0].snapshot_id == "snap-test123"
        assert snapshots[0].vm_id == "i-test123"
        assert snapshots[0].vm_name == "test-vm"

    @patch("boto3.client")
    def test_delete_snapshot_returns_correct_structure(self, mock_boto3_client, aws_config):
        """测试AWS删除快照返回正确结构"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        mock_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_client.delete_snapshot.return_value = mock_response

        adapter = AWSVMAdapter(aws_config)
        result = adapter.delete_snapshot("snap-test123")

        assert isinstance(result, bool)
        assert result is True

    @patch("boto3.client")
    def test_restore_snapshot_returns_correct_structure(self, mock_boto3_client, aws_config):
        """测试AWS恢复快照返回正确结构"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        mock_snapshot_response = {
            "Snapshots": [
                {
                    "SnapshotId": "snap-test123",
                    "VolumeId": "vol-test123",
                    "State": "completed",
                }
            ]
        }
        mock_client.describe_snapshots.return_value = mock_snapshot_response

        mock_vm_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-test123",
                            "InstanceType": "t3.large",
                            "State": {"Name": "running"},
                            "Placement": {"AvailabilityZone": "us-east-1a"},
                        }
                    ]
                }
            ]
        }
        mock_client.describe_instances.return_value = mock_vm_response

        mock_volume_response = {
            "VolumeId": "vol-restored123",
        }
        mock_client.create_volume.return_value = mock_volume_response

        mock_attach_response = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        mock_client.attach_volume.return_value = mock_attach_response

        adapter = AWSVMAdapter(aws_config)
        result = adapter.restore_snapshot("i-test123", "snap-test123")

        assert isinstance(result, bool)
        assert result is True

    @patch("boto3.client")
    def test_get_vm_info_returns_correct_structure(self, mock_boto3_client, aws_config):
        """测试AWS获取虚拟机信息返回正确结构"""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        mock_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-test123",
                            "InstanceType": "t3.large",
                            "State": {"Name": "running"},
                            "Placement": {"AvailabilityZone": "us-east-1a"},
                            "PrivateIpAddress": "10.0.0.1",
                            "PublicIpAddress": "1.2.3.4",
                            "LaunchTime": Mock(isoformat=Mock(return_value="2024-01-01T00:00:00Z")),
                            "BlockDeviceMappings": [
                                {"Ebs": {"VolumeId": "vol-test123"}}
                            ],
                            "Tags": [{"Key": "Name", "Value": "test-vm"}],
                        }
                    ]
                }
            ]
        }
        mock_client.describe_instances.return_value = mock_response

        adapter = AWSVMAdapter(aws_config)
        vm_info = adapter.get_vm_info("i-test123")

        assert isinstance(vm_info, VMInfo)
        assert vm_info.vm_id == "i-test123"
        assert vm_info.name == "test-vm"
        assert vm_info.status == "running"
        assert vm_info.instance_type == "t3.large"
        assert vm_info.region == "us-east-1"
        assert vm_info.zone == "us-east-1a"
        assert vm_info.private_ip == "10.0.0.1"
        assert vm_info.public_ip == "1.2.3.4"
        assert vm_info.created_at == "2024-01-01T00:00:00Z"
        assert vm_info.disk_ids == ["vol-test123"]


class TestCloudVMManager:
    """CloudVMManager统一管理类测试"""

    def test_manager_selects_correct_adapter(self):
        """测试管理器选择正确的适配器"""
        aliyun_config = CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(aliyun_config)
        assert isinstance(manager.adapter, AliyunVMAdapter)

        tencent_config = CloudVMConfig(
            provider=CloudProvider.TENCENT_CLOUD,
            region="ap-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(tencent_config)
        assert isinstance(manager.adapter, TencentCloudVMAdapter)

        aws_config = CloudVMConfig(
            provider=CloudProvider.AWS,
            region="us-east-1",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(aws_config)
        assert isinstance(manager.adapter, AWSVMAdapter)

    def test_manager_raises_for_unsupported_provider(self):
        """测试管理器对不支持的云服务商抛出异常"""
        with pytest.raises(Exception) as exc_info:
            CloudVMManager(
                CloudVMConfig(
                    provider="unknown",
                    region="test",
                    access_key="test",
                    secret_key="test",
                )
            )
        assert "unknown" in str(exc_info.value)

    @patch("ai_llm_agent_crawler.cloud_vm_manager.AliyunVMAdapter")
    def test_manager_delegates_create_snapshot(self, mock_adapter_class):
        """测试管理器委托创建快照"""
        mock_adapter = Mock()
        mock_adapter.create_snapshot.return_value = VMSnapshot(
            snapshot_id="snap-test123",
            name="test-snapshot",
            vm_id="i-test123",
        )
        mock_adapter_class.return_value = mock_adapter

        config = CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(config)

        result = manager.create_snapshot("i-test123", "test-snapshot", "测试描述")

        mock_adapter.create_snapshot.assert_called_once_with(
            "i-test123", "test-snapshot", "测试描述"
        )
        assert isinstance(result, VMSnapshot)

    @patch("ai_llm_agent_crawler.cloud_vm_manager.AliyunVMAdapter")
    def test_manager_delegates_get_snapshot(self, mock_adapter_class):
        """测试管理器委托获取快照"""
        mock_adapter = Mock()
        mock_adapter.get_snapshot.return_value = VMSnapshot(
            snapshot_id="snap-test123",
            name="test-snapshot",
            vm_id="i-test123",
        )
        mock_adapter_class.return_value = mock_adapter

        config = CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(config)

        result = manager.get_snapshot("snap-test123")

        mock_adapter.get_snapshot.assert_called_once_with("snap-test123")
        assert isinstance(result, VMSnapshot)

    @patch("ai_llm_agent_crawler.cloud_vm_manager.AliyunVMAdapter")
    def test_manager_delegates_list_snapshots(self, mock_adapter_class):
        """测试管理器委托列出快照"""
        mock_adapter = Mock()
        mock_adapter.list_snapshots.return_value = [
            VMSnapshot(
                snapshot_id="snap-test123",
                name="test-snapshot",
                vm_id="i-test123",
            )
        ]
        mock_adapter_class.return_value = mock_adapter

        config = CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(config)

        result = manager.list_snapshots("i-test123")

        mock_adapter.list_snapshots.assert_called_once_with("i-test123")
        assert isinstance(result, list)
        assert len(result) == 1

    @patch("ai_llm_agent_crawler.cloud_vm_manager.AliyunVMAdapter")
    def test_manager_delegates_delete_snapshot(self, mock_adapter_class):
        """测试管理器委托删除快照"""
        mock_adapter = Mock()
        mock_adapter.delete_snapshot.return_value = True
        mock_adapter_class.return_value = mock_adapter

        config = CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(config)

        result = manager.delete_snapshot("snap-test123")

        mock_adapter.delete_snapshot.assert_called_once_with("snap-test123")
        assert result is True

    @patch("ai_llm_agent_crawler.cloud_vm_manager.AliyunVMAdapter")
    def test_manager_delegates_restore_snapshot(self, mock_adapter_class):
        """测试管理器委托恢复快照"""
        mock_adapter = Mock()
        mock_adapter.restore_snapshot.return_value = True
        mock_adapter_class.return_value = mock_adapter

        config = CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(config)

        result = manager.restore_snapshot("i-test123", "snap-test123")

        mock_adapter.restore_snapshot.assert_called_once_with("i-test123", "snap-test123")
        assert result is True

    @patch("ai_llm_agent_crawler.cloud_vm_manager.AliyunVMAdapter")
    def test_manager_delegates_get_vm_info(self, mock_adapter_class):
        """测试管理器委托获取虚拟机信息"""
        mock_adapter = Mock()
        mock_adapter.get_vm_info.return_value = VMInfo(
            vm_id="i-test123",
            name="test-vm",
        )
        mock_adapter_class.return_value = mock_adapter

        config = CloudVMConfig(
            provider=CloudProvider.ALIYUN,
            region="cn-beijing",
            access_key="test",
            secret_key="test",
        )
        manager = CloudVMManager(config)

        result = manager.get_vm_info("i-test123")

        mock_adapter.get_vm_info.assert_called_once_with("i-test123")
        assert isinstance(result, VMInfo)