import os
import json
from datetime import datetime
from typing import Dict, Optional


class ModelManager:
    def __init__(self, model_dir: str = 'models'):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

    def save_model_config(self, config: Dict, model_name: str) -> str:
        config_dir = os.path.join(self.model_dir, model_name)
        os.makedirs(config_dir, exist_ok=True)
        
        config_path = os.path.join(config_dir, 'config.json')
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return config_path

    def load_model_config(self, model_name: str) -> Optional[Dict]:
        config_path = os.path.join(self.model_dir, model_name, 'config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None

    def list_models(self) -> list:
        if not os.path.exists(self.model_dir):
            return []
        
        models = []
        for item in os.listdir(self.model_dir):
            item_path = os.path.join(self.model_dir, item)
            if os.path.isdir(item_path):
                config = self.load_model_config(item)
                if config:
                    models.append({
                        'name': item,
                        'config': config
                    })
        
        return models
