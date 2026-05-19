import re
from typing import Dict, List
import json


class DataCleaner:
    def __init__(self):
        pass

    def clean_text(self, text: str) -> str:
        if not text:
            return ''
        
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

    def clean_data(self, data: Dict) -> Dict:
        cleaned = data.copy()
        
        if 'title' in cleaned:
            cleaned['title'] = self.clean_text(cleaned['title'])
        
        if 'content' in cleaned:
            cleaned['content'] = self.clean_text(cleaned['content'])
        
        return cleaned

    def clean_batch(self, data_list: List[Dict]) -> List[Dict]:
        return [self.clean_data(data) for data in data_list]

    def remove_duplicates(self, data_list: List[Dict], key: str = 'url') -> List[Dict]:
        seen = set()
        unique = []
        
        for data in data_list:
            if key in data and data[key] not in seen:
                seen.add(data[key])
                unique.append(data)
        
        return unique

    def filter_by_length(self, data_list: List[Dict], min_len: int = 100) -> List[Dict]:
        return [data for data in data_list if len(data.get('content', '')) >= min_len]
