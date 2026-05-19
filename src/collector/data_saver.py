import json
import os
from datetime import datetime
from typing import Dict, List


class DataSaver:
    def __init__(self, base_dir: str = 'data/raw'):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_json(self, data: Dict, filename: Optional[str] = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data_{timestamp}.json'
        
        filepath = os.path.join(self.base_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

    def save_batch_json(self, data_list: List[Dict], filename: Optional[str] = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'batch_data_{timestamp}.json'
        
        filepath = os.path.join(self.base_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        
        return filepath

    def load_json(self, filepath: str) -> Dict:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
