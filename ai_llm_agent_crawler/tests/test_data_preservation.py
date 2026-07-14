"""
数据保全模块单元测试
"""

import pytest
from pathlib import Path

from ai_llm_agent_crawler.data_preservation import (
    GitManager,
    CherryTreeManager,
    DataIntegrityChecker,
    DataPreservationManager,
)


class TestGitManager:
    """GitManager类测试"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """设置测试环境"""
        self.repo_path = tmp_path / "test_repo"
        self.git_manager = GitManager(self.repo_path)

    def test_init_repo(self):
        """测试初始化仓库"""
        result = self.git_manager.init_repo()
        assert result is True
        assert (self.repo_path / ".git").exists()

    def test_add_files(self):
        """测试添加文件"""
        self.git_manager.init_repo()
        
        test_file = self.repo_path / "test.txt"
        test_file.write_text("Test content")
        
        result = self.git_manager.add_files("test.txt")
        assert result is True

    def test_commit_returns_hash(self):
        """测试Git提交操作成功，返回commit hash"""
        self.git_manager.init_repo()
        
        test_file = self.repo_path / "test.txt"
        test_file.write_text("Test content")
        
        self.git_manager.add_files(".")
        commit_hash = self.git_manager.commit("Initial commit")
        
        assert commit_hash is not None
        assert len(commit_hash) == 40
        assert commit_hash.isalnum()

    def test_get_status(self):
        """测试获取仓库状态"""
        self.git_manager.init_repo()
        
        test_file = self.repo_path / "test.txt"
        test_file.write_text("Test content")
        
        self.git_manager.add_files(".")
        self.git_manager.commit("Test commit")
        
        status = self.git_manager.get_status()
        
        assert "branch" in status
        assert "commit" in status
        assert "dirty" in status
        assert status["dirty"] is False

    def test_get_commit_history(self):
        """测试获取提交历史"""
        self.git_manager.init_repo()
        
        test_file = self.repo_path / "test.txt"
        test_file.write_text("First content")
        self.git_manager.add_files(".")
        self.git_manager.commit("First commit")
        
        test_file.write_text("Second content")
        self.git_manager.add_files(".")
        self.git_manager.commit("Second commit")
        
        history = self.git_manager.get_commit_history(limit=5)
        
        assert len(history) == 2
        assert history[0]["message"] == "Second commit"
        assert history[1]["message"] == "First commit"


class TestCherryTreeManager:
    """CherryTreeManager类测试"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """设置测试环境"""
        self.ct_path = tmp_path / "knowledge.ctb"
        self.cherrytree_manager = CherryTreeManager(self.ct_path)

    def test_export_to_file_xml(self, tmp_path):
        """测试导出到XML文件"""
        output_path = tmp_path / "output" / "exported.xml"
        result = self.cherrytree_manager.export_to_file(output_path, format="xml")
        
        assert result is True
        assert output_path.exists()
        content = output_path.read_text()
        assert "<cherrytree>" in content

    def test_export_to_file_json(self, tmp_path):
        """测试导出到JSON文件"""
        output_path = tmp_path / "output" / "exported.json"
        result = self.cherrytree_manager.export_to_file(output_path, format="json")
        
        assert result is True
        assert output_path.exists()

    def test_export_to_file_text(self, tmp_path):
        """测试导出到文本文件"""
        output_path = tmp_path / "output" / "exported.txt"
        result = self.cherrytree_manager.export_to_file(output_path, format="text")
        
        assert result is True
        assert output_path.exists()

    def test_import_from_file(self, tmp_path):
        """测试从文件导入"""
        input_path = tmp_path / "input.xml"
        input_path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<cherrytree>\n</cherrytree>')
        
        result = self.cherrytree_manager.import_from_file(input_path, format="xml")
        
        assert result is True

    def test_sync_completes(self, tmp_path):
        """测试CherryTree文件同步完成"""
        source_file = self.ct_path
        source_file.write_text("Test CherryTree content")
        
        target_path = tmp_path / "sync_target" / "knowledge.ctb"
        
        result = self.cherrytree_manager.sync(target_path)
        
        assert result is True
        assert target_path.exists()
        assert target_path.read_text() == "Test CherryTree content"

    def test_backup(self, tmp_path):
        """测试备份文档"""
        source_file = self.ct_path
        source_file.write_text("Test CherryTree content")
        
        backup_dir = tmp_path / "backups"
        
        backup_path = self.cherrytree_manager.backup(backup_dir)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert "knowledge_" in backup_path.name
        assert backup_path.suffix == ".ctb"


class TestDataIntegrityChecker:
    """DataIntegrityChecker类测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.checker = DataIntegrityChecker(algorithm="sha256")

    def test_calculate_checksum(self, tmp_path):
        """测试计算文件校验和"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for checksum")
        
        checksum = self.checker.calculate_checksum(test_file)
        
        assert checksum is not None
        assert len(checksum) == 64
        assert checksum.isalnum()

    def test_verify_checksum_correct(self, tmp_path):
        """测试验证正确的校验和"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        checksum = self.checker.calculate_checksum(test_file)
        result = self.checker.verify_checksum(test_file, checksum)
        
        assert result is True

    def test_verify_checksum_incorrect(self, tmp_path):
        """测试验证错误的校验和"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        result = self.checker.verify_checksum(test_file, "wrong_checksum_1234567890")
        
        assert result is False

    def test_data_integrity_check_returns_correct_result(self, tmp_path):
        """测试数据完整性校验返回正确结果"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        (test_dir / "file1.txt").write_text("Content 1")
        (test_dir / "file2.txt").write_text("Content 2")
        (test_dir / "subdir").mkdir()
        (test_dir / "subdir" / "file3.txt").write_text("Content 3")
        
        result = self.checker.check_directory_integrity(test_dir)
        
        assert "directory" in result
        assert "total_files" in result
        assert "checksums" in result
        assert "errors" in result
        assert result["total_files"] == 3
        assert len(result["errors"]) == 0

    def test_generate_manifest(self, tmp_path):
        """测试生成完整性清单"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("Content")
        
        manifest_path = tmp_path / "manifest.json"
        
        result = self.checker.generate_manifest(test_dir, manifest_path)
        
        assert result is True
        assert manifest_path.exists()


class TestDataPreservationManager:
    """DataPreservationManager类测试"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """设置测试环境"""
        self.tmp_path = tmp_path
        self.backup_dir = tmp_path / "backups"
        self.source_dir = tmp_path / "source_data"
        self.source_dir.mkdir()
        (self.source_dir / "data1.txt").write_text("Test data")
        (self.source_dir / "data2.txt").write_text("More data")

    def test_backup(self):
        """测试完整数据保全备份"""
        git_manager = GitManager(self.backup_dir)
        git_manager.init_repo()
        
        cherrytree_manager = CherryTreeManager(self.tmp_path / "knowledge.ctb")
        
        manager = DataPreservationManager(
            git_manager=git_manager,
            cherrytree_manager=cherrytree_manager,
            backup_dir=self.backup_dir,
        )
        
        result = manager.backup(self.source_dir, description="Test backup")
        
        assert result["success"] is True
        assert "backup_path" in result
        assert "steps" in result

    def test_restore(self):
        """测试数据恢复"""
        git_manager = GitManager(self.tmp_path / "repo")
        git_manager.init_repo()
        
        cherrytree_manager = CherryTreeManager(self.tmp_path / "knowledge.ctb")
        
        manager = DataPreservationManager(
            git_manager=git_manager,
            cherrytree_manager=cherrytree_manager,
            backup_dir=self.backup_dir,
        )
        
        backup_result = manager.backup(self.source_dir)
        backup_path = Path(backup_result["backup_path"])
        
        target_dir = self.tmp_path / "restored"
        
        restore_result = manager.restore(backup_path, target_dir)
        
        assert restore_result["success"] is True
        assert (target_dir / "data1.txt").exists()
        assert (target_dir / "data2.txt").exists()

    def test_verify_with_manifest(self, tmp_path):
        """测试使用清单验证数据完整性"""
        checker = DataIntegrityChecker()
        test_dir = tmp_path / "verify_test"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("Verification test")
        
        manifest_path = tmp_path / "manifest.json"
        checker.generate_manifest(test_dir, manifest_path)
        
        manager = DataPreservationManager(integrity_checker=checker)
        
        result = manager.verify(data_dir=test_dir, manifest_path=manifest_path)
        
        assert result is True

    def test_verify_without_manifest(self, tmp_path):
        """测试不使用清单验证数据完整性"""
        test_dir = tmp_path / "verify_test"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("Verification test")
        
        manager = DataPreservationManager()
        
        result = manager.verify(data_dir=test_dir)
        
        assert result is True