import base64
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
