import os
import hashlib
from collections import defaultdict
from ..utils.logging import setup_logger
from ..utils.helpers import get_file_hash

logger = setup_logger('dataset_distiller')

class DatasetDistiller:
    def __init__(self, dataset_dir):
        self.dataset_dir = dataset_dir
        self.file_groups = defaultdict(list)
    
    def deduplicate_by_hash(self):
        logger.info('Starting deduplication by file hash')
        
        hash_map = {}
        removed_files = []
        
        for root, dirs, files in os.walk(self.dataset_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_hash = get_file_hash(file_path)
                    
                    if file_hash in hash_map:
                        logger.info(f'Duplicate found: {file_path} (matches {hash_map[file_hash]})')
                        removed_files.append(file_path)
                    else:
                        hash_map[file_hash] = file_path
                        
                except Exception as e:
                    logger.error(f'Error processing {file_path}: {e}')
        
        logger.info(f'Found {len(removed_files)} duplicate files')
        return hash_map, removed_files
    
    def group_by_type(self):
        logger.info('Grouping files by type')
        
        type_groups = defaultdict(list)
        
        for root, dirs, files in os.walk(self.dataset_dir):
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                type_groups[ext].append(file_path)
        
        for ext, files in type_groups.items():
            logger.info(f'  {ext}: {len(files)} files')
        
        self.file_groups = type_groups
        return type_groups
    
    def generate_index(self):
        logger.info('Generating dataset index')
        
        index = {
            'total_files': 0,
            'total_size': 0,
            'files': [],
            'groups': {}
        }
        
        for root, dirs, files in os.walk(self.dataset_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    stat = os.stat(file_path)
                    file_info = {
                        'path': file_path,
                        'relative_path': os.path.relpath(file_path, self.dataset_dir),
                        'size': stat.st_size,
                        'hash': get_file_hash(file_path),
                        'modified': stat.st_mtime
                    }
                    index['files'].append(file_info)
                    index['total_files'] += 1
                    index['total_size'] += stat.st_size
                except Exception as e:
                    logger.error(f'Error indexing {file_path}: {e}')
        
        index['groups'] = self.group_by_type()
        
        return index
    
    def distill(self):
        logger.info('Starting dataset distillation')
        
        results = {
            'hash_map': {},
            'removed_duplicates': [],
            'index': None,
            'groups': {}
        }
        
        results['hash_map'], results['removed_duplicates'] = self.deduplicate_by_hash()
        results['groups'] = self.group_by_type()
        results['index'] = self.generate_index()
        
        logger.info('Dataset distillation complete')
        return results
