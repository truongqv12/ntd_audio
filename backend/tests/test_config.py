from voiceforge.config import _read_version_file, settings


def test_app_version_matches_version_file():
    """settings.app_version must reflect the contents of backend/VERSION."""
    assert settings.app_version == _read_version_file()
    assert settings.app_version != "0.0.0"


def test_app_allowed_origins_csv_parsed():
    """APP_ALLOWED_ORIGINS may be supplied as a CSV string and is parsed into a list."""
    from voiceforge.config import Settings

    parsed = Settings(APP_ALLOWED_ORIGINS="https://a.example,https://b.example , https://c.example")
    assert parsed.app_allowed_origins == [
        "https://a.example",
        "https://b.example",
        "https://c.example",
    ]


def test_app_allowed_origins_csv_from_env(monkeypatch):
    """The env-var path must accept CSV without JSON-decoding (regression).

    Older pydantic-settings releases JSON-decoded list[str] env values *before*
    `mode="before"` validators ran, so a plain `APP_ALLOWED_ORIGINS=http://...`
    in `.env` crashed startup with a JSON parse error. The Annotated `NoDecode`
    marker on the field prevents that.
    """
    from voiceforge.config import Settings

    monkeypatch.setenv("APP_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:4173")
    parsed = Settings(_env_file=None)
    assert parsed.app_allowed_origins == ["http://localhost:5173", "http://localhost:4173"]


def test_app_api_keys_csv_from_env(monkeypatch):
    from voiceforge.config import Settings

    monkeypatch.setenv("APP_API_KEYS", "key-one,key-two")
    parsed = Settings(_env_file=None)
    assert parsed.app_api_keys == ["key-one", "key-two"]


def test_app_allowed_origins_json_array_from_env(monkeypatch):
    """JSON-array form must also work — older pydantic-settings forced this format,
    so users upgrading must not silently get garbage origins."""
    from voiceforge.config import Settings

    monkeypatch.setenv(
        "APP_ALLOWED_ORIGINS", '["http://localhost:5173", "http://localhost:4173"]'
    )
    parsed = Settings(_env_file=None)
    assert parsed.app_allowed_origins == ["http://localhost:5173", "http://localhost:4173"]


def test_app_api_keys_json_array_from_env(monkeypatch):
    from voiceforge.config import Settings

    monkeypatch.setenv("APP_API_KEYS", '["key-a", "key-b"]')
    parsed = Settings(_env_file=None)
    assert parsed.app_api_keys == ["key-a", "key-b"]
