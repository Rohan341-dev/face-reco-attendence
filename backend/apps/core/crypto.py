"""Authenticated-encryption helpers for secrets at rest (MFA secrets,
biometric templates). AES-256-GCM with a key derived from the configured
BIOMETRIC_KEY_BASE64 (falling back to SECRET_KEY in development only)."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_prefix = "enc:v1:"


def _derive_key() -> bytes:
    material = os.environ.get("BIOMETRIC_KEY_BASE64", "")
    if material:
        root = base64.b64decode(material)
    else:  # development fallback; prod must set BIOMETRIC_KEY_BASE64
        root = hashlib.sha256(os.environ.get("SECRET_KEY", "insecure-dev-key").encode()).digest()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b"facetrack-secrets-v1", info=None).derive(root)


_key: bytes | None = None


def _get_key() -> bytes:
    global _key
    if _key is None:
        _key = _derive_key()
    return _key


def encrypt_text(plaintext: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_get_key()).encrypt(nonce, plaintext.encode(), None)
    return _prefix + base64.b64encode(nonce + ct).decode()


def decrypt_text(token: str) -> str:
    if not token.startswith(_prefix):
        raise ValueError("Unencrypted value where encrypted text expected")
    raw = base64.b64decode(token[len(_prefix):])
    try:
        pt = AESGCM(_get_key()).decrypt(raw[:12], raw[12:], None)
    except InvalidTag as exc:
        raise ValueError("Decryption failed (wrong key or tampered data)") from exc
    return pt.decode()


def encrypt_bytes(data: bytes) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_get_key()).encrypt(nonce, data, None)
    return _prefix + base64.b64encode(nonce + ct).decode()


def decrypt_bytes(token: str) -> bytes:
    if not token.startswith(_prefix):
        raise ValueError("Unencrypted value where encrypted bytes expected")
    raw = base64.b64decode(token[len(_prefix):])
    try:
        return AESGCM(_get_key()).decrypt(raw[:12], raw[12:], None)
    except InvalidTag as exc:
        raise ValueError("Decryption failed (wrong key or tampered data)") from exc
