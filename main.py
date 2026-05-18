#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.collector.csv_parser import DataCollectsListParser
from src.collector.data_collector import DataCollector
from src.processor.data_processor import DataProcessor
from src.encryptor.compressor import DataCompressor
from src.encryptor.gpg_encryptor import GPGEncryptor
from src.encryptor.database import DictionaryDatabase
from src.git_manager.git_manager import GitManager
from src.utils.logging import setup_logger
from src.utils.config import DATA_COLLECTS_LIST_URL, DATA_DIR, get_pool_dir, get_dataset_dir

logger = setup_logger('main')

def parse_args():
    parser = argparse.ArgumentParser(description='Data Collection and Processing Agent')
    parser.add_argument('--csv-url', help='URL to DataCollectsList.csv', default=DATA_COLLECTS_LIST_URL)
    parser.add_argument('--csv-local', help='Local path to DataCollectsList.csv')
    parser.add_argument('--compress', action='store_true', help='Compress collected data')
    parser.add_argument('--encrypt', action='store_true', help='Encrypt collected data')
    parser.add_argument('--gpg-key', help='GPG key ID for encryption')
    parser.add_argument('--gpg-passphrase', help='GPG passphrase for symmetric encryption')
    parser.add_argument('--git-push', action='store_true', help='Push to Git repository')
    parser.add_argument('--git-url', help='Git repository URL')
    parser.add_argument('--git-branch', default='main', help='Git branch')
    parser.add_argument('--no-process', action='store_true', help='Skip data processing/distillation')
    parser.add_argument('--create-db', action='store_true', help='Create dictionary database')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    logger.info('=' * 60)
    logger.info('Data Collection and Processing Agent Starting')
    logger.info('=' * 60)
    
    try:
        logger.info('Step 1: Parsing DataCollectsList.csv')
        parser = DataCollectsListParser(url=args.csv_url, local_path=args.csv_local)
        entries = parser.parse()
        
        if not entries:
            logger.error('No entries found in DataCollectsList.csv')
            return 1
        
        parser.save_entries()
        
        logger.info('Step 2: Collecting data')
        collector = DataCollector(entries)
        collected_files = collector.collect_all()
        
        if not collected_files:
            logger.warning('No files collected')
            return 0
        
        dataset_dir = get_dataset_dir()
        
        if not args.no_process:
            logger.info('Step 3: Processing and distilling dataset')
            processor = DataProcessor(dataset_dir)
            processor.process()
        
        if args.create_db:
            logger.info('Step 4: Creating dictionary database')
            db_path = os.path.join(dataset_dir, 'dataset_db.pkl.gz')
            db = DictionaryDatabase(db_path)
            
            for file_info in collected_files:
                key = file_info['hash']
                metadata = {
                    'path': file_info['path'],
                    'dest_path': file_info['dest_path'],
                    'size': file_info['size'],
                    'modified': file_info['modified']
                }
                db.add(key, file_info['dest_path'], metadata)
            
            logger.info(f'Database created with {len(collected_files)} entries')
        
        if args.compress:
            logger.info('Step 5: Compressing dataset')
            compressor = DataCompressor()
            compressed_path = compressor.compress(dataset_dir, format='zip')
            if compressed_path:
                logger.info(f'Compressed to: {compressed_path}')
        
        if args.encrypt:
            logger.info('Step 6: Encrypting data')
            encryptor = GPGEncryptor(key_id=args.gpg_key, passphrase=args.gpg_passphrase)
            
            for file_info in collected_files:
                encryptor.encrypt_file(file_info['dest_path'])
        
        if args.git_push:
            logger.info('Step 7: Pushing to Git')
            git_manager = GitManager(get_pool_dir())
            git_url = args.git_url or None
            git_manager.full_push(
                message=f'Data collection {datetime.now().isoformat()}',
                url=git_url,
                branch=args.git_branch
            )
        
        logger.info('=' * 60)
        logger.info('Process completed successfully!')
        logger.info(f'  Dataset directory: {dataset_dir}')
        logger.info(f'  Collected files: {len(collected_files)}')
        logger.info('=' * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f'Process failed: {e}', exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
