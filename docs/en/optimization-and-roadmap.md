# Optimization & roadmap

> **For AI agents:** this is the **forward-looking** doc. Anything here is **not yet implemented**. Do not document items below as if they exist. When working on one of these initiatives, move the relevant block into `feature-map.md` (with the file paths it landed in) and shrink the entry here.
>
> **For humans:** the prioritized list of post-Epic-4 work, scoped for the project's actual deployment shape: **a single user running the stack on one machine via Docker.** Items optimize feature value and UX over multi-tenant or platform-grade infrastructure.

## TL;DR

- The deployment target is **one person, one Docker host**. Multi-user, multi-tenant, and Kubernetes work is intentionally out of scope.
- Tier 1 is **new user-facing features** (bulk import, multi-voice dialogue, subtitle output).
- Tier 2 is **host adaptation** (GPU detect, concurrency tuning).
- Tier 3 is **quality of life** (provider plugins, simple retention, smoke E2E).
- The "Out of scope" section lists what was deliberately removed from earlier roadmaps and the reason.

## Scope: who this is for

`ntd_audio` is built for the developer running it on their own machine to produce TTS audio for personal projects (videos, podcasts, audio dramas, study material). That shapes every priority decision below:

- **Authentication** is "API key or nothing" — there's no second user.
- **Deployment** is `docker compose up`. Helm / Kubernetes / autoscaling don't apply.
- **Workers** run on the same machine as the API. Queue priorities, dead-letter queues, and per-tenant concurrency caps add complexity for no benefit.
- **Telemetry** doesn't apply — there's nothing for the project to learn from a single anonymous install.

## How this doc is organized

For each item:
1. **Why it matters** (concrete pain it removes for a single-user install).
2. **What changes** (files / components touched).
3. **Acceptance criteria** (the test that proves it shipped).
4. **Risk and migration notes** (what existing installs need to do).

---

## Tier 1 — User-facing features

### 1. Bulk import: TXT / CSV → batch project — **shipped**

Implemented in `routes_project_rows.py` + `services_bulk_import.py` + `BulkImportDialog.tsx`.

- `POST /v1/projects/{key}/rows/bulk` (multipart): TXT with line / blank-line split, CSV with configurable `text_column`, optional `voice_column`, `speaker_column`, `title_column`. `auto_enqueue=true` queues all imported rows immediately.
- `GET /v1/projects/{key}/rows/artifacts.zip?status=succeeded` streams a deflate-compressed zip named `{key}_{row_index:03d}_{slug}.{ext}`.
- Limits: `BULK_IMPORT_MAX_ROWS=5000`, `BULK_IMPORT_MAX_BYTES=5_242_880`. 413 / 422 returned for over-size or unparseable uploads.
- Frontend: "Import .txt / .csv" + "Download all .zip" actions in the script editor toolbar.

Cancel-the-whole-batch and per-row cancel rely on existing per-row queue/cancel infrastructure (Epic 3). Speaker label propagation to subtitles is tracked under #3.

### 2. Multi-voice / dialogue mode — **shipped (minimum viable)**

Per-row voice routing already worked via `provider_voice_id`. This iteration adds the missing piece: a `speaker_label` column on `project_script_rows` plus a small editable field below the title input in the script editor.

- Migration `20260424_0004` adds `speaker_label String(80) NULLABLE`. Existing rows keep `NULL`.
- Schema, `_serialize_row`, and `replace_project_rows` all propagate `speaker_label`.
- Frontend: `DraftRow` carries `speaker_label`; the title cell now hosts both the title input and a small speaker input below it (placeholder: "Speaker label (optional)" / "Tên speaker (tuỳ chọn)").

Concatenation into a single conversation mixdown is already implemented (`merge_project_rows` + ffmpeg), so dialogue mode reuses the existing `join_to_master` flag and the "Merge completed" panel.

A heavier "Speakers" panel that maps `speaker_label → provider_voice_id` and auto-fills the voice for newly added rows is intentionally deferred. For personal-use one-off scripts, manually setting voice + speaker per row is fine; revisit if it becomes ergonomically painful.

### 3. Subtitle output (.srt / .vtt)

**Why it matters.** For video creators (the natural audience for this kind of TTS workflow), the audio file alone is half the asset. They want a synchronized subtitle file per row or per conversation, with optional speaker labels for dialogue.

**What changes.**

- New artifact kind: `subtitle` (file extension `.srt`; `.vtt` available via query param on download).
- For engines that emit timing info (some cloud providers expose phoneme-level or sentence-level timestamps), use that timing directly.
- For engines that don't, estimate timing from `audio_duration_ms` and `char_count` (uniform char-per-second within the row, with sentence breaks aligned to punctuation).
- For "Conversation" output mode, the subtitle is one combined `.srt` covering the full mixdown, with each row as a cue and the speaker label (if any) prefixed (`[Anna] Hello there.`).
- Frontend: subtitle download appears next to audio download on the project page.

**Acceptance criteria.**

- After a successful job, downloading subtitle returns valid SRT (verified against the `srt` parsing library).
- Conversation mode produces one combined SRT; stems mode produces one SRT per row.
- For an engine that emits real timestamps (e.g. Google Cloud TTS markup mode), the SRT cue boundaries match what the audio actually says (within a small tolerance).
- For an engine without timing info, the SRT is at least monotonic and the total duration matches the audio file's duration.

**Risk and migration.** Pure addition. New artifact kind needs an enum migration but no destructive change.

### 4. Inline single-row preview — **shipped**

Implemented in `routes_providers.py::preview_arbitrary_text` + `previewRowSynthesis` API helper + per-row "Preview" button in the script editor.

- `POST /v1/providers/{provider_key}/preview` accepts `{text, voice_id, output_format?, params?}` and streams the synthesized audio back. No `synthesis_jobs` row, no artifact write, no DB persistence.
- Length cap via `PREVIEW_MAX_CHARS` (default 500). Returns 413 over the cap.
- Rate-limit reuses the existing token bucket (`RATE_LIMIT_PER_MINUTE`).
- Frontend: each row in `ScriptEditor` shows a "Preview" button next to the artifact cell. Result is rendered with `<audio controls src=blob:...>` and the blob URL is revoked when the page unmounts.

### 5. Project export bundle

**Why it matters.** A finished project (script + voice mappings + audio + subtitles) is portable content the user wants to back up, share, or move between machines. Today, exporting requires manually downloading each artifact and remembering which voice was used.

**What changes.**

- New endpoint `GET /v1/projects/{key}/export` that returns a zip containing:
  - `script.json` — full row dump, including `text`, `voice`, `speaker`, ordering.
  - `voice-map.json` — speaker-to-voice-key mapping (resolved against the catalog at export time).
  - `original.txt` / `original.csv` — the file that was imported (if any), preserved verbatim.
  - `audio/` — every successful artifact, named per the convention from #1.
  - `subtitles/` — matching `.srt` files (when #3 ships).
  - `metadata.json` — project ID, title, created/updated timestamps, schema version.
- Reverse: `POST /v1/projects/import` accepts the same zip and recreates the project (idempotent on `project_key`; existing artifacts are reused).

**Acceptance criteria.**

- Export of a 50-row project produces a single zip containing all rows, all audio, and the voice map.
- Importing the zip on a fresh install recreates the project with the same rows in the same order.
- Round-trip (export → import → export) produces byte-identical script.json and voice-map.json.

**Risk and migration.** Pure addition. The export schema is part of the public contract; bumps require a CHANGELOG entry.

---

## Tier 2 — Host adaptation

### 6. GPU / CPU auto-detect — **shipped**

Implemented in `services_system.py` and exposed at `GET /v1/system/capabilities`.

- Probe runs `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits` once per process (cached for the container's lifetime — capabilities don't change without a restart).
- CPU info uses `os.sched_getaffinity(0)` when available (cgroup-aware on Docker), otherwise `os.cpu_count()`.
- Response shape: `{ gpu: { vendor, name, vram_mb } | null, cpu: { cores, threads }, recommended_overlays: ["docker-compose.gpu.yml"] }`. GPU is `null` on CPU-only hosts and `recommended_overlays` is empty.
- Frontend: Settings page gains a "Host" panel rendering the detected hardware plus the exact `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` command to switch overlay when a GPU is present.

Per-engine "which device did I actually load on" reporting (CPU vs CUDA) from inside the engine container is still an open extension; today the panel reports what the API container can see, which is enough to validate that the GPU is correctly mounted into the compose project.

### 7. Concurrency tuning per provider — **shipped**

Implemented in `services_provider_concurrency.py`, wrapping the synthesize call in `services_jobs.process_job`.

- Process-local `BoundedSemaphore` per provider key; created lazily on first job.
- Defaults: `cloud` providers → 4 concurrent calls (network-bound), `self_hosted` → 1 (single CPU/GPU backend).
- Per-category overrides via `PROVIDER_CONCURRENCY_CLOUD` / `PROVIDER_CONCURRENCY_SELF_HOSTED`.
- Per-provider override via `PROVIDER_CONCURRENCY` (JSON dict, e.g. `{"openai": 6, "voicevox": 2}`).
- The active limit is exposed in `GET /v1/providers` as `concurrency_limit` so the UI can display it.

If you scale by running multiple worker processes (e.g. `dramatiq voiceforge.tasks --processes 2`), the effective ceiling is `worker_count * provider_limit`. For personal-use single-host installs this is the right tradeoff (no Redis-side coordination needed).

A future iteration may add a Settings → "Performance" panel that persists overrides in `app_settings` so changes don't require an env reload. Not implemented yet — env-driven configuration covers the personal-use case.

### 8. Wire `ArtifactStorage` into `write_artifact` — **shipped (write path)**

`storage.py::write_artifact` now delegates to `services.storage.get_storage().write_bytes(...)`. Operators who set `STORAGE_BACKEND=s3` (or re-target `ARTIFACT_ROOT` to a NAS / external HDD) finally get the bytes routed through the abstraction. The function's contract `(relative_key, size, sha256_hex)` is unchanged.

Reads (`artifact_absolute_path` + `FileResponse`) are still local-fs only. Adding S3 read / redirect support — either streaming bytes back through FastAPI or returning a presigned URL — is the natural follow-up but is intentionally out of scope here so this PR is small and reviewable.

Migrating an existing local artifact tree to S3 still needs an out-of-band `aws s3 sync` (no automatic copy on boot).

---

## Tier 3 — Quality of life

### 9. Provider plugin entry points

**Why it matters.** Adding a TTS engine today requires editing the provider registry. For a personal install, the user occasionally wants to plug in their own model (a fine-tune, a research checkpoint, a niche language model) without forking the project.

**What changes.**

- Define a stable provider Protocol (already partially formalized) and turn it into a tagged ABC.
- Discover providers via `[project.entry-points."voiceforge.providers"]`. The built-in ones move to entries; the registry loads them at startup.
- A small example plugin in `examples/voiceforge-provider-stub` shows the contract.
- `docs/en/providers.md` gains a "Build your own" section.

**Acceptance criteria.**

- All existing providers continue to work, registered via entry points.
- The example plugin is installable with `pip install -e ./examples/...` and shows up in the catalog.

**Risk and migration.** Internal — no operator-facing breaking change.

### 10. Simple retention controls — **shipped**

Settings page gains a "Retention" panel with a configurable "older than (days)" window (default 30). New endpoints:

- `GET /v1/admin/retention/preview?older_than_days=N` returns `{ cutoff_iso, job_count, artifact_count, bytes_on_disk }`.
- `POST /v1/admin/retention/purge` body `{ older_than_days: N, confirm: true }` deletes terminal jobs (`succeeded`/`failed`/`canceled`) older than the cutoff plus their artifacts (DB rows + files on disk). The API rejects calls without `confirm: true`.

The UI flow is preview → confirm → delete: the "Delete now" button stays disabled until a non-empty preview is loaded. Active and recent jobs are never touched. The `voiceforge_artifacts_pruned_total` counter and per-status filtering are deliberate follow-ups.

### 11. Playwright smoke E2E

**Why it matters.** Vitest covers components in isolation; pytest covers handlers. Neither catches "I imported a CSV, queued the batch, waited via SSE, and the zip download didn't have all the files." One tight smoke scenario catches a wide class of regressions.

**What changes.**

- One scenario: **bulk import → run → wait → download zip**. CSV with 5 rows, two voices, "Conversation" output mode, expect 5 stems + 1 mixdown + 1 SRT in the zip.
- Run against a stub-provider Compose profile so it doesn't depend on cloud APIs.
- New CI job `frontend-e2e` on PRs touching `frontend/`, `backend/`, or `engines/`.

**Acceptance criteria.**

- `make e2e` builds the stack, runs the scenario, tears down. Runs locally and in CI.
- Failing E2E blocks PR merges on the relevant paths.

**Risk and migration.** New CI minutes — limit to relevant paths.

---

## Out of scope (deliberately removed)

These items were proposed in earlier roadmaps and are intentionally **not** going to be pursued, given the personal-use scope:

| Removed | Why |
|---|---|
| **JWT / multi-user auth** | One user. The existing `X-API-Key` gate is enough; no need for accounts, sessions, or per-user audit. |
| **Workspace boundaries / per-user audit** | Same — multi-tenant concerns don't apply. |
| **Helm chart for Kubernetes** | One Docker host. Compose is the deployment story. |
| **Worker scaling primitives (DLQ, priority queues, per-project concurrency caps)** | A single host with one worker doesn't benefit from this. Tier 2 #7 (concurrency tuning) covers the actual personal-use need. |
| **Anonymous opt-in telemetry** | A single anonymous install yields no signal worth collecting. The complexity isn't justified. |
| **Per-project retention policies (full table + nightly cron)** | Tier 3 #10 (a single "delete older than X days" button) covers the actual need with one-tenth the complexity. |

If the project's scope ever changes (multi-user, hosted offering, fleet deployment), revisit this section.

---

## How to propose a new initiative

1. Open a GitHub issue describing the symptom, not the solution.
2. If you're proposing a solution, fork this doc's structure (Why / What changes / Acceptance / Risk).
3. Link related issues.
4. PRs that pick up an item should move the entry from this doc into `feature-map.md` once it lands, with file paths.
