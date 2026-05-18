import os
import pickle
import gzip
from datetime import datetime
from ..utils.logging import setup_logger
from ..utils.helpers import save_json, load_json

logger = setup_logger('database')

class DictionaryDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.data = {}
        self.index = {}
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'version': '1.0',
            'entry_count': 0
        }
        self._load()
    
    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with gzip.open(self.db_path, 'rb') as f:
                    db_data = pickle.load(f)
                    self.data = db_data.get('data', {})
                    self.index = db_data.get('index', {})
                    self.metadata = db_data.get('metadata', self.metadata)
                logger.info(f'Loaded database with {len(self.data)} entries')
            except Exception as e:
                logger.error(f'Failed to load database: {e}')
    
    def _save(self):
        try:
            self.metadata['updated_at'] = datetime.now().isoformat()
            self.metadata['entry_count'] = len(self.data)
            
            db_data = {
                'data': self.data,
                'index': self.index,
                'metadata': self.metadata
            }
            
            with gzip.open(self.db_path, 'wb') as f:
                pickle.dump(db_data, f)
            logger.info(f'Saved database with {len(self.data)} entries')
            return True
        except Exception as e:
            logger.error(f'Failed to save database: {e}')
            return False
    
    def add(self, key, value, metadata=None):
        entry = {
            'value': value,
            'metadata': metadata or {},
            'added_at': datetime.now().isoformat()
        }
        self.data[key] = entry
        
        if metadata:
            for k, v in metadata.items():
                if k not in self.index:
                    self.index[k] = {}
                if v not in self.index[k]:
                    self.index[k][v] = []
                if key not in self.index[k][v]:
                    self.index[k][v].append(key)
        
        return self._save()
    
    def get(self, key):
        entry = self.data.get(key)
        if entry:
            return entry['value']
        return None
    
    def get_with_metadata(self, key):
        return self.data.get(key)
    
    def search(self, **filters):
        results = []
        for key, entry in self.data.items():
            match = True
            for k, v in filters.items():
                if entry.get('metadata', {}).get(k) != v:
                    match = False
                    break
            if match:
                results.append((key, entry))
        return results
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            for k in self.index:
                for v in self.index[k]:
                    if key in self.index[k][v]:
                        self.index[k][v].remove(key)
            return self._save()
        return False
    
    def keys(self):
        return list(self.data.keys())
    
    def values(self):
        return [entry['value'] for entry in self.data.values()]
    
    def items(self):
        return [(k, entry['value']) for k, entry in self.data.items()]
