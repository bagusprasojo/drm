import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class EncryptedBlob:
    nonce: bytes
    ciphertext: bytes


def load_master_key_from_env(key_b64: str) -> bytes:
    if not key_b64:
        raise ValueError("DRM_MASTER_KEY_B64 is not configured")
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise ValueError("DRM master key must be 32 bytes for AES-256")
    return key


def derive_page_key(master_key: bytes, page_number: int) -> bytes:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(master_key)
    digest.update(str(page_number).encode("utf-8"))
    return digest.finalize()


def generate_content_key() -> bytes:
    return os.urandom(32)


def sha256_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


def encrypt_key_for_storage(master_key: bytes, content_key: bytes) -> str:
    encrypted = aes_gcm_encrypt(master_key, content_key)
    return base64.b64encode(encrypted.nonce + encrypted.ciphertext).decode("ascii")


def decrypt_key_from_storage(master_key: bytes, encrypted_key_b64: str) -> bytes:
    blob = base64.b64decode(encrypted_key_b64)
    nonce = blob[:12]
    ciphertext = blob[12:]
    aesgcm = AESGCM(master_key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def derive_device_wrap_key(device_hash: str) -> bytes:
    return hashlib.sha256(f"ebook-reader-device-wrap-v1|{device_hash}".encode("utf-8")).digest()


def wrap_content_key_for_device(content_key: bytes, device_hash: str) -> str:
    encrypted = aes_gcm_encrypt(derive_device_wrap_key(device_hash), content_key)
    return base64.b64encode(encrypted.nonce + encrypted.ciphertext).decode("ascii")


def wrap_content_key_for_public_key(content_key: bytes, public_key_pem: str) -> str:
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    ciphertext = public_key.encrypt(
        content_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode("ascii")


def aes_gcm_encrypt(page_key: bytes, payload: bytes) -> EncryptedBlob:
    aesgcm = AESGCM(page_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, payload, None)
    return EncryptedBlob(nonce=nonce, ciphertext=ciphertext)


def rsa_sign(private_key_pem: str, data: bytes) -> bytes:
    if not private_key_pem:
        raise ValueError("DRM_RSA_PRIVATE_KEY_PEM is not configured")
    private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())


def build_manifest(payload: Dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
