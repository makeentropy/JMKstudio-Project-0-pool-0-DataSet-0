"""
SSH运维管理模块

提供SSH连接管理、远程命令执行、文件传输等功能。
支持密码认证和密钥认证，支持连接池管理。
"""

import os
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import paramiko
from paramiko import SSHClient, SFTPClient
from paramiko.ssh_exception import (
    AuthenticationException,
    BadHostKeyException,
    NoValidConnectionsError,
    SSHException,
)

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class SSHConfig:
    """
    SSH连接配置

    定义SSH连接所需的参数。
    """

    def __init__(
        self,
        hostname: str,
        username: str,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
        port: int = 22,
        timeout: int = 10,
        banner_timeout: int = 30,
        auth_timeout: int = 30,
        gss_auth: bool = False,
        gss_kex: bool = False,
        gss_deleg_creds: bool = True,
        gss_host: Optional[str] = None,
    ):
        """
        初始化SSH配置

        Args:
            hostname: 主机地址
            username: 用户名
            password: 密码（用于密码认证）
            private_key_path: 私钥路径（用于密钥认证）
            private_key_passphrase: 私钥密码（如果私钥有密码保护）
            port: SSH端口，默认为22
            timeout: 连接超时时间（秒）
            banner_timeout: banner超时时间（秒）
            auth_timeout: 认证超时时间（秒）
            gss_auth: 是否启用GSS认证
            gss_kex: 是否启用GSS密钥交换
            gss_deleg_creds: 是否启用GSS凭证委托
            gss_host: GSS主机名
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.private_key_passphrase = private_key_passphrase
        self.port = port
        self.timeout = timeout
        self.banner_timeout = banner_timeout
        self.auth_timeout = auth_timeout
        self.gss_auth = gss_auth
        self.gss_kex = gss_kex
        self.gss_deleg_creds = gss_deleg_creds
        self.gss_host = gss_host

    def __repr__(self) -> str:
        return (
            f"SSHConfig(hostname={self.hostname!r}, username={self.username!r}, "
            f"port={self.port}, timeout={self.timeout})"
        )


class SSHConnection:
    """
    SSH连接封装

    封装单个SSH连接及其状态。
    """

    def __init__(self, config: SSHConfig):
        """
        初始化SSH连接

        Args:
            config: SSH配置
        """
        self.config = config
        self._client: Optional[SSHClient] = None
        self._sftp: Optional[SFTPClient] = None
        self._connected: bool = False
        self._last_used: float = 0.0

    @property
    def connected(self) -> bool:
        """检查连接是否已建立"""
        return self._connected and self._client is not None

    @property
    def client(self) -> Optional[SSHClient]:
        """获取SSH客户端"""
        return self._client

    @property
    def sftp(self) -> Optional[SFTPClient]:
        """获取SFTP客户端"""
        return self._sftp

    def connect(self) -> bool:
        """
        建立SSH连接

        Returns:
            是否连接成功
        """
        try:
            self._client = SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            kwargs: Dict[str, Any] = {
                "hostname": self.config.hostname,
                "username": self.config.username,
                "port": self.config.port,
                "timeout": self.config.timeout,
                "banner_timeout": self.config.banner_timeout,
                "auth_timeout": self.config.auth_timeout,
            }

            if self.config.password:
                kwargs["password"] = self.config.password
            elif self.config.private_key_path:
                private_key = paramiko.RSAKey.from_private_key_file(
                    self.config.private_key_path,
                    password=self.config.private_key_passphrase,
                )
                kwargs["pkey"] = private_key
            else:
                kwargs["look_for_keys"] = True
                kwargs["allow_agent"] = True

            self._client.connect(**kwargs)
            self._connected = True
            logger.info(f"SSH连接成功: {self.config.hostname}:{self.config.port}")
            return True

        except AuthenticationException:
            logger.error(f"SSH认证失败: {self.config.hostname}")
            self.close()
            return False
        except BadHostKeyException:
            logger.error(f"SSH主机密钥验证失败: {self.config.hostname}")
            self.close()
            return False
        except NoValidConnectionsError:
            logger.error(f"SSH连接失败，无法连接到 {self.config.hostname}:{self.config.port}")
            self.close()
            return False
        except socket.timeout:
            logger.error(f"SSH连接超时: {self.config.hostname}")
            self.close()
            return False
        except SSHException as e:
            logger.error(f"SSH连接异常: {self.config.hostname}, 错误: {str(e)}")
            self.close()
            return False
        except Exception as e:
            logger.error(f"SSH连接发生未知错误: {self.config.hostname}, 错误: {str(e)}")
            self.close()
            return False

    def close(self) -> None:
        """关闭SSH连接"""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

        self._connected = False
        logger.debug(f"SSH连接已关闭: {self.config.hostname}")


class SSHConnectionPool:
    """
    SSH连接池

    管理多个SSH连接，支持连接复用。
    """

    def __init__(
        self,
        config: SSHConfig,
        max_connections: int = 5,
        connection_timeout: int = 300,
    ):
        """
        初始化连接池

        Args:
            config: SSH配置（池中的所有连接使用相同配置）
            max_connections: 最大连接数
            connection_timeout: 连接超时时间（秒），超过此时间的连接将被回收
        """
        self.config = config
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self._connections: List[SSHConnection] = []
        self._in_use: Dict[int, bool] = {}

    def _get_available_connection(self) -> Optional[SSHConnection]:
        """获取可用连接"""
        # 先检查是否有空闲连接
        for i, conn in enumerate(self._connections):
            if not self._in_use.get(i, False) and conn.connected:
                self._in_use[i] = True
                return conn

        # 如果没有空闲连接，检查是否可以创建新连接
        if len(self._connections) < self.max_connections:
            conn = SSHConnection(self.config)
            if conn.connect():
                self._connections.append(conn)
                self._in_use[len(self._connections) - 1] = True
                return conn

        return None

    def acquire(self) -> Optional[SSHConnection]:
        """
        获取一个可用的SSH连接

        Returns:
            SSH连接实例，如果无法获取则返回None
        """
        # 先尝试回收超时连接
        self._cleanup()

        # 获取可用连接
        conn = self._get_available_connection()

        if conn:
            logger.debug(f"从连接池获取连接: {self.config.hostname}")
        else:
            logger.warning(f"连接池已满，无法获取连接: {self.config.hostname}")

        return conn

    def release(self, conn: SSHConnection) -> None:
        """
        释放连接，将其放回连接池

        Args:
            conn: 要释放的连接
        """
        for i, c in enumerate(self._connections):
            if c == conn:
                self._in_use[i] = False
                logger.debug(f"连接已释放回连接池: {self.config.hostname}")
                break

    def _cleanup(self) -> None:
        """清理超时或断开的连接"""
        import time

        current_time = time.time()
        to_remove = []

        for i, conn in enumerate(self._connections):
            if not conn.connected or (
                not self._in_use.get(i, False)
                and current_time - conn._last_used > self.connection_timeout
            ):
                conn.close()
                to_remove.append(i)

        # 逆序删除以保持索引正确
        for i in reversed(to_remove):
            del self._connections[i]
            del self._in_use[i]

    def close_all(self) -> None:
        """关闭所有连接"""
        for conn in self._connections:
            conn.close()
        self._connections = []
        self._in_use = {}
        logger.info(f"连接池已关闭所有连接: {self.config.hostname}")

    @property
    def active_connections(self) -> int:
        """获取活跃连接数"""
        return sum(1 for conn in self._connections if conn.connected)

    @property
    def available_connections(self) -> int:
        """获取可用连接数"""
        return sum(
            1
            for i, conn in enumerate(self._connections)
            if conn.connected and not self._in_use.get(i, False)
        )


class SSHManager:
    """
    SSH管理器

    提供SSH连接管理、远程命令执行、文件传输等功能。
    """

    def __init__(
        self,
        config: Optional[SSHConfig] = None,
        use_pool: bool = False,
        max_pool_size: int = 5,
    ):
        """
        初始化SSH管理器

        Args:
            config: SSH配置
            use_pool: 是否使用连接池
            max_pool_size: 连接池最大连接数
        """
        self.config = config
        self.use_pool = use_pool
        self._pool: Optional[SSHConnectionPool] = None
        self._connection: Optional[SSHConnection] = None

        if use_pool and config:
            self._pool = SSHConnectionPool(config, max_connections=max_pool_size)

        logger.info(f"SSHManager初始化完成, 使用连接池: {use_pool}")

    def connect(self, config: Optional[SSHConfig] = None) -> bool:
        """
        建立SSH连接

        Args:
            config: SSH配置，如果未提供则使用初始化时的配置

        Returns:
            是否连接成功
        """
        if config:
            self.config = config

        if not self.config:
            logger.error("SSH配置未提供")
            return False

        if self.use_pool:
            if not self._pool:
                self._pool = SSHConnectionPool(self.config)
            conn = self._pool.acquire()
            if conn:
                self._connection = conn
                return True
            return False
        else:
            self._connection = SSHConnection(self.config)
            return self._connection.connect()

    def disconnect(self) -> None:
        """断开SSH连接"""
        if self.use_pool and self._connection and self._pool:
            self._pool.release(self._connection)
            self._connection = None
        else:
            if self._connection:
                self._connection.close()
                self._connection = None

    def close_pool(self) -> None:
        """关闭连接池"""
        if self._pool:
            self._pool.close_all()
            self._pool = None

    @property
    def connected(self) -> bool:
        """检查是否已连接"""
        return self._connection is not None and self._connection.connected

    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        get_pty: bool = False,
    ) -> Tuple[str, str, int]:
        """
        执行单个命令

        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            get_pty: 是否获取PTY

        Returns:
            (stdout, stderr, exit_code)

        Raises:
            SSHException: SSH连接异常
            RuntimeError: 未连接或执行失败
        """
        if not self.connected:
            raise RuntimeError("SSH未连接，请先调用connect()方法")

        if not self._connection or not self._connection.client:
            raise RuntimeError("SSH客户端不可用")

        try:
            logger.debug(f"执行命令: {command}")

            stdin, stdout, stderr = self._connection.client.exec_command(
                command,
                timeout=timeout,
                get_pty=get_pty,
            )

            output = stdout.read().decode("utf-8", errors="ignore").strip()
            error = stderr.read().decode("utf-8", errors="ignore").strip()
            exit_code = stdout.channel.recv_exit_status()

            logger.debug(f"命令执行完成, 退出码: {exit_code}")

            return output, error, exit_code

        except socket.timeout:
            raise SSHException(f"命令执行超时: {command}")
        except SSHException as e:
            logger.error(f"命令执行失败: {command}, 错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"命令执行发生未知错误: {command}, 错误: {str(e)}")
            raise RuntimeError(f"命令执行失败: {str(e)}")

    def execute_commands(
        self,
        commands: List[str],
        timeout: Optional[int] = None,
        stop_on_error: bool = True,
    ) -> List[Tuple[str, str, int]]:
        """
        执行命令序列

        Args:
            commands: 命令列表
            timeout: 每个命令的超时时间（秒）
            stop_on_error: 是否在遇到错误时停止执行

        Returns:
            每个命令的执行结果列表，格式为 [(stdout, stderr, exit_code), ...]

        Raises:
            RuntimeError: 未连接
        """
        if not self.connected:
            raise RuntimeError("SSH未连接，请先调用connect()方法")

        results = []

        for command in commands:
            try:
                result = self.execute_command(command, timeout=timeout)
                results.append(result)

                if stop_on_error and result[2] != 0:
                    logger.warning(f"命令执行失败，停止后续命令: {command}")
                    break

            except Exception as e:
                logger.error(f"命令执行异常: {command}, 错误: {str(e)}")
                results.append(("", str(e), -1))
                if stop_on_error:
                    break

        return results

    def upload_file(
        self,
        local_path: Union[str, Path],
        remote_path: str,
        callback: Optional[callable] = None,
    ) -> bool:
        """
        上传单个文件

        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            callback: 上传进度回调函数，接收(bytes_transferred, total_bytes)

        Returns:
            是否上传成功

        Raises:
            RuntimeError: 未连接或上传失败
        """
        if not self.connected:
            raise RuntimeError("SSH未连接，请先调用connect()方法")

        if not self._connection:
            raise RuntimeError("SSH连接不可用")

        try:
            local_path = Path(local_path)
            if not local_path.exists():
                raise FileNotFoundError(f"本地文件不存在: {local_path}")

            if not self._connection.sftp:
                self._connection._sftp = self._connection.client.open_sftp()

            logger.info(f"上传文件: {local_path} -> {remote_path}")

            self._connection.sftp.put(
                str(local_path),
                remote_path,
                callback=callback,
            )

            logger.info(f"文件上传成功: {local_path}")
            return True

        except FileNotFoundError as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise
        except SSHException as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise RuntimeError(f"文件上传失败: {str(e)}")
        except Exception as e:
            logger.error(f"文件上传发生未知错误: {str(e)}")
            raise RuntimeError(f"文件上传失败: {str(e)}")

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        callback: Optional[callable] = None,
    ) -> bool:
        """
        下载单个文件

        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径
            callback: 下载进度回调函数，接收(bytes_transferred, total_bytes)

        Returns:
            是否下载成功

        Raises:
            RuntimeError: 未连接或下载失败
        """
        if not self.connected:
            raise RuntimeError("SSH未连接，请先调用connect()方法")

        if not self._connection:
            raise RuntimeError("SSH连接不可用")

        try:
            local_path = Path(local_path)

            if not self._connection.sftp:
                self._connection._sftp = self._connection.client.open_sftp()

            logger.info(f"下载文件: {remote_path} -> {local_path}")

            self._connection.sftp.get(
                remote_path,
                str(local_path),
                callback=callback,
            )

            logger.info(f"文件下载成功: {local_path}")
            return True

        except FileNotFoundError as e:
            logger.error(f"文件下载失败: {str(e)}")
            raise
        except SSHException as e:
            logger.error(f"文件下载失败: {str(e)}")
            raise RuntimeError(f"文件下载失败: {str(e)}")
        except Exception as e:
            logger.error(f"文件下载发生未知错误: {str(e)}")
            raise RuntimeError(f"文件下载失败: {str(e)}")

    def upload_directory(
        self,
        local_dir: Union[str, Path],
        remote_dir: str,
        callback: Optional[callable] = None,
    ) -> bool:
        """
        上传目录（递归）

        Args:
            local_dir: 本地目录路径
            remote_dir: 远程目录路径
            callback: 上传进度回调函数，接收(bytes_transferred, total_bytes)

        Returns:
            是否上传成功

        Raises:
            RuntimeError: 未连接或上传失败
        """
        if not self.connected:
            raise RuntimeError("SSH未连接，请先调用connect()方法")

        if not self._connection:
            raise RuntimeError("SSH连接不可用")

        try:
            local_dir = Path(local_dir)
            if not local_dir.exists() or not local_dir.is_dir():
                raise FileNotFoundError(f"本地目录不存在或不是目录: {local_dir}")

            if not self._connection.sftp:
                self._connection._sftp = self._connection.client.open_sftp()

            # 确保远程目录存在
            self._ensure_remote_directory(remote_dir)

            logger.info(f"上传目录: {local_dir} -> {remote_dir}")

            total_bytes = 0
            transferred_bytes = 0

            # 计算总大小
            for filepath in local_dir.rglob("*"):
                if filepath.is_file():
                    total_bytes += filepath.stat().st_size

            # 递归上传
            for filepath in local_dir.rglob("*"):
                if filepath.is_file():
                    # 计算相对路径
                    rel_path = filepath.relative_to(local_dir)
                    remote_path = os.path.join(remote_dir, str(rel_path))

                    # 确保远程父目录存在
                    remote_parent = os.path.dirname(remote_path)
                    if remote_parent != remote_dir:
                        self._ensure_remote_directory(remote_parent)

                    # 上传文件
                    self._connection.sftp.put(str(filepath), remote_path)

                    file_size = filepath.stat().st_size
                    transferred_bytes += file_size

                    if callback:
                        callback(transferred_bytes, total_bytes)

            logger.info(f"目录上传成功: {local_dir}")
            return True

        except FileNotFoundError as e:
            logger.error(f"目录上传失败: {str(e)}")
            raise
        except SSHException as e:
            logger.error(f"目录上传失败: {str(e)}")
            raise RuntimeError(f"目录上传失败: {str(e)}")
        except Exception as e:
            logger.error(f"目录上传发生未知错误: {str(e)}")
            raise RuntimeError(f"目录上传失败: {str(e)}")

    def _ensure_remote_directory(self, remote_path: str) -> None:
        """
        确保远程目录存在

        Args:
            remote_path: 远程目录路径
        """
        if not self._connection or not self._connection.sftp:
            return

        try:
            self._connection.sftp.stat(remote_path)
        except FileNotFoundError:
            # 目录不存在，递归创建
            parent = os.path.dirname(remote_path)
            if parent and parent != remote_path:
                self._ensure_remote_directory(parent)
            self._connection.sftp.mkdir(remote_path)
            logger.debug(f"创建远程目录: {remote_path}")

    def list_directory(self, remote_path: str = ".") -> List[Dict[str, Any]]:
        """
        列出远程目录内容

        Args:
            remote_path: 远程目录路径，默认为当前目录

        Returns:
            文件/目录信息列表，每个元素包含: filename, type(file/dir), size, mtime

        Raises:
            RuntimeError: 未连接或操作失败
        """
        if not self.connected:
            raise RuntimeError("SSH未连接，请先调用connect()方法")

        if not self._connection:
            raise RuntimeError("SSH连接不可用")

        try:
            if not self._connection.sftp:
                self._connection._sftp = self._connection.client.open_sftp()

            files = []
            for entry in self._connection.sftp.listdir_attr(remote_path):
                filename = entry.filename
                is_dir = stat.S_ISDIR(entry.st_mode)
                size = entry.st_size
                mtime = entry.st_mtime

                files.append(
                    {
                        "filename": filename,
                        "type": "dir" if is_dir else "file",
                        "size": size,
                        "mtime": mtime,
                    }
                )

            return files

        except FileNotFoundError:
            raise RuntimeError(f"远程目录不存在: {remote_path}")
        except SSHException as e:
            logger.error(f"列出目录失败: {str(e)}")
            raise RuntimeError(f"列出目录失败: {str(e)}")
        except Exception as e:
            logger.error(f"列出目录发生未知错误: {str(e)}")
            raise RuntimeError(f"列出目录失败: {str(e)}")


# 导入stat模块用于list_directory
import stat


__all__ = [
    "SSHConfig",
    "SSHConnection",
    "SSHConnectionPool",
    "SSHManager",
]
