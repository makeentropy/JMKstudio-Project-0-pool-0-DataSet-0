"""
开发环境初始化管理模块

提供远程开发环境的自动化安装和配置功能，支持Kali Linux、VSCode IDE、Jupyter Notebook/Lab等工具的安装。
"""

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.ssh_manager import SSHConfig, SSHManager
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class EnvConfig(BaseModel):
    """
    环境配置类

    定义开发环境初始化所需的所有配置参数。
    """

    ssh_config: SSHConfig = Field(..., description="目标主机SSH配置")
    install_kali: bool = Field(default=True, description="是否安装Kali Linux Full")
    install_ide: bool = Field(default=True, description="是否安装VSCode IDE")
    install_jupyter: bool = Field(default=True, description="是否安装Jupyter Notebook/Lab")
    custom_packages: List[str] = Field(default_factory=list, description="自定义安装包列表")
    jupyter_port: int = Field(default=8888, description="Jupyter服务端口")
    jupyter_password: Optional[str] = Field(default=None, description="Jupyter访问密码")
    jupyter_notebook_dir: str = Field(default="~/notebooks", description="Jupyter工作目录")
    use_sudo: bool = Field(default=True, description="是否使用sudo权限执行安装命令")

    model_config = {"arbitrary_types_allowed": True}


class EnvironmentManager:
    """
    开发环境核心管理类

    提供远程开发环境的安装、配置和验证功能。
    """

    def __init__(self, config: EnvConfig):
        """
        初始化环境管理器

        Args:
            config: 环境配置
        """
        self.config = config
        self.ssh_manager = SSHManager(config=config.ssh_config)

    def connect(self) -> bool:
        """
        建立SSH连接

        Returns:
            是否连接成功
        """
        return self.ssh_manager.connect()

    def disconnect(self) -> None:
        """断开SSH连接"""
        self.ssh_manager.disconnect()

    def _sudo_prefix(self) -> str:
        """获取sudo前缀"""
        return "sudo " if self.config.use_sudo else ""

    def install_kali_linux_full(self) -> Tuple[str, str, int]:
        """
        安装Kali Linux Full

        Returns:
            (stdout, stderr, exit_code)
        """
        commands = [
            f"{self._sudo_prefix()}apt-get update -y",
            f"{self._sudo_prefix()}apt-get upgrade -y",
            f"{self._sudo_prefix()}apt-get install -y kali-linux-full",
        ]

        logger.info("开始安装Kali Linux Full")
        results = self.ssh_manager.execute_commands(commands, timeout=3600)

        for cmd, result in zip(commands, results):
            stdout, stderr, exit_code = result
            if exit_code != 0:
                logger.error(f"Kali Linux安装失败: {cmd}, 错误: {stderr}")
                return stdout, stderr, exit_code

        logger.info("Kali Linux Full安装完成")
        return results[-1]

    def install_ide(self) -> Tuple[str, str, int]:
        """
        安装VSCode IDE

        Returns:
            (stdout, stderr, exit_code)
        """
        commands = [
            f"{self._sudo_prefix()}apt-get update -y",
            f"{self._sudo_prefix()}apt-get install -y wget gpg",
            "wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg",
            f"{self._sudo_prefix()}install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg",
            f'{self._sudo_prefix()}sh -c \'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list\'',
            f"{self._sudo_prefix()}rm -f packages.microsoft.gpg",
            f"{self._sudo_prefix()}apt-get update -y",
            f"{self._sudo_prefix()}apt-get install -y code",
        ]

        logger.info("开始安装VSCode IDE")
        results = self.ssh_manager.execute_commands(commands, timeout=600)

        for cmd, result in zip(commands, results):
            stdout, stderr, exit_code = result
            if exit_code != 0:
                logger.error(f"VSCode安装失败: {cmd}, 错误: {stderr}")
                return stdout, stderr, exit_code

        logger.info("VSCode IDE安装完成")
        return results[-1]

    def install_jupyter(self) -> Tuple[str, str, int]:
        """
        安装Jupyter Notebook/Lab

        Returns:
            (stdout, stderr, exit_code)
        """
        commands = [
            f"{self._sudo_prefix()}apt-get update -y",
            f"{self._sudo_prefix()}apt-get install -y python3-pip python3-dev",
            f"{self._sudo_prefix()}pip3 install --upgrade pip",
            f"{self._sudo_prefix()}pip3 install jupyter jupyterlab",
        ]

        logger.info("开始安装Jupyter Notebook/Lab")
        results = self.ssh_manager.execute_commands(commands, timeout=600)

        for cmd, result in zip(commands, results):
            stdout, stderr, exit_code = result
            if exit_code != 0:
                logger.error(f"Jupyter安装失败: {cmd}, 错误: {stderr}")
                return stdout, stderr, exit_code

        logger.info("Jupyter Notebook/Lab安装完成")
        return results[-1]

    def configure_jupyter(self) -> Tuple[str, str, int]:
        """
        配置Jupyter（密码、端口等）

        Returns:
            (stdout, stderr, exit_code)
        """
        commands = [
            f"mkdir -p {self.config.jupyter_notebook_dir}",
        ]

        if self.config.jupyter_password:
            commands.append(
                f'python3 -c "from jupyter_server.auth import passwd; print(passwd(\'{self.config.jupyter_password}\'))" | xargs -I {{}} echo \"c.NotebookApp.password = \'{{}}\'\" >> ~/.jupyter/jupyter_notebook_config.py'
            )

        commands.extend([
            f'echo "c.NotebookApp.port = {self.config.jupyter_port}" >> ~/.jupyter/jupyter_notebook_config.py',
            f'echo "c.NotebookApp.notebook_dir = \'{self.config.jupyter_notebook_dir}\'" >> ~/.jupyter/jupyter_notebook_config.py',
            f'echo "c.NotebookApp.ip = \'0.0.0.0\'" >> ~/.jupyter/jupyter_notebook_config.py',
            f'echo "c.NotebookApp.allow_remote_access = True" >> ~/.jupyter/jupyter_notebook_config.py',
        ])

        logger.info("开始配置Jupyter")
        results = self.ssh_manager.execute_commands(commands, timeout=300)

        for cmd, result in zip(commands, results):
            stdout, stderr, exit_code = result
            if exit_code != 0:
                logger.error(f"Jupyter配置失败: {cmd}, 错误: {stderr}")
                return stdout, stderr, exit_code

        logger.info("Jupyter配置完成")
        return results[-1]

    def install_custom_packages(self) -> List[Tuple[str, str, int]]:
        """
        安装自定义包列表

        Returns:
            每个包的安装结果列表
        """
        if not self.config.custom_packages:
            logger.info("没有自定义包需要安装")
            return []

        commands = [
            f"{self._sudo_prefix()}apt-get install -y {' '.join(self.config.custom_packages)}"
        ]

        logger.info(f"开始安装自定义包: {', '.join(self.config.custom_packages)}")
        results = self.ssh_manager.execute_commands(commands, timeout=600)

        for cmd, result in zip(commands, results):
            stdout, stderr, exit_code = result
            if exit_code != 0:
                logger.error(f"自定义包安装失败: {cmd}, 错误: {stderr}")

        logger.info("自定义包安装完成")
        return results

    def full_setup(self) -> Dict[str, Tuple[str, str, int]]:
        """
        完整环境设置

        Returns:
            各个组件的安装结果字典
        """
        results = {}

        try:
            if self.config.install_kali:
                results["kali_linux"] = self.install_kali_linux_full()

            if self.config.install_ide:
                results["vscode"] = self.install_ide()

            if self.config.install_jupyter:
                results["jupyter"] = self.install_jupyter()
                results["jupyter_config"] = self.configure_jupyter()

            if self.config.custom_packages:
                results["custom_packages"] = self.install_custom_packages()

            logger.info("完整环境设置完成")
        except Exception as e:
            logger.error(f"完整环境设置失败: {str(e)}")
            raise

        return results

    def verify_setup(self) -> Dict[str, bool]:
        """
        验证环境设置

        Returns:
            各个组件的验证结果字典
        """
        checks = {}

        try:
            if self.config.install_kali:
                checks["kali_linux"] = self._verify_kali_linux()

            if self.config.install_ide:
                checks["vscode"] = self._verify_vscode()

            if self.config.install_jupyter:
                checks["jupyter"] = self._verify_jupyter()

            logger.info("环境验证完成")
        except Exception as e:
            logger.error(f"环境验证失败: {str(e)}")
            raise

        return checks

    def _verify_kali_linux(self) -> bool:
        """
        验证Kali Linux安装

        Returns:
            是否验证通过
        """
        stdout, stderr, exit_code = self.ssh_manager.execute_command(
            "dpkg -l | grep -i kali-linux-full"
        )
        return exit_code == 0 and "kali-linux-full" in stdout

    def _verify_vscode(self) -> bool:
        """
        验证VSCode安装

        Returns:
            是否验证通过
        """
        stdout, stderr, exit_code = self.ssh_manager.execute_command("code --version")
        return exit_code == 0

    def _verify_jupyter(self) -> bool:
        """
        验证Jupyter安装

        Returns:
            是否验证通过
        """
        stdout, stderr, exit_code = self.ssh_manager.execute_command(
            "jupyter notebook --version"
        )
        if exit_code != 0:
            return False

        stdout, stderr, exit_code = self.ssh_manager.execute_command(
            "jupyter lab --version"
        )
        return exit_code == 0


__all__ = [
    "EnvConfig",
    "EnvironmentManager",
]