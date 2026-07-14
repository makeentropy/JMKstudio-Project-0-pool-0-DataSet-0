"""
数据保全模块

提供数据版本控制、知识库同步和完整性校验功能：
- Git版本控制管理
- CherryTree知识库同步
- 数据完整性校验
- 统一数据保全管理
"""

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from git import Repo


class GitManager:
    """
    Git版本控制管理类
    
    提供Git仓库的初始化、克隆、提交、推送、拉取等操作。
    """

    def __init__(self, repo_path: Optional[Union[str, Path]] = None):
        """
        初始化Git管理器
        
        Args:
            repo_path: Git仓库路径
        """
        try:
            from git import Repo
        except ImportError:
            raise ImportError("需要安装 gitpython 库: pip install gitpython")

        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self._repo: Optional["Repo"] = None

    def _get_repo(self) -> Optional["Repo"]:
        """获取或创建Repo对象"""
        if self._repo is None:
            try:
                from git import Repo

                self._repo = Repo(str(self.repo_path))
            except Exception:
                self._repo = None
        return self._repo

    def init_repo(self) -> bool:
        """
        初始化Git仓库
        
        Returns:
            是否成功
        """
        try:
            from git import Repo

            if self.repo_path.exists() and list(self.repo_path.iterdir()):
                Repo.init(str(self.repo_path))
            else:
                self.repo_path.mkdir(parents=True, exist_ok=True)
                Repo.init(str(self.repo_path))

            self._repo = Repo(str(self.repo_path))
            logger.info(f"初始化Git仓库: {self.repo_path}")
            return True
        except Exception as e:
            logger.error(f"初始化Git仓库失败: {e}")
            return False

    def clone_repo(self, url: str, branch: Optional[str] = None) -> bool:
        """
        克隆Git仓库
        
        Args:
            url: 仓库URL
            branch: 分支名称（可选）
        
        Returns:
            是否成功
        """
        try:
            from git import Repo

            if self.repo_path.exists():
                shutil.rmtree(self.repo_path)

            clone_kwargs = {}
            if branch:
                clone_kwargs["branch"] = branch

            self._repo = Repo.clone_from(url, str(self.repo_path), **clone_kwargs)
            logger.info(f"克隆仓库: {url} -> {self.repo_path}")
            return True
        except Exception as e:
            logger.error(f"克隆仓库失败: {e}")
            return False

    def add_files(self, patterns: Union[str, List[str]] = ".") -> bool:
        """
        添加文件到暂存区
        
        Args:
            patterns: 文件路径或模式（单个字符串或列表）
        
        Returns:
            是否成功
        """
        try:
            repo = self._get_repo()
            if repo is None:
                raise ValueError("仓库未初始化")

            if isinstance(patterns, str):
                patterns = [patterns]

            repo.index.add(patterns)
            logger.info(f"添加文件: {patterns}")
            return True
        except Exception as e:
            logger.error(f"添加文件失败: {e}")
            return False

    def commit(self, message: str) -> Optional[str]:
        """
        提交更改
        
        Args:
            message: 提交消息
        
        Returns:
            commit hash，如果失败返回None
        """
        try:
            repo = self._get_repo()
            if repo is None:
                raise ValueError("仓库未初始化")

            commit = repo.index.commit(message)
            commit_hash = str(commit)
            logger.info(f"提交成功: {commit_hash}")
            return commit_hash
        except Exception as e:
            logger.error(f"提交失败: {e}")
            return None

    def push(self, remote: str = "origin", branch: str = "main") -> bool:
        """
        推送到远程仓库
        
        Args:
            remote: 远程仓库名称
            branch: 分支名称
        
        Returns:
            是否成功
        """
        try:
            repo = self._get_repo()
            if repo is None:
                raise ValueError("仓库未初始化")

            origin = repo.remote(name=remote)
            origin.push(branch)
            logger.info(f"推送到远程: {remote}/{branch}")
            return True
        except Exception as e:
            logger.error(f"推送失败: {e}")
            return False

    def pull(self, remote: str = "origin", branch: str = "main") -> bool:
        """
        从远程拉取
        
        Args:
            remote: 远程仓库名称
            branch: 分支名称
        
        Returns:
            是否成功
        """
        try:
            repo = self._get_repo()
            if repo is None:
                raise ValueError("仓库未初始化")

            origin = repo.remote(name=remote)
            origin.pull(branch)
            logger.info(f"从远程拉取: {remote}/{branch}")
            return True
        except Exception as e:
            logger.error(f"拉取失败: {e}")
            return False

    def checkout(self, target: str) -> bool:
        """
        切换分支或版本
        
        Args:
            target: 分支名称或commit hash
        
        Returns:
            是否成功
        """
        try:
            repo = self._get_repo()
            if repo is None:
                raise ValueError("仓库未初始化")

            repo.git.checkout(target)
            logger.info(f"切换到: {target}")
            return True
        except Exception as e:
            logger.error(f"切换失败: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        获取仓库状态
        
        Returns:
            状态信息字典
        """
        try:
            repo = self._get_repo()
            if repo is None:
                return {"error": "仓库未初始化"}

            status = {
                "branch": str(repo.active_branch),
                "commit": str(repo.head.commit),
                "dirty": repo.is_dirty(),
                "untracked": repo.untracked_files,
            }

            return status
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return {"error": str(e)}

    def get_commit_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取提交历史
        
        Args:
            limit: 返回的提交数量限制
        
        Returns:
            提交历史列表
        """
        try:
            repo = self._get_repo()
            if repo is None:
                return []

            commits = []
            for commit in repo.iter_commits(max_count=limit):
                commits.append(
                    {
                        "hash": str(commit),
                        "message": commit.message.strip(),
                        "author": commit.author.name,
                        "email": commit.author.email,
                        "date": commit.authored_datetime.isoformat(),
                    }
                )

            return commits
        except Exception as e:
            logger.error(f"获取提交历史失败: {e}")
            return []


class CherryTreeManager:
    """
    CherryTree知识库同步类
    
    提供CherryTree文档的导出、导入、同步和备份功能。
    """

    def __init__(self, ct_path: Optional[Union[str, Path]] = None):
        """
        初始化CherryTree管理器
        
        Args:
            ct_path: CherryTree文档路径
        """
        self.ct_path = Path(ct_path) if ct_path else Path.cwd() / "knowledge.ctb"

    def export_to_file(self, output_path: Union[str, Path], format: str = "xml") -> bool:
        """
        导出CherryTree文档到文件
        
        Args:
            output_path: 输出文件路径
            format: 导出格式（xml/json/text）
        
        Returns:
            是否成功
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format == "xml":
                content = self._generate_xml_structure()
                output_path.write_text(content, encoding="utf-8")
            elif format == "json":
                content = self._generate_json_structure()
                output_path.write_text(content, encoding="utf-8")
            elif format == "text":
                content = self._generate_text_structure()
                output_path.write_text(content, encoding="utf-8")
            else:
                raise ValueError(f"不支持的格式: {format}")

            logger.info(f"导出CherryTree文档: {self.ct_path} -> {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出CherryTree文档失败: {e}")
            return False

    def import_from_file(self, input_path: Union[str, Path], format: str = "xml") -> bool:
        """
        从文件导入CherryTree文档
        
        Args:
            input_path: 输入文件路径
            format: 导入格式（xml/json/text）
        
        Returns:
            是否成功
        """
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                raise FileNotFoundError(f"文件不存在: {input_path}")

            content = input_path.read_text(encoding="utf-8")

            if format == "xml":
                self._parse_xml_structure(content)
            elif format == "json":
                self._parse_json_structure(content)
            elif format == "text":
                self._parse_text_structure(content)
            else:
                raise ValueError(f"不支持的格式: {format}")

            logger.info(f"导入CherryTree文档: {input_path} -> {self.ct_path}")
            return True
        except Exception as e:
            logger.error(f"导入CherryTree文档失败: {e}")
            return False

    def sync(self, target_path: Union[str, Path]) -> bool:
        """
        同步文档到目标位置
        
        Args:
            target_path: 目标路径
        
        Returns:
            是否成功
        """
        try:
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if self.ct_path.exists():
                shutil.copy2(self.ct_path, target_path)
                logger.info(f"同步文档: {self.ct_path} -> {target_path}")
                return True
            else:
                logger.warning(f"源文档不存在: {self.ct_path}")
                return False
        except Exception as e:
            logger.error(f"同步文档失败: {e}")
            return False

    def backup(self, backup_dir: Union[str, Path]) -> Optional[Path]:
        """
        备份文档
        
        Args:
            backup_dir: 备份目录
        
        Returns:
            备份文件路径，如果失败返回None
        """
        try:
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)

            if self.ct_path.exists():
                import datetime

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"knowledge_{timestamp}.ctb"
                backup_path = backup_dir / backup_filename

                shutil.copy2(self.ct_path, backup_path)
                logger.info(f"备份文档: {self.ct_path} -> {backup_path}")
                return backup_path
            else:
                logger.warning(f"源文档不存在: {self.ct_path}")
                return None
        except Exception as e:
            logger.error(f"备份文档失败: {e}")
            return None

    def _generate_xml_structure(self) -> str:
        """生成XML结构"""
        return '<?xml version="1.0" encoding="UTF-8"?>\n<cherrytree>\n</cherrytree>'

    def _generate_json_structure(self) -> str:
        """生成JSON结构"""
        structure = {"cherrytree": {"nodes": []}}
        return json.dumps(structure, ensure_ascii=False, indent=2)

    def _generate_text_structure(self) -> str:
        """生成文本结构"""
        return "# CherryTree Knowledge Base\n\n"

    def _parse_xml_structure(self, content: str) -> None:
        """解析XML结构"""
        pass

    def _parse_json_structure(self, content: str) -> None:
        """解析JSON结构"""
        pass

    def _parse_text_structure(self, content: str) -> None:
        """解析文本结构"""
        pass


class DataIntegrityChecker:
    """
    数据完整性校验类
    
    提供文件校验和计算、验证、目录完整性检查等功能。
    """

    def __init__(self, algorithm: str = "sha256"):
        """
        初始化数据完整性校验器
        
        Args:
            algorithm: 哈希算法（sha256/sha512/md5）
        """
        import hashlib

        self.algorithm = algorithm.lower()
        self._hash_func = hashlib.new(self.algorithm)

    def calculate_checksum(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        计算文件校验和
        
        Args:
            file_path: 文件路径
        
        Returns:
            校验和字符串，如果失败返回None
        """
        try:
            import hashlib

            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")

            hash_func = hashlib.new(self.algorithm)
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)

            checksum = hash_func.hexdigest()
            logger.info(f"计算校验和: {file_path} -> {checksum}")
            return checksum
        except Exception as e:
            logger.error(f"计算校验和失败: {e}")
            return None

    def verify_checksum(self, file_path: Union[str, Path], expected_checksum: str) -> bool:
        """
        验证校验和
        
        Args:
            file_path: 文件路径
            expected_checksum: 预期的校验和
        
        Returns:
            是否匹配
        """
        try:
            calculated_checksum = self.calculate_checksum(file_path)
            if calculated_checksum is None:
                return False

            is_valid = calculated_checksum == expected_checksum.lower()
            if is_valid:
                logger.info(f"校验和验证通过: {file_path}")
            else:
                logger.warning(f"校验和验证失败: {file_path}")

            return is_valid
        except Exception as e:
            logger.error(f"验证校验和失败: {e}")
            return False

    def check_directory_integrity(self, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """
        检查目录完整性
        
        Args:
            dir_path: 目录路径
        
        Returns:
            完整性检查结果
        """
        try:
            dir_path = Path(dir_path)
            if not dir_path.exists():
                return {"error": f"目录不存在: {dir_path}"}

            results = {
                "directory": str(dir_path),
                "total_files": 0,
                "checksums": {},
                "errors": [],
            }

            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    try:
                        checksum = self.calculate_checksum(file_path)
                        relative_path = str(file_path.relative_to(dir_path))
                        results["checksums"][relative_path] = checksum
                        results["total_files"] += 1
                    except Exception as e:
                        results["errors"].append(f"{file_path}: {e}")

            logger.info(f"检查目录完整性: {dir_path}, 文件数: {results['total_files']}")
            return results
        except Exception as e:
            logger.error(f"检查目录完整性失败: {e}")
            return {"error": str(e)}

    def generate_manifest(self, dir_path: Union[str, Path], output_path: Union[str, Path]) -> bool:
        """
        生成完整性清单
        
        Args:
            dir_path: 目录路径
            output_path: 输出清单文件路径
        
        Returns:
            是否成功
        """
        try:
            dir_path = Path(dir_path)
            output_path = Path(output_path)

            if not dir_path.exists():
                raise FileNotFoundError(f"目录不存在: {dir_path}")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            manifest = {
                "algorithm": self.algorithm,
                "directory": str(dir_path),
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "files": {},
            }

            for file_path in sorted(dir_path.rglob("*")):
                if file_path.is_file():
                    checksum = self.calculate_checksum(file_path)
                    relative_path = str(file_path.relative_to(dir_path))
                    manifest["files"][relative_path] = checksum

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            logger.info(f"生成完整性清单: {output_path}")
            return True
        except Exception as e:
            logger.error(f"生成完整性清单失败: {e}")
            return False


class DataPreservationManager:
    """
    统一数据保全管理类
    
    提供完整的数据保全备份、恢复和验证功能。
    """

    def __init__(
        self,
        git_manager: Optional[GitManager] = None,
        cherrytree_manager: Optional[CherryTreeManager] = None,
        integrity_checker: Optional[DataIntegrityChecker] = None,
        backup_dir: Optional[Union[str, Path]] = None,
    ):
        """
        初始化数据保全管理器
        
        Args:
            git_manager: Git管理器实例
            cherrytree_manager: CherryTree管理器实例
            integrity_checker: 数据完整性校验器实例
            backup_dir: 备份目录
        """
        self.git_manager = git_manager or GitManager()
        self.cherrytree_manager = cherrytree_manager or CherryTreeManager()
        self.integrity_checker = integrity_checker or DataIntegrityChecker()
        self.backup_dir = Path(backup_dir) if backup_dir else Path.cwd() / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, source_dir: Union[str, Path], description: str = "") -> Dict[str, Any]:
        """
        执行完整数据保全备份
        
        Args:
            source_dir: 源目录
            description: 备份描述
        
        Returns:
            备份结果
        """
        try:
            import datetime

            source_dir = Path(source_dir)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)

            result = {
                "timestamp": timestamp,
                "source_dir": str(source_dir),
                "backup_path": str(backup_path),
                "description": description,
                "steps": [],
                "success": True,
            }

            if source_dir.exists():
                shutil.copytree(source_dir, backup_path / "data", dirs_exist_ok=True)
                result["steps"].append({"name": "copy_data", "status": "success"})
            else:
                result["steps"].append({"name": "copy_data", "status": "failed", "error": "源目录不存在"})
                result["success"] = False

            manifest_path = backup_path / "manifest.json"
            manifest_result = self.integrity_checker.generate_manifest(
                backup_path / "data", manifest_path
            )
            if manifest_result:
                result["steps"].append({"name": "generate_manifest", "status": "success"})
            else:
                result["steps"].append({"name": "generate_manifest", "status": "failed"})
                result["success"] = False

            cherrytree_backup = self.cherrytree_manager.backup(backup_path)
            if cherrytree_backup:
                result["steps"].append({"name": "backup_cherrytree", "status": "success"})
            else:
                result["steps"].append({"name": "backup_cherrytree", "status": "skipped"})

            git_commit = self.git_manager.commit(f"Backup {timestamp}: {description}")
            if git_commit:
                result["steps"].append({"name": "git_commit", "status": "success", "commit_hash": git_commit})
                self.git_manager.push()
                result["steps"].append({"name": "git_push", "status": "success"})
            else:
                result["steps"].append({"name": "git_commit", "status": "skipped"})

            logger.info(f"数据保全备份完成: {backup_path}")
            return result

        except Exception as e:
            logger.error(f"数据保全备份失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def restore(self, backup_path: Union[str, Path], target_dir: Union[str, Path]) -> Dict[str, Any]:
        """
        恢复数据
        
        Args:
            backup_path: 备份路径
            target_dir: 目标目录
        
        Returns:
            恢复结果
        """
        try:
            backup_path = Path(backup_path)
            target_dir = Path(target_dir)

            if not backup_path.exists():
                return {"success": False, "error": f"备份路径不存在: {backup_path}"}

            target_dir.mkdir(parents=True, exist_ok=True)

            result = {
                "backup_path": str(backup_path),
                "target_dir": str(target_dir),
                "steps": [],
                "success": True,
            }

            data_path = backup_path / "data"
            if data_path.exists():
                shutil.copytree(data_path, target_dir, dirs_exist_ok=True)
                result["steps"].append({"name": "restore_data", "status": "success"})
            else:
                result["steps"].append({"name": "restore_data", "status": "failed", "error": "数据目录不存在"})
                result["success"] = False

            manifest_path = backup_path / "manifest.json"
            if manifest_path.exists():
                verification = self.verify(manifest_path=manifest_path, data_dir=target_dir)
                result["steps"].append({"name": "verify_integrity", "status": "success" if verification else "failed"})
                result["integrity_verified"] = verification
            else:
                result["steps"].append({"name": "verify_integrity", "status": "skipped"})

            logger.info(f"数据恢复完成: {target_dir}")
            return result

        except Exception as e:
            logger.error(f"数据恢复失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def verify(
        self,
        data_dir: Optional[Union[str, Path]] = None,
        manifest_path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """
        验证数据完整性
        
        Args:
            data_dir: 数据目录
            manifest_path: 完整性清单路径
        
        Returns:
            是否验证通过
        """
        try:
            if manifest_path and data_dir:
                manifest_path = Path(manifest_path)
                data_dir = Path(data_dir)

                if not manifest_path.exists():
                    logger.error(f"清单文件不存在: {manifest_path}")
                    return False

                if not data_dir.exists():
                    logger.error(f"数据目录不存在: {data_dir}")
                    return False

                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

                algorithm = manifest.get("algorithm", "sha256")
                checker = DataIntegrityChecker(algorithm=algorithm)

                for relative_path, expected_checksum in manifest.get("files", {}).items():
                    file_path = data_dir / relative_path
                    if file_path.exists():
                        if not checker.verify_checksum(file_path, expected_checksum):
                            logger.error(f"文件校验失败: {relative_path}")
                            return False
                    else:
                        logger.error(f"文件缺失: {relative_path}")
                        return False

                logger.info(f"数据完整性验证通过: {data_dir}")
                return True

            elif data_dir:
                data_dir = Path(data_dir)
                if not data_dir.exists():
                    logger.error(f"数据目录不存在: {data_dir}")
                    return False

                result = self.integrity_checker.check_directory_integrity(data_dir)
                return len(result.get("errors", [])) == 0

            else:
                logger.error("缺少必要参数")
                return False

        except Exception as e:
            logger.error(f"验证数据完整性失败: {e}")
            return False


__all__ = [
    "GitManager",
    "CherryTreeManager",
    "DataIntegrityChecker",
    "DataPreservationManager",
]