"""Transparent encryption for stored provider secrets.

Reads APP_ENCRYPTION_KEY at first use. Encrypted values are tagged with a
versioned prefix `enc:v1:` so we can read both legacy plaintext and ciphertext
during the rollout window without a forced data migration.
"""

from __future__ import annotations

import base64
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings

logger = logging.getLogger(__name__)

ENCRYPTED_PREFIX = "enc:v1:"


def is_encrypted(value: object) -> bool:
    return isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX)


@lru_cache(maxsize=1)
def _get_cipher() -> Fernet | None:
    """Return a Fernet cipher built from APP_ENCRYPTION_KEY, or None if unset.

    Accepts either a raw 32-byte URL-safe base64 key (Fernet native format)
    or any string ≥32 chars (we'll pad/truncate via SHA256 to derive a key).
    """
    raw = getattr(settings, "app_encryption_key", "")
    if not raw:
        if settings.app_env == "production":
            logger.warning("encryption_key_unset app_env=production secrets_will_be_stored_plaintext")
        return None

    try:
        return Fernet(raw.encode("utf-8"))
    except (ValueError, TypeError):
        # Derive a stable 32-byte key from arbitrary input via SHA-256.
        import hashlib

        digest = hashlib.sha256(raw.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_value(plain: str) -> str:
    """Encrypt a string. Returns the original value if no key is configured."""
    if not isinstance(plain, str) or not plain:
        return plain
    if is_encrypted(plain):
        return plain
    cipher = _get_cipher()
    if cipher is None:
        return plain
    token = cipher.encrypt(plain.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_value(maybe_encrypted: object) -> object:
    """Transparent decrypt: returns plaintext for legacy values, decrypts tagged values."""
    if not is_encrypted(maybe_encrypted):
        return maybe_encrypted
    cipher = _get_cipher()
    if cipher is None:
        logger.warning("encryption_key_missing_for_decrypt — returning ciphertext")
        return maybe_encrypted
    token = maybe_encrypted[len(ENCRYPTED_PREFIX) :]  # type: ignore[index]
    try:
        return cipher.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error("encryption_invalid_token — returning ciphertext")
        return maybe_encrypted


def reset_cipher_cache() -> None:
    """Test hook: drop cached cipher so a new APP_ENCRYPTION_KEY is picked up."""
    _get_cipher.cache_clear()
