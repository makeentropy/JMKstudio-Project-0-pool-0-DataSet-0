import os
import json
import uuid
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
import zipfile
from pathlib import Path


class DataPool:
    def __init__(self, pool_dir: Optional[str] = None):
        if pool_dir is None:
            pool_dir = os.path.join(os.getcwd(), 'data', 'pool-0')
        self.pool_dir = pool_dir
        os.makedirs(pool_dir, exist_ok=True)
        self.index_file = os.path.join(pool_dir, 'index.json')
        self._init_index()

    def _init_index(self):
        if not os.path.exists(self.index_file):
            index = {
                'datasets': [],
                'metadata': {
                    'pool_id': 'pool-0',
                    'created_at': os.path.getctime(self.pool_dir),
                    'total_datasets': 0
                }
            }
            self._save_index(index)

    def _load_index(self) -> Dict[str, Any]:
        with open(self.index_file, 'r') as f:
            return json.load(f)

    def _save_index(self, index: Dict[str, Any]):
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def create_dataset(self, name: str, description: str = '', 
                      tags: Optional[List[str]] = None) -> Dict[str, Any]:
        dataset_id = str(uuid.uuid4())[:8]
        dataset_dir = os.path.join(self.pool_dir, f'dataSet-{dataset_id}')
        os.makedirs(dataset_dir, exist_ok=True)
        
        dataset = {
            'id': dataset_id,
            'name': name,
            'description': description,
            'tags': tags or [],
            'path': dataset_dir,
            'files': [],
            'created_at': os.path.getctime(dataset_dir),
            'updated_at': os.path.getctime(dataset_dir)
        }
        
        index = self._load_index()
        index['datasets'].append(dataset)
        index['metadata']['total_datasets'] = len(index['datasets'])
        self._save_index(index)
        
        return dataset

    def add_file(self, dataset_id: str, file_path: str, 
                file_type: str = 'data') -> Dict[str, Any]:
        index = self._load_index()
        dataset = next((d for d in index['datasets'] if d['id'] == dataset_id), None)
        
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        filename = os.path.basename(file_path)
        dest_path = os.path.join(dataset['path'], filename)
        
        import shutil
        shutil.copy2(file_path, dest_path)
        
        file_info = {
            'id': str(uuid.uuid4())[:8],
            'filename': filename,
            'path': dest_path,
            'type': file_type,
            'size': os.path.getsize(dest_path),
            'added_at': os.path.getctime(dest_path)
        }
        
        dataset['files'].append(file_info)
        dataset['updated_at'] = os.path.getctime(dest_path)
        self._save_index(index)
        
        return file_info

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        index = self._load_index()
        return next((d for d in index['datasets'] if d['id'] == dataset_id), None)

    def list_datasets(self, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        index = self._load_index()
        datasets = index['datasets']
        
        if tags:
            datasets = [d for d in datasets if any(t in d['tags'] for t in tags)]
        
        return datasets

    def search_datasets(self, query: str) -> List[Dict[str, Any]]:
        index = self._load_index()
        query_lower = query.lower()
        
        results = []
        for ds in index['datasets']:
            if (query_lower in ds['name'].lower() or 
                query_lower in ds['description'].lower() or
                any(query_lower in t.lower() for t in ds['tags'])):
                results.append(ds)
        
        return results

    def package_dataset(self, dataset_id: str, 
                       output_path: Optional[str] = None) -> str:
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        if output_path is None:
            output_path = os.path.join(self.pool_dir, f'{dataset_id}.zip')
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in dataset['files']:
                arcname = os.path.basename(file_info['path'])
                zf.write(file_info['path'], arcname)
        
        return output_path

    def load_dataframe(self, dataset_id: str, 
                      filename: Optional[str] = None) -> pd.DataFrame:
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        if filename:
            file_info = next((f for f in dataset['files'] if f['filename'] == filename), None)
            if not file_info:
                raise ValueError(f"File {filename} not found in dataset")
            files_to_load = [file_info]
        else:
            files_to_load = dataset['files']
        
        dfs = []
        for file_info in files_to_load:
            ext = os.path.splitext(file_info['filename'])[1].lower()
            if ext == '.csv':
                df = pd.read_csv(file_info['path'])
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_info['path'])
            elif ext == '.json':
                df = pd.read_json(file_info['path'])
            else:
                continue
            dfs.append(df)
        
        if not dfs:
            return pd.DataFrame()
        
        if len(dfs) == 1:
            return dfs[0]
        
        return pd.concat(dfs, ignore_index=True)

    def delete_dataset(self, dataset_id: str) -> bool:
        index = self._load_index()
        dataset = next((d for d in index['datasets'] if d['id'] == dataset_id), None)
        
        if not dataset:
            return False
        
        import shutil
        shutil.rmtree(dataset['path'], ignore_errors=True)
        
        index['datasets'] = [d for d in index['datasets'] if d['id'] != dataset_id]
        index['metadata']['total_datasets'] = len(index['datasets'])
        self._save_index(index)
        
        return True
