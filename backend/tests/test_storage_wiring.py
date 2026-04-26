"""T2.8 — write_artifact must flow through ArtifactStorage.

Verifies the seam: substituting the storage backend with a fake captures the
bytes, and the legacy contract `(relative_key, size, sha256)` is preserved.
"""

from __future__ import annotations

import hashlib
from typing import IO

import pytest

from voiceforge import storage as storage_module
from voiceforge.services import storage as backend_module


class _FakeStorage:
    def __init__(self) -> None:
        self.writes: dict[str, bytes] = {}

    def write_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        self.writes[key] = data
        return f"/artifacts/{key}"

    def write_stream(self, key: str, stream: IO[bytes], *, content_type: str | None = None) -> str:
        return self.write_bytes(key, stream.read(), content_type=content_type)

    def read_bytes(self, key: str) -> bytes:
        return self.writes[key]

    def exists(self, key: str) -> bool:
        return key in self.writes

    def delete(self, key: str) -> None:
        self.writes.pop(key, None)


@pytest.fixture()
def fake_storage(monkeypatch: pytest.MonkeyPatch) -> _FakeStorage:
    fake = _FakeStorage()
    monkeypatch.setattr(backend_module, "get_storage", lambda: fake)
    monkeypatch.setattr(storage_module, "get_storage", lambda: fake)
    return fake


def test_write_artifact_routes_through_storage_backend(fake_storage: _FakeStorage) -> None:
    payload = b"\x00\x01synthesized-bytes"
    relative, size, sha = storage_module.write_artifact(
        provider_key="voicevox",
        suffix=".wav",
        content=payload,
    )
    assert relative.startswith("voicevox/")
    assert relative.endswith(".wav")
    assert size == len(payload)
    assert sha == hashlib.sha256(payload).hexdigest()
    assert fake_storage.writes[relative] == payload


def test_write_artifact_strips_leading_dot_in_suffix(fake_storage: _FakeStorage) -> None:
    relative, _, _ = storage_module.write_artifact(
        provider_key="openai",
        suffix="mp3",
        content=b"x",
    )
    assert relative.endswith(".mp3")
    assert ".." not in relative
