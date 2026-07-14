"""
环境管理器单元测试

使用mock测试环境配置初始化、安装命令生成和验证功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ai_llm_agent_crawler.env_manager import EnvConfig, EnvironmentManager
from ai_llm_agent_crawler.ssh_manager import SSHConfig


class TestEnvConfig:
    """EnvConfig类测试"""

    def test_init_default_values(self):
        """测试默认配置初始化"""
        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        config = EnvConfig(ssh_config=ssh_config)

        assert config.ssh_config == ssh_config
        assert config.install_kali is True
        assert config.install_ide is True
        assert config.install_jupyter is True
        assert config.custom_packages == []
        assert config.jupyter_port == 8888
        assert config.jupyter_password is None
        assert config.jupyter_notebook_dir == "~/notebooks"
        assert config.use_sudo is True

    def test_init_with_custom_values(self):
        """测试自定义配置初始化"""
        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        config = EnvConfig(
            ssh_config=ssh_config,
            install_kali=False,
            install_ide=False,
            install_jupyter=True,
            custom_packages=["vim", "git"],
            jupyter_port=9999,
            jupyter_password="testpass",
            jupyter_notebook_dir="~/my_notebooks",
            use_sudo=False,
        )

        assert config.install_kali is False
        assert config.install_ide is False
        assert config.install_jupyter is True
        assert config.custom_packages == ["vim", "git"]
        assert config.jupyter_port == 9999
        assert config.jupyter_password == "testpass"
        assert config.jupyter_notebook_dir == "~/my_notebooks"
        assert config.use_sudo is False

    def test_init_without_password(self):
        """测试无密码配置"""
        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        config = EnvConfig(ssh_config=ssh_config, jupyter_password=None)

        assert config.jupyter_password is None


class TestEnvironmentManager:
    """EnvironmentManager类测试"""

    def test_init(self):
        """测试初始化"""
        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        assert manager.config == env_config
        assert manager.ssh_manager.config == ssh_config

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_connect_success(self, mock_ssh_manager_class):
        """测试连接成功"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.connect.return_value = True
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        result = manager.connect()

        assert result is True
        mock_ssh_manager.connect.assert_called_once()

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_connect_failure(self, mock_ssh_manager_class):
        """测试连接失败"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.connect.return_value = False
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        result = manager.connect()

        assert result is False
        mock_ssh_manager.connect.assert_called_once()

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_disconnect(self, mock_ssh_manager_class):
        """测试断开连接"""
        mock_ssh_manager = Mock()
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        manager.disconnect()

        mock_ssh_manager.disconnect.assert_called_once()

    def test_sudo_prefix_with_sudo(self):
        """测试带sudo前缀"""
        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, use_sudo=True)
        manager = EnvironmentManager(config=env_config)

        assert manager._sudo_prefix() == "sudo "

    def test_sudo_prefix_without_sudo(self):
        """测试不带sudo前缀"""
        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, use_sudo=False)
        manager = EnvironmentManager(config=env_config)

        assert manager._sudo_prefix() == ""

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_install_kali_linux_full_success(self, mock_ssh_manager_class):
        """测试安装Kali Linux Full成功"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("", "", 0),
            ("", "", 0),
            ("kali-linux-full installed", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, use_sudo=True)
        manager = EnvironmentManager(config=env_config)

        stdout, stderr, exit_code = manager.install_kali_linux_full()

        assert stdout == "kali-linux-full installed"
        assert stderr == ""
        assert exit_code == 0
        mock_ssh_manager.execute_commands.assert_called_once()

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_install_kali_linux_full_failure(self, mock_ssh_manager_class):
        """测试安装Kali Linux Full失败"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("", "", 0),
            ("", "upgrade error", 1),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, use_sudo=True)
        manager = EnvironmentManager(config=env_config)

        stdout, stderr, exit_code = manager.install_kali_linux_full()

        assert stderr == "upgrade error"
        assert exit_code == 1

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_install_ide_success(self, mock_ssh_manager_class):
        """测试安装VSCode成功"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("code version 1.80", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, use_sudo=True)
        manager = EnvironmentManager(config=env_config)

        stdout, stderr, exit_code = manager.install_ide()

        assert stdout == "code version 1.80"
        assert exit_code == 0
        mock_ssh_manager.execute_commands.assert_called_once()

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_install_jupyter_success(self, mock_ssh_manager_class):
        """测试安装Jupyter成功"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("jupyter installed", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, use_sudo=True)
        manager = EnvironmentManager(config=env_config)

        stdout, stderr, exit_code = manager.install_jupyter()

        assert stdout == "jupyter installed"
        assert exit_code == 0
        mock_ssh_manager.execute_commands.assert_called_once()

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_configure_jupyter_with_password(self, mock_ssh_manager_class):
        """测试配置Jupyter（带密码）"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(
            ssh_config=ssh_config,
            jupyter_password="testpass",
            jupyter_port=9999,
            jupyter_notebook_dir="~/my_notebooks",
        )
        manager = EnvironmentManager(config=env_config)

        stdout, stderr, exit_code = manager.configure_jupyter()

        assert exit_code == 0
        assert mock_ssh_manager.execute_commands.call_count == 1

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_configure_jupyter_without_password(self, mock_ssh_manager_class):
        """测试配置Jupyter（无密码）"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, jupyter_password=None)
        manager = EnvironmentManager(config=env_config)

        stdout, stderr, exit_code = manager.configure_jupyter()

        assert exit_code == 0

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_install_custom_packages(self, mock_ssh_manager_class):
        """测试安装自定义包"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("vim git installed", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(
            ssh_config=ssh_config,
            custom_packages=["vim", "git"],
            use_sudo=True,
        )
        manager = EnvironmentManager(config=env_config)

        results = manager.install_custom_packages()

        assert len(results) == 1
        assert results[0][2] == 0
        mock_ssh_manager.execute_commands.assert_called_once()

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_install_custom_packages_empty(self, mock_ssh_manager_class):
        """测试安装空自定义包列表"""
        mock_ssh_manager = Mock()
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config, custom_packages=[])
        manager = EnvironmentManager(config=env_config)

        results = manager.install_custom_packages()

        assert results == []
        mock_ssh_manager.execute_commands.assert_not_called()

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_full_setup(self, mock_ssh_manager_class):
        """测试完整环境设置"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [
            ("", "", 0),
            ("", "", 0),
            ("", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(
            ssh_config=ssh_config,
            install_kali=True,
            install_ide=True,
            install_jupyter=True,
        )
        manager = EnvironmentManager(config=env_config)

        results = manager.full_setup()

        assert "kali_linux" in results
        assert "vscode" in results
        assert "jupyter" in results
        assert "jupyter_config" in results

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_full_setup_partial(self, mock_ssh_manager_class):
        """测试部分环境设置"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_commands.return_value = [("", "", 0)]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(
            ssh_config=ssh_config,
            install_kali=False,
            install_ide=False,
            install_jupyter=True,
        )
        manager = EnvironmentManager(config=env_config)

        results = manager.full_setup()

        assert "kali_linux" not in results
        assert "vscode" not in results
        assert "jupyter" in results
        assert "jupyter_config" in results

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_verify_setup(self, mock_ssh_manager_class):
        """测试验证环境设置"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_command.side_effect = [
            ("kali-linux-full", "", 0),
            ("code 1.80", "", 0),
            ("notebook 6.5", "", 0),
            ("lab 3.6", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(
            ssh_config=ssh_config,
            install_kali=True,
            install_ide=True,
            install_jupyter=True,
        )
        manager = EnvironmentManager(config=env_config)

        checks = manager.verify_setup()

        assert checks["kali_linux"] is True
        assert checks["vscode"] is True
        assert checks["jupyter"] is True

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_verify_setup_failure(self, mock_ssh_manager_class):
        """测试验证环境设置失败"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_command.side_effect = [
            ("", "", 1),
            ("code 1.80", "", 0),
            ("notebook 6.5", "", 0),
            ("", "command not found", 127),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(
            ssh_config=ssh_config,
            install_kali=True,
            install_ide=True,
            install_jupyter=True,
        )
        manager = EnvironmentManager(config=env_config)

        checks = manager.verify_setup()

        assert checks["kali_linux"] is False
        assert checks["vscode"] is True
        assert checks["jupyter"] is False

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_verify_kali_linux(self, mock_ssh_manager_class):
        """测试验证Kali Linux"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_command.return_value = ("ii  kali-linux-full", "", 0)
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        result = manager._verify_kali_linux()

        assert result is True

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_verify_kali_linux_not_installed(self, mock_ssh_manager_class):
        """测试验证Kali Linux未安装"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_command.return_value = ("", "", 1)
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        result = manager._verify_kali_linux()

        assert result is False

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_verify_vscode(self, mock_ssh_manager_class):
        """测试验证VSCode"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_command.return_value = ("1.80.0", "", 0)
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        result = manager._verify_vscode()

        assert result is True

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_verify_jupyter(self, mock_ssh_manager_class):
        """测试验证Jupyter"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_command.side_effect = [
            ("6.5.0", "", 0),
            ("3.6.0", "", 0),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        result = manager._verify_jupyter()

        assert result is True

    @patch("ai_llm_agent_crawler.env_manager.SSHManager")
    def test_verify_jupyter_lab_failure(self, mock_ssh_manager_class):
        """测试验证Jupyter Lab失败"""
        mock_ssh_manager = Mock()
        mock_ssh_manager.execute_command.side_effect = [
            ("6.5.0", "", 0),
            ("", "command not found", 127),
        ]
        mock_ssh_manager_class.return_value = mock_ssh_manager

        ssh_config = SSHConfig(hostname="192.168.1.1", username="admin")
        env_config = EnvConfig(ssh_config=ssh_config)
        manager = EnvironmentManager(config=env_config)

        result = manager._verify_jupyter()

        assert result is False