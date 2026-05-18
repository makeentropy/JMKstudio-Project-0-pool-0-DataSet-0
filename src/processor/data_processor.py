import os
import json
from datetime import datetime
from ..utils.logging import setup_logger
from ..utils.helpers import save_json, load_json
from .dataset_distiller import DatasetDistiller

logger = setup_logger('data_processor')

class DataProcessor:
    def __init__(self, dataset_dir):
        self.dataset_dir = dataset_dir
        self.distiller = DatasetDistiller(dataset_dir)
    
    def process(self):
        logger.info('Starting data processing pipeline')
        
        results = {}
        
        results['distillation'] = self.distiller.distill()
        
        results['processing_info'] = {
            'processed_at': datetime.now().isoformat(),
            'dataset_dir': self.dataset_dir
        }
        
        self._save_processing_report(results)
        
        logger.info('Data processing complete')
        return results
    
    def _save_processing_report(self, results):
        report_path = os.path.join(self.dataset_dir, 'processing_report.json')
        save_json(results, report_path)
        logger.info(f'Saved processing report to {report_path}')
