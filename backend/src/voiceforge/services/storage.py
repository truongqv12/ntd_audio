"""Pluggable artifact storage (Epic 4).

The single-host build writes synthesized audio to the local filesystem under
``ARTIFACT_ROOT``. For multi-instance / cloud deployments we want the same
code path to write to S3 (or any S3-compatible object store) instead.

Callers should depend on the ``ArtifactStorage`` Protocol below, not on the
concrete implementations. ``get_storage()`` resolves the backend from
``settings.storage_backend`` ("local" or "s3"). When S3 is selected we
lazy-import ``boto3`` so the dependency stays optional for local-only setups.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import IO, Protocol

from ..config import settings

logger = logging.getLogger(__name__)


class ArtifactStorage(Protocol):
    """Common surface for any artifact backend."""

    def write_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        """Persist ``data`` under ``key`` and return a stable URL/path the API can serve."""

    def write_stream(self, key: str, stream: IO[bytes], *, content_type: str | None = None) -> str:
        """Persist ``stream`` under ``key`` and return a stable URL/path."""

    def read_bytes(self, key: str) -> bytes:
        """Load and return the raw bytes for ``key``."""

    def exists(self, key: str) -> bool:
        """Return True if ``key`` is present."""

    def delete(self, key: str) -> None:
        """Remove ``key`` (no-op if missing)."""


class LocalArtifactStorage:
    """Write artifacts under ``settings.artifact_root``. Returns a relative URL the API serves."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve ``key`` against the artifact root and refuse anything that escapes it.

        Any caller-controlled key — even one that looks innocuous — must be
        contained inside ``self._root``. Without this check, ``../`` segments
        let the caller read or clobber arbitrary files on the host.
        """
        candidate = (self._root / key).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ValueError(f"artifact key escapes storage root: {key!r}")
        return candidate

    def _path(self, key: str) -> Path:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        target = self._path(key)
        target.write_bytes(data)
        return f"/artifacts/{key}"

    def write_stream(self, key: str, stream: IO[bytes], *, content_type: str | None = None) -> str:
        target = self._path(key)
        with target.open("wb") as fh:
            shutil.copyfileobj(stream, fh)
        return f"/artifacts/{key}"

    def read_bytes(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).exists()
        except ValueError:
            return False

    def delete(self, key: str) -> None:
        target = self._resolve(key)
        if target.exists():
            target.unlink()


class S3ArtifactStorage:
    """S3 / S3-compatible (MinIO, Cloudflare R2, etc.) backend.

    ``boto3`` is imported lazily inside ``__init__`` so it stays optional for
    local-only installs.
    """

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        prefix: str,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires the optional dependency 'boto3'. " "Install with `pip install boto3`."
            ) from exc

        if not bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 requires S3_BUCKET to be set.")

        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""
        self._client = boto3.client(
            "s3",
            region_name=region or None,
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key_id or None,
            aws_secret_access_key=secret_access_key or None,
        )

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key.lstrip('/')}"

    def _public_url(self, full_key: str) -> str:
        return f"s3://{self._bucket}/{full_key}"

    def write_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        full_key = self._full_key(key)
        extra = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self._bucket, Key=full_key, Body=data, **extra)
        return self._public_url(full_key)

    def write_stream(self, key: str, stream: IO[bytes], *, content_type: str | None = None) -> str:
        full_key = self._full_key(key)
        extra = {"ContentType": content_type} if content_type else {}
        self._client.upload_fileobj(stream, self._bucket, full_key, ExtraArgs=extra)
        return self._public_url(full_key)

    def read_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=self._full_key(key))
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._full_key(key))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=self._full_key(key))


_storage_instance: dict[str, ArtifactStorage | None] = {}


def get_storage() -> ArtifactStorage:
    """Return the configured backend (cached)."""
    cached = _storage_instance.get("instance")
    if cached is not None:
        return cached

    backend = settings.storage_backend.lower()
    storage: ArtifactStorage
    if backend == "s3":
        storage = S3ArtifactStorage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            prefix=settings.s3_prefix,
        )
    else:
        if backend != "local":
            logger.warning("storage_backend_unknown value=%s falling_back=local", backend)
        storage = LocalArtifactStorage(settings.artifact_root)
    _storage_instance["instance"] = storage
    return storage
