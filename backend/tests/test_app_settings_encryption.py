"""Verifies provider-credential secret fields are encrypted at rest in app_settings.value_json."""

from cryptography.fernet import Fernet

from voiceforge.security import encryption


def test_secret_fields_are_encrypted_in_value_json(db_session, monkeypatch):
    from voiceforge import config as config_module
    from voiceforge.models import AppSetting
    from voiceforge.services_app_settings import _get_setting, _upsert_setting

    monkeypatch.setattr(config_module.settings, "app_encryption_key", Fernet.generate_key().decode(), raising=False)
    encryption.reset_cipher_cache()

    secret = "sk-real-openai-key-xxxxxxxxxxxx"
    _upsert_setting(
        db_session,
        "provider_credentials",
        "openai_tts",
        {"openai_api_key": secret, "openai_tts_model": "tts-1"},
        is_secret=True,
    )

    row = db_session.query(AppSetting).filter_by(namespace="provider_credentials", key="openai_tts").one()
    raw = row.value_json
    assert raw["openai_api_key"].startswith(encryption.ENCRYPTED_PREFIX)
    assert raw["openai_tts_model"] == "tts-1"

    decrypted = _get_setting(db_session, "provider_credentials", "openai_tts")
    assert decrypted["openai_api_key"] == secret
    assert decrypted["openai_tts_model"] == "tts-1"


def test_legacy_plaintext_secret_still_readable(db_session, monkeypatch):
    """A row written before encryption was enabled must still decrypt cleanly."""
    from voiceforge import config as config_module
    from voiceforge.models import AppSetting
    from voiceforge.services_app_settings import _get_setting

    monkeypatch.setattr(config_module.settings, "app_encryption_key", Fernet.generate_key().decode(), raising=False)
    encryption.reset_cipher_cache()

    db_session.add(
        AppSetting(
            namespace="provider_credentials",
            key="elevenlabs",
            value_json={"elevenlabs_api_key": "legacy-plaintext", "elevenlabs_model_id": "eleven_v2"},
            is_secret=True,
        )
    )
    db_session.commit()

    decrypted = _get_setting(db_session, "provider_credentials", "elevenlabs")
    assert decrypted["elevenlabs_api_key"] == "legacy-plaintext"
    assert decrypted["elevenlabs_model_id"] == "eleven_v2"
