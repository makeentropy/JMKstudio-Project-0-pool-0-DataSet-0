import os
import shutil
from datetime import datetime
from ..utils.logging import setup_logger
from ..utils.config import get_dataset_dir, ensure_dir
from ..utils.helpers import get_file_info, save_json

logger = setup_logger('data_collector')

class DataCollector:
    def __init__(self, entries):
        self.entries = entries
        self.dataset_dir = ensure_dir(get_dataset_dir())
        self.collected_files = []
        self.logs = []
    
    def collect_path(self, entry):
        path = entry.get('path', '')
        if not path:
            return []
        
        collected = []
        try:
            if os.path.isfile(path):
                collected.append(self._collect_file(path, entry))
            elif os.path.isdir(path):
                collected.extend(self._collect_directory(path, entry))
            else:
                logger.warning(f'Path does not exist: {path}')
        except Exception as e:
            logger.error(f'Error collecting {path}: {e}')
            self._add_log(entry, f'Error: {str(e)}')
        
        return collected
    
    def _collect_file(self, file_path, entry):
        logger.info(f'Collecting file: {file_path}')
        
        file_info = get_file_info(file_path)
        dest_path = os.path.join(self.dataset_dir, os.path.basename(file_path))
        
        counter = 1
        while os.path.exists(dest_path):
            name, ext = os.path.splitext(os.path.basename(file_path))
            dest_path = os.path.join(self.dataset_dir, f'{name}_{counter}{ext}')
            counter += 1
        
        shutil.copy2(file_path, dest_path)
        file_info['dest_path'] = dest_path
        file_info['entry_info'] = entry
        
        self.collected_files.append(file_info)
        self._add_log(entry, f'Collected file: {file_path} -> {dest_path}')
        
        return file_info
    
    def _collect_directory(self, dir_path, entry):
        logger.info(f'Collecting directory: {dir_path}')
        collected = []
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                collected.append(self._collect_file(file_path, entry))
        
        return collected
    
    def _add_log(self, entry, message):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'path': entry.get('path', ''),
            'message': message,
            'rule': entry.get('rule', ''),
            'information': entry.get('information', '')
        }
        self.logs.append(log_entry)
    
    def collect_all(self):
        logger.info(f'Starting collection of {len(self.entries)} entries')
        
        for entry in self.entries:
            self.collect_path(entry)
        
        self._save_collection_info()
        logger.info(f'Collection complete. Collected {len(self.collected_files)} files')
        
        return self.collected_files
    
    def _save_collection_info(self):
        info_path = os.path.join(self.dataset_dir, 'collection_info.json')
        info = {
            'collected_at': datetime.now().isoformat(),
            'total_files': len(self.collected_files),
            'files': self.collected_files,
            'logs': self.logs
        }
        save_json(info, info_path)
        
        logs_path = os.path.join(self.dataset_dir, 'collection_logs.json')
        save_json(self.logs, logs_path)
