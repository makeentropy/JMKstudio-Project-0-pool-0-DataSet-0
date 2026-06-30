#!/usr/bin/env python3
"""
示例：使用 GitSync 和 GitHubDataPool 进行数据池同步
"""

import os
from pathlib import Path
from src.manager import GitSync, GitHubDataPool


def git_sync_example():
    """GitSync 基础使用示例"""
    print("=== GitSync 基础使用示例 ===\n")
    
    sync = GitSync(repo_path=str(Path.cwd()))
    
    print("1. 检查是否为 Git 仓库...")
    is_repo = sync.is_git_repo()
    print(f"   是否为 Git 仓库: {is_repo}")
    
    if is_repo:
        print("\n2. 获取 Git 状态...")
        status = sync.get_status()
        print(f"   Git 状态:\n{status}")
        
        print("\n3. 获取最近 5 次提交记录...")
        logs = sync.get_log(limit=5)
        print("   最近提交:")
        for log in logs:
            print(f"   - {log}")


def github_data_pool_example():
    """GitHubDataPool 使用示例"""
    print("\n=== GitHubDataPool 使用示例 ===\n")
    
    repo_owner = "your-username"
    repo_name = "your-data-repo"
    token = os.getenv("GITHUB_TOKEN")
    
    github_pool = GitHubDataPool(
        repo_owner=repo_owner,
        repo_name=repo_name,
        token=token
    )
    
    print("1. 获取仓库信息...")
    repo_info = github_pool.get_repo_info()
    if repo_info:
        print(f"   仓库名称: {repo_info.get('full_name')}")
        print(f"   描述: {repo_info.get('description')}")
        print(f"   星标: {repo_info.get('stargazers_count')}")
    else:
        print("   无法获取仓库信息")
    
    print("\n2. 获取克隆 URL...")
    https_url = github_pool.get_clone_url(use_ssh=False)
    ssh_url = github_pool.get_clone_url(use_ssh=True)
    print(f"   HTTPS URL: {https_url}")
    print(f"   SSH URL: {ssh_url}")


def main():
    git_sync_example()
    github_data_pool_example()
    
    print("\n" + "=" * 50)
    print("注意事项:")
    print("1. 要实际运行同步功能，请设置 GITHUB_TOKEN 环境变量")
    print("2. 请修改 repo_owner 和 repo_name 为实际的仓库信息")
    print("3. 确保本地有 Git 安装且配置正确")
    print("=" * 50)


if __name__ == "__main__":
    main()
