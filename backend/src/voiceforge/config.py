from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VoiceForge Studio"
    app_env: str = Field(default="development", alias="APP_ENV")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/voiceforge",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    allow_sqlite_fallback: bool = Field(default=True, alias="ALLOW_SQLITE_FALLBACK")

    artifact_root: Path = Field(default=Path("/data/artifacts"), alias="ARTIFACT_ROOT")
    cache_root: Path = Field(default=Path("/data/cache"), alias="CACHE_ROOT")


    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file_path: Path = Field(default=Path("/data/logs/voiceforge.log"), alias="LOG_FILE_PATH")
    log_max_bytes: int = Field(default=2_000_000, alias="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")

    event_stream_poll_seconds: float = Field(default=2.0, alias="EVENT_STREAM_POLL_SECONDS")

    monitor_docker_socket_path: str = Field(default="/var/run/docker.sock", alias="MONITOR_DOCKER_SOCKET_PATH")
    monitor_container_logs_enabled: bool = Field(default=True, alias="MONITOR_CONTAINER_LOGS_ENABLED")
    preview_sample_text_vi: str = Field(default="Xin chào, đây là bản nghe thử giọng nói.", alias="PREVIEW_SAMPLE_TEXT_VI")
    preview_sample_text_en: str = Field(default="Hello, this is a short preview of the selected voice.", alias="PREVIEW_SAMPLE_TEXT_EN")

    voice_catalog_refresh_on_start: bool = Field(default=True, alias="VOICE_CATALOG_REFRESH_ON_START")

    voicevox_base_url: str = Field(default="http://voicevox:50021", alias="VOICEVOX_BASE_URL")
    voicevox_timeout_seconds: float = Field(default=30.0, alias="VOICEVOX_TIMEOUT_SECONDS")


    piper_base_url: str = Field(default="", alias="PIPER_BASE_URL")
    piper_timeout_seconds: float = Field(default=60.0, alias="PIPER_TIMEOUT_SECONDS")

    kokoro_base_url: str = Field(default="", alias="KOKORO_BASE_URL")
    kokoro_timeout_seconds: float = Field(default=30.0, alias="KOKORO_TIMEOUT_SECONDS")

    vieneu_tts_base_url: str = Field(default="", alias="VIENEU_TTS_BASE_URL")
    vieneu_tts_timeout_seconds: float = Field(default=45.0, alias="VIENEU_TTS_TIMEOUT_SECONDS")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_tts_model: str = Field(default="gpt-4o-mini-tts", alias="OPENAI_TTS_MODEL")

    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_model_id: str = Field(default="eleven_multilingual_v2", alias="ELEVENLABS_MODEL_ID")

    google_tts_access_token: str = Field(default="", alias="GOOGLE_TTS_ACCESS_TOKEN")
    google_tts_project_id: str = Field(default="", alias="GOOGLE_TTS_PROJECT_ID")

    azure_speech_key: str = Field(default="", alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(default="", alias="AZURE_SPEECH_REGION")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
settings.artifact_root.mkdir(parents=True, exist_ok=True)
settings.cache_root.mkdir(parents=True, exist_ok=True)
settings.log_file_path.parent.mkdir(parents=True, exist_ok=True)
