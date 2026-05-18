import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

GITHUB_REPO_URL = 'https://github.com/makeentropy/JMKstudio-Project-0-pool-0-DataSet-0.git'
DATA_COLLECTS_LIST_URL = 'https://github.com/makeentropy/DataCollectsList.csv'

def get_date_str():
    return datetime.now().strftime('%Y%m%d')

def get_pool_dir():
    return os.path.join(DATA_DIR, f'pool-{get_date_str()}')

def get_dataset_dir():
    return os.path.join(get_pool_dir(), f'dataSet-{get_date_str()}')

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path
