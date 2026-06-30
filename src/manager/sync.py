import subprocess
import os
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime


class GitSync:
    def __init__(self, repo_path: Optional[str] = None):
        if repo_path is None:
            self.repo_path = Path.cwd()
        else:
            self.repo_path = Path(repo_path)
        self.repo_path.mkdir(parents=True, exist_ok=True)

    def _run_command(self, command: List[str]) -> Tuple[str, str, int]:
        try:
            result = subprocess.run(
                command,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def is_git_repo(self) -> bool:
        stdout, stderr, code = self._run_command(["git", "rev-parse", "--is-inside-work-tree"])
        return code == 0 and stdout.strip() == "true"

    def init_repo(self) -> bool:
        if self.is_git_repo():
            return True
        stdout, stderr, code = self._run_command(["git", "init"])
        return code == 0

    def add_remote(self, name: str, url: str) -> bool:
        stdout, stderr, code = self._run_command(["git", "remote", "add", name, url])
        if code != 0 and "already exists" in stderr:
            self._run_command(["git", "remote", "set-url", name, url])
            return True
        return code == 0

    def fetch(self, remote: str = "origin") -> bool:
        stdout, stderr, code = self._run_command(["git", "fetch", remote])
        return code == 0

    def pull(self, remote: str = "origin", branch: str = "main") -> bool:
        stdout, stderr, code = self._run_command(["git", "pull", remote, branch])
        return code == 0

    def add(self, paths: Optional[List[str]] = None) -> bool:
        if paths is None:
            paths = ["."]
        stdout, stderr, code = self._run_command(["git", "add"] + paths)
        return code == 0

    def commit(self, message: str) -> bool:
        stdout, stderr, code = self._run_command(["git", "commit", "-m", message])
        return code == 0

    def push(self, remote: str = "origin", branch: str = "main") -> bool:
        stdout, stderr, code = self._run_command(["git", "push", remote, branch])
        return code == 0

    def create_branch(self, branch_name: str) -> bool:
        stdout, stderr, code = self._run_command(["git", "checkout", "-b", branch_name])
        return code == 0

    def checkout(self, branch_name: str) -> bool:
        stdout, stderr, code = self._run_command(["git", "checkout", branch_name])
        return code == 0

    def get_status(self) -> str:
        stdout, stderr, code = self._run_command(["git", "status"])
        return stdout if code == 0 else stderr

    def get_log(self, limit: int = 10) -> List[str]:
        stdout, stderr, code = self._run_command(["git", "log", f"-{limit}", "--oneline"])
        if code == 0:
            return [line.strip() for line in stdout.splitlines() if line.strip()]
        return []

    def set_user(self, name: str, email: str) -> bool:
        self._run_command(["git", "config", "user.name", name])
        stdout, stderr, code = self._run_command(["git", "config", "user.email", email])
        return code == 0

    def sync_data_pool(self, remote_url: str, branch: str = "main", commit_message: Optional[str] = None) -> bool:
        if not self.is_git_repo():
            self.init_repo()
        self.add_remote("origin", remote_url)
        self.fetch()
        self.pull("origin", branch)
        self.add()
        if commit_message is None:
            commit_message = f"Update data pool - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.commit(commit_message)
        return self.push("origin", branch)
