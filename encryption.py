import os
import base64
from typing import Optional

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_MAGIC = b"BC1"  # simple version/tag for payloads
_SALT_LEN = 16
_NONCE_LEN = 12
_ITER = 200_000
_KEY_LEN = 32


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if not isinstance(passphrase, str) or not passphrase:
        raise ValueError("Passphrase required for encryption")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=salt,
        iterations=_ITER,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_text(plaintext: str, passphrase: str) -> str:
    """Encrypt a UTF-8 string with AES-256-GCM using a passphrase.

    Returns base64 text suitable for sending over the wire as a line (append "\n").
    """
    if plaintext is None:
        plaintext = ""
    salt = os.urandom(_SALT_LEN)
    key = _derive_key(passphrase, salt)
    aes = AESGCM(key)
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = _MAGIC + salt + nonce + ciphertext
    return base64.b64encode(payload).decode("ascii")


def decrypt_text(token_b64: str, passphrase: str) -> str:
    """Decrypt a base64 token produced by encrypt_text back to UTF-8 text."""
    raw = base64.b64decode(token_b64.encode("ascii"))
    if len(raw) < 3 + _SALT_LEN + _NONCE_LEN or not raw.startswith(_MAGIC):
        raise ValueError("Invalid message format")
    salt = raw[3 : 3 + _SALT_LEN]
    nonce = raw[3 + _SALT_LEN : 3 + _SALT_LEN + _NONCE_LEN]
    ciphertext = raw[3 + _SALT_LEN + _NONCE_LEN :]
    key = _derive_key(passphrase, salt)
    aes = AESGCM(key)
    plaintext = aes.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
