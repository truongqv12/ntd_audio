"""Thin wrapper that routes artifact writes through the configured backend.

The legacy `write_artifact` API stays the same — callers get back
`(relative_key, size, sha256_hex)` — but bytes now flow through
`services.storage.get_storage()` so an operator who sets `STORAGE_BACKEND=s3`
or points `ARTIFACT_ROOT` at a NAS / external HDD has a single seam.

Reading (`artifact_absolute_path`) is still local-fs only: `FileResponse`
needs a path on disk. S3 reads / downloads are intentionally not in scope
for T2.8; that's a separate piece of work to add a redirect or stream-back
in the download routes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from .config import settings
from .services.storage import get_storage


def write_artifact(*, provider_key: str, suffix: str, content: bytes) -> tuple[str, int, str]:
    relative = f"{provider_key}/{uuid4()}.{suffix.lstrip('.')}"
    sha256_hex = hashlib.sha256(content).hexdigest()
    get_storage().write_bytes(relative, content)
    return relative, len(content), sha256_hex


def artifact_absolute_path(relative_path: str) -> Path:
    return settings.artifact_root / relative_path
