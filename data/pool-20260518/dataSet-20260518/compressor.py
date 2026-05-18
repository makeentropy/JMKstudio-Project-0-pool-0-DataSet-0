import os
import zipfile
import tarfile
import gzip
from ..utils.logging import setup_logger

logger = setup_logger('compressor')

class DataCompressor:
    def __init__(self):
        self.supported_formats = ['zip', 'tar.gz', 'gz']
    
    def compress_zip(self, source_path, output_path):
        try:
            logger.info(f'Compressing {source_path} to {output_path} (ZIP)')
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.isfile(source_path):
                    zf.write(source_path, os.path.basename(source_path))
                else:
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, source_path)
                            zf.write(file_path, arcname)
            return output_path
        except Exception as e:
            logger.error(f'Failed to compress ZIP: {e}')
            return None
    
    def compress_tar_gz(self, source_path, output_path):
        try:
            logger.info(f'Compressing {source_path} to {output_path} (TAR.GZ)')
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(source_path, arcname=os.path.basename(source_path))
            return output_path
        except Exception as e:
            logger.error(f'Failed to compress TAR.GZ: {e}')
            return None
    
    def compress_gz(self, source_path, output_path=None):
        try:
            if not output_path:
                output_path = source_path + '.gz'
            logger.info(f'Compressing {source_path} to {output_path} (GZ)')
            with open(source_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return output_path
        except Exception as e:
            logger.error(f'Failed to compress GZ: {e}')
            return None
    
    def compress(self, source_path, output_path=None, format='zip'):
        if not output_path:
            if os.path.isdir(source_path):
                output_path = f'{source_path}.{format}'
            else:
                name, ext = os.path.splitext(source_path)
                output_path = f'{name}.{format}'
        
        if format == 'zip':
            return self.compress_zip(source_path, output_path)
        elif format == 'tar.gz':
            return self.compress_tar_gz(source_path, output_path)
        elif format == 'gz' and os.path.isfile(source_path):
            return self.compress_gz(source_path, output_path)
        else:
            logger.error(f'Unsupported format: {format}')
            return None

import shutil
