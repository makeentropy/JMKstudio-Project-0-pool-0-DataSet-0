import json
import os
from typing import Dict, List
from datetime import datetime


class DataFormatter:
    def __init__(self, output_dir: str = 'data/processed'):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def format_for_training(self, data_list: List[Dict]) -> List[Dict]:
        formatted = []
        
        for data in data_list:
            item = {
                'instruction': f"分析以下内容: {data.get('title', '')}",
                'input': data.get('content', ''),
                'output': '',
                'source': data.get('url', ''),
                'timestamp': data.get('timestamp', datetime.now().isoformat())
            }
            formatted.append(item)
        
        return formatted

    def format_as_conversation(self, data_list: List[Dict]) -> List[Dict]:
        conversations = []
        
        for data in data_list:
            conv = {
                'messages': [
                    {
                        'role': 'user',
                        'content': f"请分析关于「{data.get('title', '')}」的内容"
                    },
                    {
                        'role': 'assistant',
                        'content': data.get('content', '')
                    }
                ],
                'metadata': {
                    'source': data.get('url', ''),
                    'timestamp': data.get('timestamp', '')
                }
            }
            conversations.append(conv)
        
        return conversations

    def save_formatted_data(self, data_list: List[Dict], filename: str) -> str:
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        
        return filepath

    def create_dataset(self, train_data: List[Dict], val_data: List[Dict] = None, 
                      test_data: List[Dict] = None, name: str = 'dataset') -> Dict:
        dataset = {
            'name': name,
            'created_at': datetime.now().isoformat(),
            'train': train_data,
            'val': val_data if val_data else [],
            'test': test_data if test_data else []
        }
        
        return dataset
