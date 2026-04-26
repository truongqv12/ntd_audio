"""Subtitle generation for project rows (T1.3).

Builds a single `.srt` or `.vtt` file by walking a project's enabled rows in
order, using each row's `duration_seconds` (set by the worker after a job
finishes) as the cue length. Rows without a recorded duration fall back to a
char/sec estimate (default 15 chars/sec, configurable via
``SUBTITLE_CHARS_PER_SECOND``).

A row's speaker label, if present, is prefixed in square brackets:
``[Anna] Hello there.``

The generator does not consult the audio file directly — it trusts the
duration on the row. That's accurate for engines that report a duration and a
reasonable estimate otherwise. Sub-row word-level timing is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import settings
from .models import ProjectScriptRow


@dataclass(slots=True)
class SubtitleCue:
    index: int
    start_seconds: float
    end_seconds: float
    text: str


def _estimate_duration_seconds(text: str) -> float:
    chars = max(1, len(text.strip()))
    rate = max(1.0, settings.subtitle_chars_per_second)
    return max(0.8, chars / rate)


def _format_srt_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis == 1000:
        millis = 0
        secs += 1
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    return _format_srt_timestamp(seconds).replace(",", ".")


def build_cues(rows: list[ProjectScriptRow], silence_ms: int = 150) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    cursor = 0.0
    gap = max(0, silence_ms) / 1000.0
    for idx, row in enumerate(rows, start=1):
        duration = row.duration_seconds or _estimate_duration_seconds(row.source_text)
        start = cursor
        end = cursor + duration
        text = row.source_text.strip()
        if row.speaker_label:
            text = f"[{row.speaker_label.strip()}] {text}"
        cues.append(SubtitleCue(index=idx, start_seconds=start, end_seconds=end, text=text))
        cursor = end + gap
    return cues


def render_srt(cues: list[SubtitleCue]) -> str:
    blocks: list[str] = []
    for cue in cues:
        blocks.append(
            f"{cue.index}\n"
            f"{_format_srt_timestamp(cue.start_seconds)} --> "
            f"{_format_srt_timestamp(cue.end_seconds)}\n"
            f"{cue.text}\n"
        )
    return "\n".join(blocks)


def render_vtt(cues: list[SubtitleCue]) -> str:
    blocks: list[str] = ["WEBVTT", ""]
    for cue in cues:
        blocks.append(
            f"{_format_vtt_timestamp(cue.start_seconds)} --> "
            f"{_format_vtt_timestamp(cue.end_seconds)}\n"
            f"{cue.text}\n"
        )
    return "\n".join(blocks)


def render(rows: list[ProjectScriptRow], file_format: str = "srt", silence_ms: int = 150) -> tuple[str, str]:
    cues = build_cues(rows, silence_ms=silence_ms)
    fmt = file_format.lower()
    if fmt == "vtt":
        return render_vtt(cues), "text/vtt"
    return render_srt(cues), "application/x-subrip"
