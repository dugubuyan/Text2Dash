"""
加密服务
用于加密和解密敏感信息（数据库密码、MCP认证信息等）
"""
import os
from cryptography.fernet import Fernet
from typing import Optional


class EncryptionService:
    """加密服务类"""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        初始化加密服务
        
        Args:
            key: 加密密钥（32字节URL安全的base64编码字符串）
                 如果为None，则从环境变量ENCRYPTION_KEY读取
                 如果环境变量也不存在，则生成新密钥
        """
        if key is None:
            key_str = os.getenv("ENCRYPTION_KEY")
            if key_str:
                key = key_str.encode()
            else:
                # 生成新密钥并警告
                key = Fernet.generate_key()
                print("警告: 未找到ENCRYPTION_KEY环境变量，已生成新密钥")
                print(f"请将以下密钥添加到.env文件: ENCRYPTION_KEY={key.decode()}")
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        
        Args:
            plaintext: 明文字符串
            
        Returns:
            加密后的字符串（base64编码）
        """
        if not plaintext:
            return ""
        
        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串
        
        Args:
            ciphertext: 密文字符串（base64编码）
            
        Returns:
            解密后的明文字符串
            
        Raises:
            cryptography.fernet.InvalidToken: 如果密文无效或密钥错误
        """
        if not ciphertext:
            return ""
        
        decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()
    
    @staticmethod
    def generate_key() -> str:
        """
        生成新的加密密钥
        
        Returns:
            新生成的密钥（base64编码字符串）
        """
        key = Fernet.generate_key()
        return key.decode()


# 全局加密服务实例
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """获取全局加密服务实例"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


if __name__ == "__main__":
    # 测试加密服务
    service = EncryptionService()
    
    # 测试加密和解密
    original = "my_secret_password"
    encrypted = service.encrypt(original)
    decrypted = service.decrypt(encrypted)
    
    print(f"原文: {original}")
    print(f"密文: {encrypted}")
    print(f"解密: {decrypted}")
    print(f"验证: {original == decrypted}")
    
    # 生成新密钥示例
    print(f"\n新密钥示例: {EncryptionService.generate_key()}")
