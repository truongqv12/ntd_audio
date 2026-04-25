import hashlib
from pathlib import Path
from uuid import uuid4

from .config import settings


def write_artifact(*, provider_key: str, suffix: str, content: bytes) -> tuple[str, int, str]:
    folder = settings.artifact_root / provider_key
    folder.mkdir(parents=True, exist_ok=True)
    sha256_hex = hashlib.sha256(content).hexdigest()
    filename = f"{uuid4()}.{suffix.lstrip('.')}"
    path = folder / filename
    path.write_bytes(content)
    relative = str(path.relative_to(settings.artifact_root))
    return relative, len(content), sha256_hex


def artifact_absolute_path(relative_path: str) -> Path:
    return settings.artifact_root / relative_path
