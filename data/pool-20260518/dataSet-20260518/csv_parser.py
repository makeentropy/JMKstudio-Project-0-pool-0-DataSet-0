import csv
import requests
import os
from io import StringIO
from datetime import datetime
from ..utils.logging import setup_logger
from ..utils.config import DATA_DIR, ensure_dir

logger = setup_logger('csv_parser')

class DataCollectsListParser:
    def __init__(self, url=None, local_path=None):
        self.url = url
        self.local_path = local_path
        self.entries = []
    
    def fetch_from_github(self, url):
        try:
            logger.info(f'Fetching DataCollectsList.csv from {url}')
            response = requests.get(url)
            response.raise_for_status()
            return StringIO(response.text)
        except Exception as e:
            logger.error(f'Failed to fetch from GitHub: {e}')
            return None
    
    def load_local(self, path):
        try:
            logger.info(f'Loading DataCollectsList.csv from {path}')
            return open(path, 'r', encoding='utf-8')
        except Exception as e:
            logger.error(f'Failed to load local file: {e}')
            return None
    
    def parse(self):
        f = None
        # 优先尝试本地文件
        if self.local_path:
            f = self.load_local(self.local_path)
        # 如果本地文件失败或不存在，尝试 URL
        if not f and self.url:
            f = self.fetch_from_github(self.url)
        
        if not f:
            logger.error('No valid data source available')
            return []
        
        try:
            reader = csv.DictReader(f)
            self.entries = []
            for row in reader:
                entry = {
                    'path': row.get('path', ''),
                    'rule': row.get('rule', ''),
                    'information': row.get('infomation', ''),
                    'more': row.get('more', ''),
                    'logs': row.get('[logs]', '').split('|') if row.get('[logs]') else [],
                    'collected_at': datetime.now().isoformat()
                }
                self.entries.append(entry)
            
            logger.info(f'Parsed {len(self.entries)} entries from DataCollectsList.csv')
            return self.entries
        except Exception as e:
            logger.error(f'Failed to parse CSV: {e}')
            return []
        finally:
            if f and hasattr(f, 'close'):
                f.close()
    
    def save_entries(self, output_path=None):
        if not output_path:
            output_path = os.path.join(ensure_dir(DATA_DIR), 'collected_entries.json')
        
        from ..utils.helpers import save_json
        save_json(self.entries, output_path)
        logger.info(f'Saved {len(self.entries)} entries to {output_path}')
        return output_path
