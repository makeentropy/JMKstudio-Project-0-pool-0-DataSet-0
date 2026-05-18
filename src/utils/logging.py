import logging
import os
from datetime import datetime
from .config import LOG_DIR, ensure_dir

def setup_logger(name='data_collector', level=logging.INFO):
    ensure_dir(LOG_DIR)
    log_file = os.path.join(LOG_DIR, f'{datetime.now().strftime("%Y%m%d")}.log')
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file)
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger
