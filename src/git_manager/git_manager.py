import os
import subprocess
from datetime import datetime
from ..utils.logging import setup_logger
from ..utils.config import GITHUB_REPO_URL

logger = setup_logger('git_manager')

class GitManager:
    def __init__(self, repo_path):
        self.repo_path = repo_path
    
    def init_repo(self):
        try:
            if not os.path.exists(os.path.join(self.repo_path, '.git')):
                logger.info(f'Initializing git repository at {self.repo_path}')
                subprocess.run(['git', 'init'], cwd=self.repo_path, check=True, capture_output=True, text=True)
                return True
            return True
        except Exception as e:
            logger.error(f'Failed to init repo: {e}')
            return False
    
    def add_remote(self, url=GITHUB_REPO_URL):
        try:
            subprocess.run(['git', 'remote', 'add', 'origin', url], cwd=self.repo_path, check=True, capture_output=True, text=True)
            logger.info(f'Added remote origin: {url}')
            return True
        except subprocess.CalledProcessError:
            try:
                subprocess.run(['git', 'remote', 'set-url', 'origin', url], cwd=self.repo_path, check=True, capture_output=True, text=True)
                logger.info(f'Updated remote origin: {url}')
                return True
            except Exception as e:
                logger.error(f'Failed to set remote: {e}')
                return False
    
    def add_all(self):
        try:
            subprocess.run(['git', 'add', '.'], cwd=self.repo_path, check=True, capture_output=True, text=True)
            logger.info('Added all files')
            return True
        except Exception as e:
            logger.error(f'Failed to add files: {e}')
            return False
    
    def commit(self, message=None):
        if not message:
            message = f'Auto commit {datetime.now().isoformat()}'
        try:
            result = subprocess.run(['git', 'commit', '-m', message], cwd=self.repo_path, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f'Committed: {message}')
                return True
            else:
                logger.warning('Nothing to commit')
                return False
        except Exception as e:
            logger.error(f'Failed to commit: {e}')
            return False
    
    def push(self, branch='main'):
        try:
            logger.info(f'Pushing to {branch}')
            subprocess.run(['git', 'push', '-u', 'origin', branch], cwd=self.repo_path, check=True, capture_output=True, text=True)
            logger.info('Push successful')
            return True
        except Exception as e:
            logger.error(f'Failed to push: {e}')
            return False
    
    def full_push(self, message=None, url=GITHUB_REPO_URL, branch='main'):
        logger.info('Starting full git push process')
        
        if not self.init_repo():
            return False
        
        if not self.add_remote(url):
            return False
        
        if not self.add_all():
            return False
        
        self.commit(message)
        
        return self.push(branch)
