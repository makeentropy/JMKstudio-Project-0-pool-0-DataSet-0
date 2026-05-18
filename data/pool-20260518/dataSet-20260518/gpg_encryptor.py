import os
import subprocess
from ..utils.logging import setup_logger

logger = setup_logger('gpg_encryptor')

class GPGEncryptor:
    def __init__(self, key_id=None, passphrase=None):
        self.key_id = key_id
        self.passphrase = passphrase
    
    def encrypt_file(self, file_path, output_path=None):
        try:
            if not output_path:
                output_path = file_path + '.gpg'
            
            logger.info(f'Encrypting {file_path} to {output_path}')
            
            cmd = ['gpg', '--output', output_path, '--encrypt']
            if self.key_id:
                cmd.extend(['--recipient', self.key_id])
            if self.passphrase:
                cmd.extend(['--symmetric', '--passphrase', self.passphrase, '--batch'])
            
            cmd.append(file_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f'Encryption successful: {output_path}')
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f'Encryption failed: {e.stderr}')
            return None
        except Exception as e:
            logger.error(f'Encryption error: {e}')
            return None
    
    def decrypt_file(self, file_path, output_path=None):
        try:
            if not output_path:
                if file_path.endswith('.gpg'):
                    output_path = file_path[:-4]
                else:
                    output_path = file_path + '.decrypted'
            
            logger.info(f'Decrypting {file_path} to {output_path}')
            
            cmd = ['gpg', '--output', output_path, '--decrypt']
            if self.passphrase:
                cmd.extend(['--passphrase', self.passphrase, '--batch'])
            
            cmd.append(file_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f'Decryption successful: {output_path}')
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f'Decryption failed: {e.stderr}')
            return None
        except Exception as e:
            logger.error(f'Decryption error: {e}')
            return None
    
    def generate_key(self, name, email, passphrase=None):
        try:
            logger.info(f'Generating GPG key for {name} <{email}>')
            batch_script = f'''
%echo Generating a basic OpenPGP key
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: {name}
Name-Email: {email}
Expire-Date: 0
'''
            if passphrase:
                batch_script += f'Passphrase: {passphrase}\n'
            batch_script += '%commit\n%echo done'
            
            result = subprocess.run(
                ['gpg', '--batch', '--gen-key'],
                input=batch_script,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info('Key generation successful')
            return True
        except Exception as e:
            logger.error(f'Key generation failed: {e}')
            return False
