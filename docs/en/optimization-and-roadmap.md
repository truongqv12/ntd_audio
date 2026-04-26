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

### 2. Multi-voice / dialogue mode

**Why it matters.** Today, all rows in a project use one voice (or per-row voice, but with no concept of "speaker"). For a podcast, audio drama, or dialogue scene, the user wants two or more characters speaking, with named speaker tags carrying through to subtitles and exports.

**What changes.**

- Schema: `project_script_rows.speaker_label` (nullable text — "Anna", "Host", etc.) and `projects.settings.speakers` (a JSON map of `speaker_label → voice_key`).
- `ScriptEditor` UI: a "Speakers" panel where the user defines `Anna → kokoro:af_heart`, `Host → openai:onyx`. Then in the row editor, picking a speaker auto-fills the voice for that row.
- Two output modes per project (`projects.settings.output_mode`):
  - **Stems** (default, current behavior): one audio file per row.
  - **Conversation**: at the end of a successful batch, the worker concatenates all rows in order with configurable inter-row silence (e.g. 300 ms) into a single mixdown file. The mixdown becomes its own artifact (kind `conversation_mixdown`).
- Subtitle output (next item) carries the speaker label.

**Acceptance criteria.**

- A user can define 2+ speakers, assign rows to speakers, and run the batch.
- "Stems" mode produces one file per row, named with the speaker label (e.g. `001_anna_hello.wav`).
- "Conversation" mode produces a single file with rows concatenated in order, plus the per-row stems.
- Silence-between-rows is configurable per project (`projects.settings.conversation_gap_ms`).

**Risk and migration.** Adds two new schema columns + one settings key. Existing projects: `speaker_label` is null (treated as no-speaker), `output_mode` defaults to `stems` (current behavior).

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

### 6. GPU / CPU auto-detect

**Why it matters.** OSS engines (especially Kokoro and VieNeu) can run dramatically faster on a GPU. Today, the user has to manually pick the right Compose overlay and trust that the engine container picks up the GPU. There's no UI surface that tells you whether GPU acceleration is actually active.

**What changes.**

- At API startup, probe the host:
  - Is `nvidia-smi` available and returning a device?
  - Is `/dev/dri` populated (Intel/AMD)?
  - What does `os.cpu_count()` report?
- Expose at `GET /v1/system/capabilities` (gated by API key when present): `{ gpu: { vendor, name, vram_mb } | null, cpu: { cores, threads }, recommended_overlays: [...] }`.
- Per-engine container, a small `/healthz` extension that reports back which device the engine actually loaded on (CPU vs CUDA).
- Frontend: Settings → "Host" tab shows the detected hardware and which engines are using it. If a GPU is present but a CPU-only overlay is active, surface a one-click "switch to GPU overlay" hint with the exact `docker compose` command to run.

**Acceptance criteria.**

- On a host with an NVIDIA GPU, `/v1/system/capabilities` reports it correctly.
- On a CPU-only host, the GPU field is `null` and the recommended overlays don't include GPU variants.
- Settings → Host tab matches what the engine containers actually report.

**Risk and migration.** Pure addition. No breaking change.

### 7. Concurrency tuning per provider

**Why it matters.** Cloud TTS endpoints are network-bound and happily run 4–8 in parallel. OSS engines on a single CPU saturate around 1–2 concurrent jobs. Today, there's a single global worker prefetch — too high for OSS, too low for cloud. The user gets either a slow batch or a thrashing host.

**What changes.**

- New per-provider `concurrency_hint` in the provider registry (e.g. `openai_tts: 8`, `voicevox: 2`, `kokoro: 1`).
- Worker dispatch reads the hint and uses an in-process semaphore per `provider_key` so a batch of 50 OpenAI rows runs 8-wide while a batch of 50 Kokoro rows runs 1-wide.
- Settings → "Performance" panel: a slider per provider (default = the registry hint, cap = 16). The chosen values persist in `app_settings`.
- Default global cap is `min(os.cpu_count(), 4)` for OSS engines and `8` for cloud engines.

**Acceptance criteria.**

- Running a 20-row batch against `openai_tts` completes substantially faster than the same batch ran serially (within network/provider rate-limit bounds).
- Running a 20-row batch against `voicevox` doesn't peg a 4-core host's load above 4.
- The Settings UI honors the override; setting cloud = 1 forces serial execution.

**Risk and migration.** New `app_settings` key; existing installs default to the registry hint.

### 8. Wire `ArtifactStorage` into `write_artifact`

**Why it matters.** Even on a personal install, the user often wants artifacts written to a NAS, an external drive, or an S3-compatible bucket on a home server (MinIO). Today, `STORAGE_BACKEND=s3` is a no-op for new artifacts because the legacy write path bypasses the `ArtifactStorage` Protocol. Following `self-hosting.md` and setting the env vars yields a silently broken setup.

**What changes.**

- Replace direct `Path.write_bytes` / `cache_root` calls in `services_jobs.process_job` with `storage = get_storage(); storage.write_bytes(key, audio_bytes)`.
- Same for the `generation_cache` write path.
- Migrate the read path to read through the abstraction.
- Add a smoke test that boots MinIO in CI and round-trips an artifact.
- Document in `self-hosting.md` that local → S3 migration of existing artifacts requires `aws s3 sync` (no automatic copy on boot).

**Acceptance criteria.**

- `STORAGE_BACKEND=s3` plus `S3_*` env vars makes new jobs write into the bucket; downloads stream from the bucket; nothing touches `ARTIFACT_ROOT`.
- `STORAGE_BACKEND=local` continues to work bit-for-bit identically.
- New integration test passes against MinIO in CI.

**Risk and migration.** Existing `local` installs unaffected (default unchanged).

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

### 10. Simple retention controls

**Why it matters.** Artifacts and `generation_cache` rows accumulate forever. A casual user with months of experimentation eventually fills disk. The previous roadmap proposed a full per-project retention policy table — overkill for personal use.

**What changes.**

- Settings → "Storage" panel: shows current artifact disk usage, with a single button **"Delete jobs older than X days"** (slider, default 30 d, optional filter by status: `failed` / `canceled` / `succeeded` / all).
- Backend endpoint `POST /v1/admin/retention/run-now { older_than_days, statuses }` — synchronous for small batches, queued for large ones.
- Counts metric `voiceforge_artifacts_pruned_total{reason}` so the user can see how much was reclaimed.

**Acceptance criteria.**

- A user can click "Delete jobs older than 30 days, failed only" and see disk usage drop accordingly.
- The action removes both DB rows and storage objects (works for `local` and `s3`).
- A confirmation step prevents accidental whole-history wipes.

**Risk and migration.** Destructive; the action is opt-in only and shows a confirmation.

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
