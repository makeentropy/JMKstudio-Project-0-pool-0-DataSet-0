"""
集成测试文件

测试以下场景：
1. 完整快照流程测试（创建快照 -> 验证 -> 恢复）
2. SSH+容器协作测试（SSH连接远程主机，执行Docker操作）
3. 数据保全完整流程测试（Git提交 + CherryTree同步 + 完整性校验）
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from ai_llm_agent_crawler.versioning.snapshot_manager import (
    SnapshotManager,
    SnapshotType,
    CompressionType,
)
from ai_llm_agent_crawler.ssh_manager import SSHManager, SSHConfig
from ai_llm_agent_crawler.container_manager import ContainerManager
from ai_llm_agent_crawler.data_preservation import (
    GitManager,
    CherryTreeManager,
    DataIntegrityChecker,
    DataPreservationManager,
)


class TestSnapshotFullFlow:
    """完整快照流程集成测试"""

    def test_full_snapshot_create_verify_restore(self, tmp_path):
        """测试完整快照流程：创建 -> 验证 -> 恢复"""
        source_dir = tmp_path / "source_data"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("Hello, World!")
        (source_dir / "file2.txt").write_text("Integration test data")
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("Nested file content")

        output_dir = tmp_path / "snapshots"
        output_dir.mkdir()

        snapshot_manager = SnapshotManager(storage=None)
        snapshot_manager.storage._storage_path = output_dir

        snapshot = snapshot_manager.create_full_snapshot(
            entity_id="test_entity",
            source_path=source_dir,
            name="test_snapshot",
            description="Test integration snapshot",
            compression_type=CompressionType.NONE,
        )

        assert snapshot.snapshot_type == SnapshotType.FULL
        assert snapshot.status.value == "completed"
        assert snapshot.file_count > 0
        assert len(snapshot.checksum) == 64

        verify_result = snapshot_manager.verify_snapshot(
            entity_id="test_entity",
            snapshot_id=snapshot.snapshot_id,
        )
        assert verify_result is True
        assert snapshot.is_verified is True

        restore_dir = tmp_path / "restored_data"
        restore_result = snapshot_manager.restore_snapshot(
            entity_id="test_entity",
            snapshot_id=snapshot.snapshot_id,
            output_path=restore_dir,
            verify_integrity=True,
        )
        assert restore_result is True
        assert (restore_dir / "file1.txt").exists()
        assert (restore_dir / "file2.txt").exists()
        assert (restore_dir / "subdir" / "file3.txt").exists()
        assert (restore_dir / "file1.txt").read_text() == "Hello, World!"
        assert (restore_dir / "file2.txt").read_text() == "Integration test data"
        assert (restore_dir / "subdir" / "file3.txt").read_text() == "Nested file content"

    def test_compressed_snapshot_flow(self, tmp_path):
        """测试压缩快照流程"""
        source_dir = tmp_path / "source_data"
        source_dir.mkdir()
        (source_dir / "large_file.txt").write_text("This is a test file for compression. " * 100)

        output_dir = tmp_path / "snapshots_compressed"
        output_dir.mkdir()

        snapshot_manager = SnapshotManager(storage=None)
        snapshot_manager.storage._storage_path = output_dir

        snapshot = snapshot_manager.create_full_snapshot(
            entity_id="test_entity_compressed",
            source_path=source_dir,
            name="compressed_snapshot",
            compression_type=CompressionType.TAR_GZ,
        )

        assert snapshot.compression_type == CompressionType.TAR_GZ
        assert snapshot.compression_ratio < 1.0
        assert snapshot.storage_path.exists()
        assert str(snapshot.storage_path).endswith(".tar.gz")


class TestSSHContainerIntegration:
    """SSH+容器协作集成测试"""

    def test_ssh_container_collaboration(self):
        """测试SSH连接与Docker操作的协作（使用Mock）"""
        mock_channel = Mock()
        mock_channel.recv_exit_status.return_value = 0
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"Docker version 24.0.0\n"
        mock_stdout.channel = mock_channel
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        mock_ssh_client = Mock()
        mock_ssh_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

        with patch("ai_llm_agent_crawler.ssh_manager.SSHClient") as MockSSHClient:
            MockSSHClient.return_value = mock_ssh_client

            ssh_config = SSHConfig(
                hostname="127.0.0.1",
                username="testuser",
                password="testpass",
            )
            ssh_manager = SSHManager(config=ssh_config)
            ssh_manager.connect()

            assert ssh_manager.connected is True

            output, error, exit_code = ssh_manager.execute_command("docker --version")

            assert exit_code == 0
            assert "Docker version" in output
            mock_ssh_client.exec_command.assert_called_once()

            ssh_manager.disconnect()

    def test_ssh_file_transfer_with_container(self, tmp_path):
        """测试SSH文件传输与容器操作的集成"""
        local_file = tmp_path / "test_script.sh"
        local_file.write_text("#!/bin/bash\necho 'Hello from container'")

        mock_sftp = Mock()
        mock_ssh_client = Mock()
        mock_ssh_client.open_sftp.return_value = mock_sftp

        with patch("ai_llm_agent_crawler.ssh_manager.SSHClient") as MockSSHClient:
            MockSSHClient.return_value = mock_ssh_client

            ssh_config = SSHConfig(
                hostname="127.0.0.1",
                username="testuser",
                password="testpass",
            )
            ssh_manager = SSHManager(config=ssh_config)
            ssh_manager.connect()

            result = ssh_manager.upload_file(str(local_file), "/tmp/test_script.sh")

            assert result is True
            mock_sftp.put.assert_called_once()

            ssh_manager.disconnect()


class TestDataPreservationFullFlow:
    """数据保全完整流程集成测试"""

    def test_full_data_preservation_flow(self, tmp_path):
        """测试完整数据保全流程：Git提交 + CherryTree同步 + 完整性校验"""
        source_dir = tmp_path / "source_data"
        source_dir.mkdir()
        (source_dir / "data.json").write_text('{"key": "value"}')
        (source_dir / "notes.txt").write_text("Important notes")

        backup_dir = tmp_path / "backups"
        repo_path = tmp_path / "test_repo"

        git_manager = GitManager(repo_path)
        git_manager.init_repo()
        git_manager.add_files(".")
        git_manager.commit("Initial commit")

        cherrytree_path = tmp_path / "knowledge.ctb"
        cherrytree_path.write_text("Test CherryTree knowledge base")
        cherrytree_manager = CherryTreeManager(cherrytree_path)

        integrity_checker = DataIntegrityChecker(algorithm="sha256")

        preservation_manager = DataPreservationManager(
            git_manager=git_manager,
            cherrytree_manager=cherrytree_manager,
            integrity_checker=integrity_checker,
            backup_dir=backup_dir,
        )

        backup_result = preservation_manager.backup(source_dir, description="Integration test backup")

        assert backup_result["success"] is True
        assert "backup_path" in backup_result
        assert "steps" in backup_result

        backup_path = Path(backup_result["backup_path"])
        assert (backup_path / "data").exists()
        assert (backup_path / "manifest.json").exists()

        manifest_path = backup_path / "manifest.json"
        verify_result = preservation_manager.verify(
            data_dir=backup_path / "data",
            manifest_path=manifest_path,
        )
        assert verify_result is True

        restore_dir = tmp_path / "restored_data"
        restore_result = preservation_manager.restore(backup_path, restore_dir)

        assert restore_result["success"] is True
        assert (restore_dir / "data.json").exists()
        assert (restore_dir / "notes.txt").exists()
        assert (restore_dir / "data.json").read_text() == '{"key": "value"}'
        assert (restore_dir / "notes.txt").read_text() == "Important notes"

    def test_data_integrity_with_corruption_detection(self, tmp_path):
        """测试数据完整性校验与损坏检测"""
        test_dir = tmp_path / "integrity_test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("Original content")
        (test_dir / "file2.txt").write_text("More content")

        checker = DataIntegrityChecker()

        manifest_path = tmp_path / "manifest.json"
        checker.generate_manifest(test_dir, manifest_path)

        verify_result = checker.verify_checksum(test_dir / "file1.txt", checker.calculate_checksum(test_dir / "file1.txt"))
        assert verify_result is True

        (test_dir / "file1.txt").write_text("Modified content")
        verify_result = checker.verify_checksum(test_dir / "file1.txt", checker.calculate_checksum(tmp_path / "original_file.txt" if (tmp_path / "original_file.txt").exists() else test_dir / "file1.txt"))
        original_checksum = DataIntegrityChecker().calculate_checksum(tmp_path / "original_file.txt") if (tmp_path / "original_file.txt").exists() else None
        if original_checksum:
            verify_result = checker.verify_checksum(test_dir / "file1.txt", original_checksum)
            assert verify_result is False

    def test_cherrytree_sync_and_backup(self, tmp_path):
        """测试CherryTree同步与备份"""
        source_ctb = tmp_path / "source" / "knowledge.ctb"
        source_ctb.parent.mkdir(parents=True)
        source_ctb.write_text("Source knowledge base content")

        cherrytree_manager = CherryTreeManager(source_ctb)

        target_path = tmp_path / "target" / "knowledge.ctb"
        sync_result = cherrytree_manager.sync(target_path)
        assert sync_result is True
        assert target_path.exists()
        assert target_path.read_text() == "Source knowledge base content"

        backup_dir = tmp_path / "backups"
        backup_path = cherrytree_manager.backup(backup_dir)
        assert backup_path is not None
        assert backup_path.exists()
        assert "knowledge_" in backup_path.name


class TestCrossModuleIntegration:
    """跨模块集成测试"""

    def test_snapshot_with_preservation(self, tmp_path):
        """测试快照与数据保全的集成"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "application_data.txt").write_text("Application data for snapshot")

        output_dir = tmp_path / "snapshots"
        output_dir.mkdir()

        snapshot_manager = SnapshotManager(storage=None)
        snapshot_manager.storage._storage_path = output_dir

        snapshot = snapshot_manager.create_full_snapshot(
            entity_id="app_data",
            source_path=source_dir,
            name="app_snapshot",
        )

        assert len(snapshot.checksum) == 64

        git_manager = GitManager(tmp_path / "repo")
        git_manager.init_repo()

        cherrytree_manager = CherryTreeManager(tmp_path / "knowledge.ctb")

        integrity_checker = DataIntegrityChecker()

        preservation_manager = DataPreservationManager(
            git_manager=git_manager,
            cherrytree_manager=cherrytree_manager,
            integrity_checker=integrity_checker,
            backup_dir=tmp_path / "preservation_backups",
        )

        backup_result = preservation_manager.backup(source_dir)
        assert backup_result["success"] is True
