from cryptography.fernet import Fernet

from voiceforge.security import encryption


def _set_key(monkeypatch, key: str) -> None:
    from voiceforge import config as config_module

    monkeypatch.setattr(config_module.settings, "app_encryption_key", key, raising=False)
    encryption.reset_cipher_cache()


def test_roundtrip_encrypts_and_decrypts(monkeypatch):
    _set_key(monkeypatch, Fernet.generate_key().decode())
    encrypted = encryption.encrypt_value("super-secret-token")
    assert encrypted.startswith(encryption.ENCRYPTED_PREFIX)
    assert encryption.is_encrypted(encrypted)
    assert encryption.decrypt_value(encrypted) == "super-secret-token"


def test_decrypt_passes_legacy_plaintext_through(monkeypatch):
    _set_key(monkeypatch, Fernet.generate_key().decode())
    assert encryption.decrypt_value("plain-legacy-value") == "plain-legacy-value"


def test_no_key_falls_back_to_plaintext(monkeypatch):
    _set_key(monkeypatch, "")
    assert encryption.encrypt_value("hello") == "hello"
    assert encryption.decrypt_value("hello") == "hello"


def test_arbitrary_passphrase_is_accepted(monkeypatch):
    _set_key(monkeypatch, "this-is-a-passphrase-not-a-fernet-key")
    encrypted = encryption.encrypt_value("api-key-123")
    assert encrypted.startswith(encryption.ENCRYPTED_PREFIX)
    assert encryption.decrypt_value(encrypted) == "api-key-123"
