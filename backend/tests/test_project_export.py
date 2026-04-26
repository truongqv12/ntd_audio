"""Project export bundle (T1.5)."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from voiceforge.config import settings
from voiceforge.models import Project, ProjectScriptRow
from voiceforge.services_project_export import SCHEMA_VERSION, build_export_zip


def _project(db, key: str = "p1") -> Project:
    project = Project(project_key=key, name=key)
    db.add(project)
    db.flush()
    return project


def _row(
    db,
    *,
    project: Project,
    index: int,
    text: str,
    relpath: str | None = None,
    title: str | None = None,
) -> ProjectScriptRow:
    row = ProjectScriptRow(
        project_id=project.id,
        row_index=index,
        title=title,
        source_text=text,
        provider_key="fake",
        provider_voice_id="fake:1",
        is_enabled=True,
        join_to_master=True,
        last_artifact_relative_path=relpath,
    )
    db.add(row)
    db.flush()
    return row


def _write_artifact(relpath: str, payload: bytes) -> Path:
    path = settings.artifact_root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_export_zip_contains_metadata_script_and_voice_map(db_session):
    project = _project(db_session)
    _row(db_session, project=project, index=0, text="hi", title="intro")
    body = build_export_zip(db_session, project)

    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        names = set(zf.namelist())
        assert "metadata.json" in names
        assert "script.json" in names
        assert "voice-map.json" in names

        metadata = json.loads(zf.read("metadata.json"))
        assert metadata["project_key"] == project.project_key
        assert metadata["schema_version"] == SCHEMA_VERSION
        assert metadata["row_count"] == 1

        script = json.loads(zf.read("script.json"))
        assert script["project"]["project_key"] == project.project_key
        assert script["rows"][0]["title"] == "intro"

        voice_map = json.loads(zf.read("voice-map.json"))
        assert voice_map == {"0": {"provider_key": "fake", "provider_voice_id": "fake:1"}}


def test_export_zip_includes_audio_when_artifact_exists(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifact_root", tmp_path)
    project = _project(db_session)
    relpath = "fake/abc.wav"
    _write_artifact(str(tmp_path / relpath), b"RIFF....")
    _row(db_session, project=project, index=0, text="hi", title="My Title!", relpath=relpath)
    # Force the storage helper to read from tmp_path
    monkeypatch.setattr(settings, "artifact_root", tmp_path)

    body = build_export_zip(db_session, project)
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        names = zf.namelist()
        audio_files = [n for n in names if n.startswith("audio/")]
        assert len(audio_files) == 1
        assert audio_files[0].startswith("audio/000_My_Title")
        assert audio_files[0].endswith(".wav")


def test_export_zip_skips_missing_artifact(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifact_root", tmp_path)
    project = _project(db_session)
    _row(db_session, project=project, index=0, text="hi", relpath="fake/missing.wav")

    body = build_export_zip(db_session, project)
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        names = zf.namelist()
        assert not [n for n in names if n.startswith("audio/")]


def test_export_zip_skips_voice_map_for_rows_without_voice(db_session):
    project = _project(db_session)
    row = ProjectScriptRow(
        project_id=project.id,
        row_index=0,
        source_text="no voice yet",
        is_enabled=True,
        join_to_master=True,
    )
    db_session.add(row)
    db_session.flush()
    body = build_export_zip(db_session, project)
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        voice_map = json.loads(zf.read("voice-map.json"))
        assert voice_map == {}
