"""Bulk import: parsers + service-level append (T1.1)."""

from __future__ import annotations

import pytest

from voiceforge.models import Project, ProjectScriptRow
from voiceforge.services_bulk_import import parse_csv, parse_txt
from voiceforge.services_project_rows import (
    bulk_import_rows,
    bulk_import_to_response,
    stream_artifacts_zip,
)


def test_parse_txt_one_per_line_strips_blanks():
    raw = "Hello world\n\nSecond line\nThird"
    rows = parse_txt(raw)
    assert [r.text for r in rows] == ["Hello world", "Second line", "Third"]


def test_parse_txt_handles_bom_and_crlf():
    raw = ("\ufefffirst\r\nsecond\r\n\r\nthird").encode()
    rows = parse_txt(raw)
    assert [r.text for r in rows] == ["first", "second", "third"]


def test_parse_txt_blank_line_split_treats_paragraph_as_row():
    raw = "Một câu dài\nvẫn cùng một đoạn.\n\nĐoạn hai."
    rows = parse_txt(raw, split="blank-line")
    assert len(rows) == 2
    assert "Một câu dài" in rows[0].text
    assert rows[1].text == "Đoạn hai."


def test_parse_csv_with_voice_and_speaker_columns():
    raw = "text,voice,speaker\nHello,kokoro:af_heart,Anna\nHi there,openai:onyx,Host\n"
    rows = parse_csv(raw)
    assert [r.text for r in rows] == ["Hello", "Hi there"]
    assert rows[0].provider_voice_id == "kokoro:af_heart"
    assert rows[0].speaker_label == "Anna"
    assert rows[1].speaker_label == "Host"


def test_parse_csv_skips_empty_text_rows():
    raw = "text,voice\nfoo,v1\n,v2\nbar,\n"
    rows = parse_csv(raw)
    assert [r.text for r in rows] == ["foo", "bar"]


def test_parse_csv_missing_text_column_raises():
    with pytest.raises(ValueError):
        parse_csv("name,voice\nfoo,bar\n")


def test_bulk_import_rows_appends_with_increasing_index(db_session):
    project = Project(project_key="pbulk", name="pbulk")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ProjectScriptRow(
            project_id=project.id,
            row_index=2,
            source_text="existing",
            params={},
            status="draft",
        )
    )
    db_session.commit()

    parsed = parse_txt("a\nb\nc")
    project_after, inserted = bulk_import_rows(db_session, "pbulk", parsed)
    assert project_after.project_key == "pbulk"
    assert [r.row_index for r in inserted] == [3, 4, 5]
    assert [r.source_text for r in inserted] == ["a", "b", "c"]


def test_bulk_import_to_response_serializes(db_session):
    parsed = parse_txt("hello\nworld")
    project, rows = bulk_import_rows(
        db_session,
        "presp",
        parsed,
        default_provider_key="voicevox",
        default_voice_id="0",
    )
    response = bulk_import_to_response(project, rows)
    assert response.project_key == "presp"
    assert response.inserted == 2
    assert response.rows[0].source_text == "hello"
    assert response.rows[0].provider_voice_id == "0"


def test_stream_artifacts_zip_returns_none_for_unknown_project(db_session):
    assert stream_artifacts_zip(db_session, "does-not-exist") is None
