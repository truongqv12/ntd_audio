"""Project export bundle (T1.5).

Builds an in-memory zip containing the project's persistable state plus the
audio artifacts that have been synthesized so far. The shape is stable enough
to re-import on another install (re-import endpoint is a follow-up).

Layout::

    metadata.json     - { project_key, name, schema_version, generated_at }
    script.json       - full row state, ordered by row_index
    voice-map.json    - { row_index: { provider_key, provider_voice_id } }
    audio/<idx>_<safe_title>.<ext>
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Project, ProjectScriptRow
from .storage import artifact_absolute_path

SCHEMA_VERSION = 1


def _safe_filename(title: str | None, fallback: str) -> str:
    if not title:
        return fallback
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", title.strip())
    cleaned = cleaned.strip("._-") or fallback
    return cleaned[:64]


def _row_to_dict(row: ProjectScriptRow) -> dict:
    return {
        "row_index": row.row_index,
        "title": row.title,
        "source_text": row.source_text,
        "provider_key": row.provider_key,
        "provider_voice_id": row.provider_voice_id,
        "output_format": row.output_format,
        "params": row.params or {},
        "is_enabled": row.is_enabled,
        "join_to_master": row.join_to_master,
        "last_artifact_relative_path": row.last_artifact_relative_path,
    }


def _project_to_dict(project: Project) -> dict:
    return {
        "project_key": project.project_key,
        "name": project.name,
        "default_provider_key": project.default_provider_key,
        "default_output_format": project.default_output_format,
        "settings": project.settings or {},
    }


def build_export_zip(db: Session, project: Project) -> bytes:
    rows: list[ProjectScriptRow] = list(
        db.scalars(
            select(ProjectScriptRow)
            .where(ProjectScriptRow.project_id == project.id)
            .order_by(ProjectScriptRow.row_index.asc())
        ).all()
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "metadata.json",
            json.dumps(
                {
                    "project_key": project.project_key,
                    "name": project.name,
                    "schema_version": SCHEMA_VERSION,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "row_count": len(rows),
                },
                indent=2,
                ensure_ascii=False,
            ),
        )
        zf.writestr(
            "script.json",
            json.dumps(
                {"project": _project_to_dict(project), "rows": [_row_to_dict(r) for r in rows]},
                indent=2,
                ensure_ascii=False,
            ),
        )
        zf.writestr(
            "voice-map.json",
            json.dumps(
                {
                    str(row.row_index): {
                        "provider_key": row.provider_key,
                        "provider_voice_id": row.provider_voice_id,
                    }
                    for row in rows
                    if row.provider_voice_id
                },
                indent=2,
                ensure_ascii=False,
            ),
        )
        _write_audio_files(zf, rows)
    return buf.getvalue()


def _write_audio_files(zf: zipfile.ZipFile, rows: Iterable[ProjectScriptRow]) -> None:
    for row in rows:
        rel = row.last_artifact_relative_path
        if not rel:
            continue
        abs_path: Path = artifact_absolute_path(rel)
        if not abs_path.exists():
            continue
        suffix = abs_path.suffix or ".wav"
        safe = _safe_filename(row.title, fallback=f"row{row.row_index:03d}")
        arcname = f"audio/{row.row_index:03d}_{safe}{suffix}"
        zf.write(abs_path, arcname=arcname)
