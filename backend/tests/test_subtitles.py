"""Subtitle generation (T1.3) — uses row.duration_seconds when present,
falls back to char/sec estimate, and prefixes [Speaker] when set."""

from voiceforge.models import Project, ProjectScriptRow
from voiceforge.services_subtitles import (
    _format_srt_timestamp,
    _format_vtt_timestamp,
    build_cues,
    render,
    render_srt,
    render_vtt,
)


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
    duration: float | None = None,
    speaker: str | None = None,
) -> ProjectScriptRow:
    row = ProjectScriptRow(
        project_id=project.id,
        row_index=index,
        source_text=text,
        speaker_label=speaker,
        provider_key="fake",
        provider_voice_id="fake:1",
        is_enabled=True,
        join_to_master=True,
        duration_seconds=duration,
        last_artifact_relative_path=f"a/{index}.wav" if duration else None,
    )
    db.add(row)
    db.flush()
    return row


def test_format_srt_timestamp_handles_subseconds():
    assert _format_srt_timestamp(0) == "00:00:00,000"
    assert _format_srt_timestamp(1.5) == "00:00:01,500"
    assert _format_srt_timestamp(3661.25) == "01:01:01,250"


def test_format_srt_timestamp_carries_to_minute_and_hour_boundaries():
    # ms-rounding at the second boundary must propagate up through min/hour
    assert _format_srt_timestamp(59.9999) == "00:01:00,000"
    assert _format_srt_timestamp(3599.9999) == "01:00:00,000"


def test_format_vtt_uses_dot_separator():
    assert _format_vtt_timestamp(1.5) == "00:00:01.500"


def test_build_cues_uses_duration_and_silence_gap(db_session):
    project = _project(db_session)
    rows = [
        _row(db_session, project=project, index=0, text="Hello.", duration=1.0),
        _row(db_session, project=project, index=1, text="World.", duration=2.0),
    ]
    cues = build_cues(rows, silence_ms=500)
    assert cues[0].start_seconds == 0.0
    assert cues[0].end_seconds == 1.0
    assert cues[1].start_seconds == 1.5  # 1.0 + 0.5 gap
    assert cues[1].end_seconds == 3.5


def test_build_cues_estimates_when_duration_missing(db_session):
    project = _project(db_session)
    rows = [_row(db_session, project=project, index=0, text="x" * 30, duration=None)]
    cues = build_cues(rows, silence_ms=0)
    # 30 chars / 15 cps = 2.0 seconds
    assert abs(cues[0].end_seconds - 2.0) < 0.01


def test_build_cues_treats_zero_duration_literally_not_as_missing(db_session):
    # A recorded duration of exactly 0.0 must NOT be replaced by the char/sec
    # estimate — the row contributes a zero-length cue.
    project = _project(db_session)
    rows = [_row(db_session, project=project, index=0, text="x" * 30, duration=0.0)]
    cues = build_cues(rows, silence_ms=0)
    assert cues[0].start_seconds == 0.0
    assert cues[0].end_seconds == 0.0


def test_speaker_label_prefixes_cue(db_session):
    project = _project(db_session)
    rows = [_row(db_session, project=project, index=0, text="Hello.", duration=1.0, speaker="Anna")]
    cues = build_cues(rows)
    assert cues[0].text == "[Anna] Hello."


def test_render_srt_produces_well_formed_blocks(db_session):
    project = _project(db_session)
    rows = [_row(db_session, project=project, index=0, text="Hi.", duration=1.0)]
    body = render_srt(build_cues(rows))
    assert "1\n00:00:00,000 --> 00:00:01,000\nHi.\n" in body


def test_render_vtt_starts_with_webvtt(db_session):
    project = _project(db_session)
    rows = [_row(db_session, project=project, index=0, text="Hi.", duration=1.0)]
    body = render_vtt(build_cues(rows))
    assert body.startswith("WEBVTT\n")


def test_render_dispatch_returns_correct_mime(db_session):
    project = _project(db_session)
    rows = [_row(db_session, project=project, index=0, text="Hi.", duration=1.0)]
    _, mime_srt = render(rows, "srt")
    _, mime_vtt = render(rows, "vtt")
    assert mime_srt == "application/x-subrip"
    assert mime_vtt == "text/vtt"
