import time
import uuid
import base64
import random
import string
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

from app.core.config import settings

class VidsmeSigner:
    def __init__(self):
        self.public_key = self._load_public_key()

    def _load_public_key(self):
        return serialization.load_pem_public_key(
            settings.UPSTREAM_PUBLIC_KEY.encode('utf-8'),
            backend=default_backend()
        )

    def _generate_random_key(self, length=16):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def _rsa_encrypt(self, data: str) -> str:
        encrypted = self.public_key.encrypt(
            data.encode('utf-8'),
            rsa_padding.PKCS1v15()
        )
        return base64.b64encode(encrypted).decode('utf-8')

    def _aes_encrypt(self, data: str, key: str, iv: str) -> str:
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        data_bytes = data.encode('utf-8')
        
        padder = PKCS7(128).padder()
        padded_data = padder.update(data_bytes) + padder.finalize()
        
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend())
        encryptor = cipher.encryptor()
        ct = encryptor.update(padded_data) + encryptor.finalize()
        
        return base64.b64encode(ct).decode('utf-8')

    def generate_signature(self) -> dict:
        random_key = self._generate_random_key(16)
        secret_key = self._rsa_encrypt(random_key)
        
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())
        
        message_to_sign = f"{settings.UPSTREAM_APP_ID}:{settings.UPSTREAM_STATIC_SALT}:{timestamp}:{nonce}:{secret_key}"
        
        sign = self._aes_encrypt(message_to_sign, random_key, random_key)
        
        return {
            "app_id": settings.UPSTREAM_APP_ID,
            "t": timestamp,
            "nonce": nonce,
            "sign": sign,
            "secret_key": secret_key
        }
