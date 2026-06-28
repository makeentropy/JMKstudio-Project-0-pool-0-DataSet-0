"""
加密模块

提供AES和其他加密算法的实现。
"""

import base64
import os
from typing import Optional, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AESCipher:
    """
    AES加密器
    
    使用AES-256-GCM算法进行加密和解密。
    """
    
    def __init__(self, key: Optional[Union[str, bytes]] = None):
        """
        初始化AES加密器
        
        Args:
            key: 加密密钥，如果不提供则自动生成
        """
        if key is None:
            self.key = os.urandom(32)  # 256-bit key
        elif isinstance(key, str):
            # 从字符串生成密钥
            self.key = self._derive_key(key)
        else:
            self.key = key
        
        if len(self.key) != 32:
            raise ValueError("Key must be 32 bytes (256 bits)")
    
    def _derive_key(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        从密码派生密钥
        
        Args:
            password: 密码字符串
            salt: 盐值
            
        Returns:
            派生的密钥
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())
    
    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """
        加密数据
        
        Args:
            plaintext: 要加密的数据
            
        Returns:
            Base64编码的加密数据
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        
        # 生成随机IV
        iv = os.urandom(16)
        
        # 使用AES-GCM加密
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # 组合IV、tag和密文
        encrypted_data = iv + encryptor.tag + ciphertext
        
        # Base64编码
        return base64.b64encode(encrypted_data).decode("utf-8")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密数据
        
        Args:
            ciphertext: Base64编码的加密数据
            
        Returns:
            解密后的字符串
        """
        # Base64解码
        encrypted_data = base64.b64decode(ciphertext)
        
        # 分离IV、tag和密文
        iv = encrypted_data[:16]
        tag = encrypted_data[16:32]
        ciphertext_bytes = encrypted_data[32:]
        
        # 使用AES-GCM解密
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        
        plaintext = decryptor.update(ciphertext_bytes) + decryptor.finalize()
        
        return plaintext.decode("utf-8")
    
    def encrypt_file(self, filepath: Union[str, os.PathLike], output_filepath: Optional[Union[str, os.PathLike]] = None) -> str:
        """
        加密文件
        
        Args:
            filepath: 要加密的文件路径
            output_filepath: 输出文件路径
            
        Returns:
            输出文件路径
        """
        filepath = os.PathLike(filepath) if isinstance(filepath, str) else filepath
        
        with open(filepath, "rb") as f:
            plaintext = f.read()
        
        ciphertext = self.encrypt(plaintext)
        
        if output_filepath is None:
            output_filepath = str(filepath) + ".enc"
        
        with open(output_filepath, "w") as f:
            f.write(ciphertext)
        
        logger.info(f"文件已加密: {filepath} -> {output_filepath}")
        return str(output_filepath)
    
    def decrypt_file(self, filepath: Union[str, os.PathLike], output_filepath: Optional[Union[str, os.PathLike]] = None) -> str:
        """
        解密文件
        
        Args:
            filepath: 要解密的文件路径
            output_filepath: 输出文件路径
            
        Returns:
            输出文件路径
        """
        filepath = os.PathLike(filepath) if isinstance(filepath, str) else filepath
        
        with open(filepath, "r") as f:
            ciphertext = f.read()
        
        plaintext = self.decrypt(ciphertext)
        
        if output_filepath is None:
            # 移除.enc后缀
            output_filepath = str(filepath).rstrip(".enc")
        
        with open(output_filepath, "wb") as f:
            f.write(plaintext.encode("utf-8"))
        
        logger.info(f"文件已解密: {filepath} -> {output_filepath}")
        return str(output_filepath)


class Encryptor:
    """
    通用加密器
    
    提供多种加密算法的支持。
    """
    
    def __init__(self, algorithm: str = "AES-256-GCM", key: Optional[Union[str, bytes]] = None):
        """
        初始化加密器
        
        Args:
            algorithm: 加密算法
            key: 加密密钥
        """
        self.algorithm = algorithm
        self._cipher = AESCipher(key)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """加密数据"""
        return self._cipher.encrypt(data)
    
    def decrypt(self, data: str) -> str:
        """解密数据"""
        return self._cipher.decrypt(data)