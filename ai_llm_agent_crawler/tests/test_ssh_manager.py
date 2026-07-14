"""
SSH管理器单元测试

使用mock测试SSH连接管理、命令执行和文件传输功能。
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

from ai_llm_agent_crawler.ssh_manager import (
    SSHConfig,
    SSHConnection,
    SSHConnectionPool,
    SSHManager,
)


class TestSSHConfig:
    """SSHConfig类测试"""

    def test_init_with_password(self):
        """测试密码认证配置"""
        config = SSHConfig(
            hostname="192.168.1.1",
            username="admin",
            password="password123",
            port=22,
            timeout=10,
        )

        assert config.hostname == "192.168.1.1"
        assert config.username == "admin"
        assert config.password == "password123"
        assert config.private_key_path is None
        assert config.port == 22
        assert config.timeout == 10

    def test_init_with_private_key(self):
        """测试密钥认证配置"""
        config = SSHConfig(
            hostname="192.168.1.1",
            username="admin",
            private_key_path="/home/admin/.ssh/id_rsa",
            private_key_passphrase="passphrase",
        )

        assert config.private_key_path == "/home/admin/.ssh/id_rsa"
        assert config.private_key_passphrase == "passphrase"
        assert config.password is None

    def test_repr(self):
        """测试repr方法"""
        config = SSHConfig(hostname="test.com", username="user", port=2222)
        repr_str = repr(config)
        assert "test.com" in repr_str
        assert "user" in repr_str
        assert "2222" in repr_str


class TestSSHConnection:
    """SSHConnection类测试"""

    def test_init(self):
        """测试初始化"""
        config = SSHConfig(hostname="192.168.1.1", username="admin")
        conn = SSHConnection(config)

        assert conn.config == config
        assert conn.connected is False
        assert conn.client is None
        assert conn.sftp is None

    def test_connect_with_password_success(self):
        """测试密码认证连接成功"""
        config = SSHConfig(
            hostname="192.168.1.1",
            username="admin",
            password="password123",
        )
        conn = SSHConnection(config)

        with patch.object(conn, '_client') as mock_client:
            mock_client.connect.return_value = None
            conn._client = mock_client
            conn._connected = True

            assert conn.connected is True

    def test_connect_with_private_key_success(self):
        """测试密钥认证连接成功"""
        config = SSHConfig(
            hostname="192.168.1.1",
            username="admin",
            private_key_path="/home/admin/.ssh/id_rsa",
        )
        conn = SSHConnection(config)

        with patch.object(conn, '_client') as mock_client:
            mock_client.connect.return_value = None
            conn._client = mock_client
            conn._connected = True

            assert conn.connected is True

    @patch("paramiko.SSHClient")
    @patch("paramiko.AutoAddPolicy")
    def test_connect_authentication_failure(self, mock_policy, mock_ssh_client):
        """测试认证失败"""
        from paramiko.ssh_exception import AuthenticationException

        mock_client_instance = Mock()
        mock_ssh_client.return_value = mock_client_instance
        mock_client_instance.connect.side_effect = AuthenticationException(
            "Authentication failed"
        )

        config = SSHConfig(hostname="192.168.1.1", username="admin", password="wrong")
        conn = SSHConnection(config)

        result = conn.connect()

        assert result is False
        assert conn.connected is False

    @patch("paramiko.SSHClient")
    @patch("paramiko.AutoAddPolicy")
    def test_connect_timeout(self, mock_policy, mock_ssh_client):
        """测试连接超时"""
        mock_client_instance = Mock()
        mock_ssh_client.return_value = mock_client_instance
        mock_client_instance.connect.side_effect = TimeoutError("Connection timed out")

        config = SSHConfig(hostname="192.168.1.1", username="admin", timeout=1)
        conn = SSHConnection(config)

        result = conn.connect()

        assert result is False
        assert conn.connected is False

    @patch("paramiko.SSHClient")
    @patch("paramiko.AutoAddPolicy")
    def test_close(self, mock_policy, mock_ssh_client):
        """测试关闭连接"""
        mock_client_instance = Mock()
        mock_ssh_client.return_value = mock_client_instance

        config = SSHConfig(hostname="192.168.1.1", username="admin", password="pass")
        conn = SSHConnection(config)
        conn.connect()

        conn.close()

        assert conn.connected is False
        assert conn.client is None
        assert conn.sftp is None


class TestSSHConnectionPool:
    """SSHConnectionPool类测试"""

    def test_init(self):
        """测试初始化"""
        config = SSHConfig(hostname="192.168.1.1", username="admin")
        pool = SSHConnectionPool(config, max_connections=3, connection_timeout=120)

        assert pool.config == config
        assert pool.max_connections == 3
        assert pool.connection_timeout == 120
        assert len(pool._connections) == 0

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_acquire_connection(self, mock_conn_class):
        """测试获取连接"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        pool = SSHConnectionPool(config)

        conn = pool.acquire()

        assert conn is not None
        assert conn == mock_conn
        assert pool.active_connections == 1

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_release_connection(self, mock_conn_class):
        """测试释放连接"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        pool = SSHConnectionPool(config)

        conn = pool.acquire()
        pool.release(conn)

        assert pool.available_connections == 1

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_close_all(self, mock_conn_class):
        """测试关闭所有连接"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        pool = SSHConnectionPool(config)

        pool.acquire()
        pool.acquire()

        assert pool.active_connections == 2

        pool.close_all()

        assert len(pool._connections) == 0
        assert pool.active_connections == 0


class TestSSHManager:
    """SSHManager类测试"""

    def test_init_without_config(self):
        """测试无配置初始化"""
        manager = SSHManager()

        assert manager.config is None
        assert manager.use_pool is False
        assert manager.connected is False

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)

        assert manager.config == config
        assert manager.use_pool is False

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_connect_success(self, mock_conn_class):
        """测试连接成功"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn.client = Mock()
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)

        result = manager.connect()

        assert result is True
        assert manager.connected is True
        mock_conn.connect.assert_called_once()

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_connect_failure(self, mock_conn_class):
        """测试连接失败"""
        mock_conn = Mock()
        mock_conn.connected = False
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = False

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)

        result = manager.connect()

        assert result is False
        assert manager.connected is False

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_disconnect(self, mock_conn_class):
        """测试断开连接"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn.client = Mock()
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        manager.disconnect()

        assert manager.connected is False
        mock_conn.close.assert_called_once()

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_execute_command_success(self, mock_conn_class):
        """测试执行命令成功"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_client = Mock()
        mock_conn.client = mock_client
        mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

        mock_stdout.read.return_value = b"hello world"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        stdout, stderr, exit_code = manager.execute_command("echo hello")

        assert stdout == "hello world"
        assert stderr == ""
        assert exit_code == 0
        mock_client.exec_command.assert_called_once_with(
            "echo hello", timeout=None, get_pty=False
        )

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_execute_command_failure(self, mock_conn_class):
        """测试执行命令失败"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_client = Mock()
        mock_conn.client = mock_client
        mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"command not found"
        mock_stdout.channel.recv_exit_status.return_value = 127

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        stdout, stderr, exit_code = manager.execute_command("nonexistent_cmd")

        assert stdout == ""
        assert stderr == "command not found"
        assert exit_code == 127

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_execute_command_not_connected(self, mock_conn_class):
        """测试未连接时执行命令"""
        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)

        with pytest.raises(RuntimeError, match="SSH未连接"):
            manager.execute_command("echo hello")

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_execute_commands(self, mock_conn_class):
        """测试执行命令序列"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_client = Mock()
        mock_conn.client = mock_client
        mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

        mock_stdout.read.return_value = b"result"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        results = manager.execute_commands(["cmd1", "cmd2"])

        assert len(results) == 2
        assert results[0] == ("result", "", 0)
        assert results[1] == ("result", "", 0)

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_upload_file_success(self, mock_conn_class):
        """测试文件上传成功"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_client = Mock()
        mock_conn.client = mock_client

        mock_sftp = Mock()
        type(mock_conn).sftp = PropertyMock(return_value=mock_sftp)

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        with patch("pathlib.Path.exists", return_value=True):
            result = manager.upload_file("/local/file.txt", "/remote/file.txt")

            assert result is True
            mock_sftp.put.assert_called_once_with(
                "/local/file.txt", "/remote/file.txt", callback=None
            )

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_upload_file_not_found(self, mock_conn_class):
        """测试上传不存在的文件"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                manager.upload_file("/nonexistent/file.txt", "/remote/file.txt")

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_download_file_success(self, mock_conn_class):
        """测试文件下载成功"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_client = Mock()
        mock_conn.client = mock_client

        mock_sftp = Mock()
        type(mock_conn).sftp = PropertyMock(return_value=mock_sftp)

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        result = manager.download_file("/remote/file.txt", "/local/file.txt")

        assert result is True
        mock_sftp.get.assert_called_once_with(
            "/remote/file.txt", "/local/file.txt", callback=None
        )

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_upload_directory_success(self, mock_conn_class):
        """测试目录上传成功"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_client = Mock()
        mock_conn.client = mock_client

        mock_sftp = Mock()
        mock_sftp.stat.side_effect = FileNotFoundError()
        type(mock_conn).sftp = PropertyMock(return_value=mock_sftp)

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.rglob") as mock_rglob:
                    mock_file = Mock()
                    mock_file.is_file.return_value = True
                    mock_file.is_dir.return_value = False
                    mock_file.stat.return_value.st_size = 100
                    mock_file.relative_to.return_value = Path("subdir/file.txt")
                    mock_rglob.return_value = [mock_file]

                    result = manager.upload_directory("/local/dir", "/remote/dir")

                    assert result is True

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_list_directory(self, mock_conn_class):
        """测试列出目录"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_client = Mock()
        mock_conn.client = mock_client

        mock_sftp = Mock()
        type(mock_conn).sftp = PropertyMock(return_value=mock_sftp)

        import stat

        mock_attr = Mock()
        mock_attr.filename = "test.txt"
        mock_attr.st_mode = stat.S_IFREG
        mock_attr.st_size = 1024
        mock_attr.st_mtime = 1234567890
        mock_sftp.listdir_attr.return_value = [mock_attr]

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        files = manager.list_directory("/remote/dir")

        assert len(files) == 1
        assert files[0]["filename"] == "test.txt"
        assert files[0]["type"] == "file"
        assert files[0]["size"] == 1024

    @patch("ai_llm_agent_crawler.ssh_manager.SSHConnection")
    def test_list_directory_not_found(self, mock_conn_class):
        """测试列出不存在的目录"""
        mock_conn = Mock()
        mock_conn.connected = True
        mock_conn_class.return_value = mock_conn
        mock_conn.connect.return_value = True

        mock_client = Mock()
        mock_conn.client = mock_client

        mock_sftp = Mock()
        mock_sftp.listdir_attr.side_effect = FileNotFoundError()
        type(mock_conn).sftp = PropertyMock(return_value=mock_sftp)

        config = SSHConfig(hostname="192.168.1.1", username="admin")
        manager = SSHManager(config=config)
        manager.connect()

        with pytest.raises(RuntimeError, match="远程目录不存在"):
            manager.list_directory("/nonexistent/dir")
