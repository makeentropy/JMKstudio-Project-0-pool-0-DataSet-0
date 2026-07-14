"""
容器管理器单元测试

使用mock测试Docker容器镜像导出/导入、容器状态快照等功能。
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

from ai_llm_agent_crawler.container_manager import (
    ContainerConfig,
    ContainerStatus,
    SnapshotStatus,
    ContainerSnapshot,
    ContainerManager,
)


class TestContainerConfig:
    """ContainerConfig类测试"""

    def test_init_default(self):
        """测试默认配置初始化"""
        config = ContainerConfig()

        assert config.base_url == "unix:///var/run/docker.sock"
        assert config.timeout == 60
        assert config.tls is False
        assert config.tls_ca_cert is None
        assert config.tls_cert is None
        assert config.tls_key is None
        assert config.max_pool_size == 10

    def test_init_custom(self):
        """测试自定义配置初始化"""
        config = ContainerConfig(
            base_url="tcp://192.168.1.1:2376",
            timeout=120,
            tls=True,
            tls_ca_cert="/path/ca.pem",
            tls_cert="/path/cert.pem",
            tls_key="/path/key.pem",
            max_pool_size=20,
        )

        assert config.base_url == "tcp://192.168.1.1:2376"
        assert config.timeout == 120
        assert config.tls is True
        assert config.tls_ca_cert == "/path/ca.pem"
        assert config.tls_cert == "/path/cert.pem"
        assert config.tls_key == "/path/key.pem"
        assert config.max_pool_size == 20


class TestContainerSnapshot:
    """ContainerSnapshot类测试"""

    def test_init(self):
        """测试初始化"""
        snapshot = ContainerSnapshot(
            snapshot_id="snap_20240101000000_abc123",
            name="test_snapshot",
            description="测试快照",
            container_id="container123",
            container_name="test_container",
            container_status="running",
            image_id="image123",
            image_name="nginx",
            image_tag="latest",
        )

        assert snapshot.snapshot_id == "snap_20240101000000_abc123"
        assert snapshot.name == "test_snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.container_id == "container123"
        assert snapshot.container_name == "test_container"
        assert snapshot.container_status == "running"
        assert snapshot.image_id == "image123"
        assert snapshot.image_name == "nginx"
        assert snapshot.image_tag == "latest"
        assert snapshot.status == SnapshotStatus.COMPLETED
        assert snapshot.labels == {}
        assert snapshot.metadata == {}

    def test_snapshot_contains_complete_info(self):
        """测试容器状态快照包含完整信息"""
        snapshot = ContainerSnapshot(
            snapshot_id="snap_20240101000000_abc123",
            name="test_snapshot",
            description="测试容器状态快照",
            container_id="container123",
            container_name="test_container",
            container_status="running",
            image_id="sha256:1234567890abcdef1234567890abcdef",
            image_name="nginx",
            image_tag="1.24",
            status=SnapshotStatus.COMPLETED,
            snapshot_path=Path("/tmp/snapshot.tar"),
            size=1024 * 1024,
            checksum="abc123def456",
            labels={"app": "test", "env": "dev"},
            metadata={"version": "1.0"},
        )

        assert hasattr(snapshot, "snapshot_id")
        assert hasattr(snapshot, "name")
        assert hasattr(snapshot, "description")
        assert hasattr(snapshot, "created_at")
        assert hasattr(snapshot, "size")
        assert hasattr(snapshot, "container_id")
        assert hasattr(snapshot, "container_name")
        assert hasattr(snapshot, "container_status")
        assert hasattr(snapshot, "image_id")
        assert hasattr(snapshot, "image_name")
        assert hasattr(snapshot, "image_tag")
        assert hasattr(snapshot, "status")
        assert hasattr(snapshot, "snapshot_path")
        assert hasattr(snapshot, "checksum")
        assert hasattr(snapshot, "labels")
        assert hasattr(snapshot, "metadata")

        assert snapshot.container_id == "container123"
        assert snapshot.image_name == "nginx"
        assert snapshot.image_tag == "1.24"
        assert snapshot.status == SnapshotStatus.COMPLETED
        assert snapshot.size == 1048576
        assert snapshot.labels == {"app": "test", "env": "dev"}


class TestContainerManager:
    """ContainerManager类测试"""

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_init(self, mock_docker):
        """测试初始化"""
        mock_client = Mock()
        mock_client.ping.return_value = None
        mock_docker.from_env.return_value = mock_client

        manager = ContainerManager()

        assert manager.config is not None
        assert manager.config.base_url == "unix:///var/run/docker.sock"

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_save_image_success(self, mock_docker, tmp_path):
        """测试镜像导出成功，生成tar文件"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_image = Mock()
        mock_image.save.return_value = [b"tar_content"]
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_client.images.get.return_value = mock_image

        manager = ContainerManager()

        output_path = tmp_path / "test_image.tar"
        result = manager.save_image("nginx:latest", output_path)

        assert result == output_path.resolve()
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        mock_client.images.get.assert_called_once_with("nginx:latest")

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_save_image_not_found(self, mock_docker):
        """测试导出不存在的镜像"""
        from docker.errors import NotFound

        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None
        mock_client.images.get.side_effect = NotFound("Image not found")

        manager = ContainerManager()

        with pytest.raises(RuntimeError, match="镜像不存在"):
            manager.save_image("nonexistent:latest", "/tmp/test.tar")

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_load_image_success(self, mock_docker, tmp_path):
        """测试镜像导入成功"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_load_result = [{"id": "sha256:abc123", "tags": ["nginx:imported"]}]
        mock_client.images.load.return_value = iter(mock_load_result)

        tar_path = tmp_path / "test_image.tar"
        with open(tar_path, "wb") as f:
            f.write(b"tar_content")

        manager = ContainerManager()
        result = manager.load_image(tar_path)

        assert len(result) == 1
        assert result[0]["id"] == "sha256:abc123"
        assert "nginx:imported" in result[0]["tags"]
        mock_client.images.load.assert_called_once()

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_load_image_not_found(self, mock_docker):
        """测试导入不存在的tar文件"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        manager = ContainerManager()

        with pytest.raises(FileNotFoundError):
            manager.load_image("/nonexistent/file.tar")

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_create_container_snapshot_success(self, mock_docker, tmp_path):
        """测试容器状态快照包含完整信息"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_container = Mock()
        mock_container.id = "container_abc123"
        mock_container.name = "/test_container"
        mock_container.status = "running"
        mock_container.labels = {"app": "test"}
        mock_container.attrs = {
            "Image": "sha256:image_abc123",
            "Config": {"Image": "nginx:latest"},
        }
        mock_client.containers.get.return_value = mock_container

        mock_image = Mock()
        mock_image.save.return_value = [b"tar_content"]
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_client.images.get.return_value = mock_image

        manager = ContainerManager()

        snapshot = manager.create_container_snapshot(
            "test_container",
            "test_snapshot",
            description="测试快照",
            output_dir=tmp_path,
        )

        assert snapshot.snapshot_id.startswith("snap_")
        assert snapshot.name == "test_snapshot"
        assert snapshot.description == "测试快照"
        assert snapshot.container_id == "container_abc123"
        assert snapshot.container_name == "/test_container"
        assert snapshot.container_status == "running"
        assert snapshot.image_id == "sha256:image_abc123"
        assert snapshot.image_name == "nginx"
        assert snapshot.image_tag == "latest"
        assert snapshot.status == SnapshotStatus.COMPLETED
        assert snapshot.snapshot_path.exists()
        assert snapshot.size > 0
        assert snapshot.checksum != ""
        assert snapshot.labels == {"app": "test"}

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_create_container_snapshot_container_not_found(self, mock_docker):
        """测试创建快照时容器不存在"""
        from docker.errors import NotFound

        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None
        mock_client.containers.get.side_effect = NotFound("Container not found")

        manager = ContainerManager()

        with pytest.raises(RuntimeError, match="容器不存在"):
            manager.create_container_snapshot("nonexistent", "test_snapshot")

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_list_containers(self, mock_docker):
        """测试列出容器"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_container = Mock()
        mock_container.id = "container_abc123"
        mock_container.name = "/test_container"
        mock_container.status = "running"
        mock_container.labels = {"app": "test"}
        mock_container.attrs = {
            "Config": {"Image": "nginx:latest"},
            "Image": "sha256:image_abc123",
            "Created": "2024-01-01T00:00:00Z",
            "NetworkSettings": {"Ports": {"80/tcp": None}},
        }
        mock_client.containers.list.return_value = [mock_container]

        manager = ContainerManager()
        containers = manager.list_containers()

        assert len(containers) == 1
        assert containers[0]["id"] == "container_abc123"
        assert containers[0]["name"] == "/test_container"
        assert containers[0]["status"] == "running"
        assert containers[0]["image"] == "nginx:latest"

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_list_images(self, mock_docker):
        """测试列出镜像"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_image = Mock()
        mock_image.id = "sha256:image_abc123"
        mock_image.tags = ["nginx:latest"]
        mock_image.attrs = {
            "Created": "2024-01-01T00:00:00Z",
            "Size": 1048576,
            "VirtualSize": 2097152,
        }
        mock_client.images.list.return_value = [mock_image]

        manager = ContainerManager()
        images = manager.list_images()

        assert len(images) == 1
        assert images[0]["id"] == "sha256:image_abc123"
        assert "nginx:latest" in images[0]["tags"]
        assert images[0]["size"] == 1048576

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_start_container(self, mock_docker):
        """测试启动容器"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container

        manager = ContainerManager()
        result = manager.start_container("test_container")

        assert result is True
        mock_container.start.assert_called_once()

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_stop_container(self, mock_docker):
        """测试停止容器"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container

        manager = ContainerManager()
        result = manager.stop_container("test_container", timeout=5)

        assert result is True
        mock_container.stop.assert_called_once_with(timeout=5)

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_restart_container(self, mock_docker):
        """测试重启容器"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container

        manager = ContainerManager()
        result = manager.restart_container("test_container", timeout=5)

        assert result is True
        mock_container.restart.assert_called_once_with(timeout=5)

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_remove_container(self, mock_docker):
        """测试删除容器"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container

        manager = ContainerManager()
        result = manager.remove_container("test_container", force=True)

        assert result is True
        mock_container.remove.assert_called_once_with(force=True)

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_get_container_info(self, mock_docker):
        """测试获取容器信息"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_container = Mock()
        mock_container.attrs = {"Id": "container_abc123", "Name": "/test_container"}
        mock_client.containers.get.return_value = mock_container

        manager = ContainerManager()
        info = manager.get_container_info("test_container")

        assert info["Id"] == "container_abc123"
        assert info["Name"] == "/test_container"

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_close(self, mock_docker):
        """测试关闭客户端"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        manager = ContainerManager()
        _ = manager.client
        manager.close()

        mock_client.close.assert_called_once()

    @patch("ai_llm_agent_crawler.container_manager.docker")
    def test_restore_container_snapshot_success(self, mock_docker, tmp_path):
        """测试从快照恢复容器"""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        mock_load_result = [{"id": "sha256:abc123", "tags": ["nginx:latest"]}]
        mock_client.images.load.return_value = iter(mock_load_result)

        mock_container = Mock()
        mock_container.id = "restored_container_abc123"
        mock_container.attrs = {"Id": "restored_container_abc123", "Name": "/restored_container"}
        mock_client.containers.run.return_value = mock_container

        snapshot_path = tmp_path / "snapshot.tar"
        with open(snapshot_path, "wb") as f:
            f.write(b"tar_content")

        snapshot = ContainerSnapshot(
            snapshot_id="snap_20240101000000_abc123",
            name="test_snapshot",
            container_id="container_abc123",
            image_name="nginx",
            image_tag="latest",
            snapshot_path=snapshot_path,
            labels={"app": "test"},
        )

        manager = ContainerManager()
        result = manager.restore_container_snapshot(snapshot, "restored_container")

        assert result["Id"] == "restored_container_abc123"
        assert result["Name"] == "/restored_container"
        mock_client.containers.run.assert_called_once_with(
            "nginx", name="restored_container", detach=True, labels={"app": "test"}
        )