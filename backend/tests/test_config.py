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
