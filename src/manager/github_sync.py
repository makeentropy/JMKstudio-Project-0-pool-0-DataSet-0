import os
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from .sync import GitSync


class GitHubDataPool:
    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        token: Optional[str] = None,
        repo_path: Optional[str] = None
    ):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.git_sync = GitSync(repo_path)
        self.base_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def get_repo_info(self) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(self.base_api_url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def get_repo_contents(self, path: str = "") -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_api_url}/contents/{path}"
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return []

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_api_url}/issues"
            data = {"title": title, "body": body}
            if labels:
                data["labels"] = labels
            response = requests.post(url, json=data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def create_pull_request(
        self,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_api_url}/pulls"
            data = {
                "title": title,
                "head": head,
                "base": base,
                "body": body or ""
            }
            response = requests.post(url, json=data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def get_clone_url(self, use_ssh: bool = False) -> str:
        if use_ssh:
            return f"git@github.com:{self.repo_owner}/{self.repo_name}.git"
        elif self.token:
            return f"https://{self.token}@github.com/{self.repo_owner}/{self.repo_name}.git"
        else:
            return f"https://github.com/{self.repo_owner}/{self.repo_name}.git"

    def sync_from_github(self, branch: str = "main") -> bool:
        clone_url = self.get_clone_url()
        return self.git_sync.pull("origin", branch)

    def sync_to_github(
        self,
        branch: str = "main",
        commit_message: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        if user_name and user_email:
            self.git_sync.set_user(user_name, user_email)
        clone_url = self.get_clone_url()
        return self.git_sync.sync_data_pool(clone_url, branch, commit_message)

    def sync_with_pr(
        self,
        base_branch: str = "main",
        feature_branch: Optional[str] = None,
        pr_title: Optional[str] = None,
        pr_body: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if feature_branch is None:
            feature_branch = f"update-data-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if pr_title is None:
            pr_title = f"Update data pool - {datetime.now().strftime('%Y-%m-%d')}"
        
        clone_url = self.get_clone_url()
        
        if not self.git_sync.is_git_repo():
            self.git_sync.init_repo()
            self.git_sync.add_remote("origin", clone_url)
        
        self.git_sync.fetch()
        self.git_sync.checkout(base_branch)
        self.git_sync.pull("origin", base_branch)
        self.git_sync.create_branch(feature_branch)
        self.git_sync.add()
        
        if user_name and user_email:
            self.git_sync.set_user(user_name, user_email)
        
        commit_msg = f"Update data pool - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.git_sync.commit(commit_msg)
        
        if self.git_sync.push("origin", feature_branch):
            return self.create_pull_request(pr_title, feature_branch, base_branch, pr_body)
        return None
