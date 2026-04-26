"""Pure parsers for bulk-imported script rows (TXT or CSV).

Producers in this module never touch the DB. They take raw bytes / text and
return a list of ``ParsedRow`` records that the caller turns into
``ProjectScriptRow`` rows in a single transaction.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class ParsedRow:
    text: str
    provider_voice_id: str | None = None
    speaker_label: str | None = None
    title: str | None = None


TxtSplitMode = Literal["line", "blank-line"]


def _strip_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def parse_txt(raw: bytes | str, *, split: TxtSplitMode = "line") -> list[ParsedRow]:
    """Split a TXT blob into rows.

    - ``split="line"`` (default): one non-empty line == one row.
    - ``split="blank-line"``: split on blank lines (paragraph mode).
    """
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    text = _strip_bom(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if split == "line":
        chunks = [line.strip() for line in text.split("\n")]
    elif split == "blank-line":
        chunks = [block.strip() for block in text.split("\n\n")]
    else:  # pragma: no cover - guarded by Literal
        raise ValueError(f"Unsupported split mode: {split}")

    return [ParsedRow(text=chunk) for chunk in chunks if chunk]


def parse_csv(
    raw: bytes | str,
    *,
    text_column: str = "text",
    voice_column: str | None = "voice",
    speaker_column: str | None = "speaker",
    title_column: str | None = "title",
) -> list[ParsedRow]:
    """Parse a CSV blob with a configurable text column and optional voice / speaker columns.

    The CSV must have a header row. Rows where the text column is empty are skipped.
    Unknown columns are ignored. Trailing whitespace and a UTF-8 BOM on the first column
    name are tolerated.
    """
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    text = _strip_bom(text)

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []

    # csv.DictReader doesn't strip the BOM from the first column name on its own.
    fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
    reader.fieldnames = fieldnames

    if text_column not in fieldnames:
        raise ValueError(f"CSV is missing required column: {text_column!r}")

    rows: list[ParsedRow] = []
    for record in reader:
        body = (record.get(text_column) or "").strip()
        if not body:
            continue
        voice = (record.get(voice_column) or "").strip() if voice_column else ""
        speaker = (record.get(speaker_column) or "").strip() if speaker_column else ""
        title = (record.get(title_column) or "").strip() if title_column else ""
        rows.append(
            ParsedRow(
                text=body,
                provider_voice_id=voice or None,
                speaker_label=speaker or None,
                title=title or None,
            )
        )
    return rows
