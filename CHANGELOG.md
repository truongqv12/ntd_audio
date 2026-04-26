# Changelog

All notable changes to VoiceForge Studio are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Bulk import script rows from TXT/CSV (T1.1).** `POST /v1/projects/{key}/rows/bulk` accepts a multipart upload (`format=txt|csv`). TXT supports line-per-row or blank-line paragraph splitting; CSV supports configurable text/voice/speaker/title columns. Rows are appended (existing `row_index` is preserved). Optional `auto_enqueue=true` queues all imported rows immediately. Limits enforced via `BULK_IMPORT_MAX_ROWS` (default 5000) and `BULK_IMPORT_MAX_BYTES` (default 5 MiB). The `BulkImportDialog` modal in the script editor wraps it (file picker, format toggle, CSV column overrides, default provider/voice fields, auto-enqueue toggle).
- **Project artifacts zip download (T1.1).** `GET /v1/projects/{key}/rows/artifacts.zip?status=succeeded` streams a deflate-compressed zip of every completed row's artifact, named `{key}_{idx:03d}_{slug}.{ext}`. Surface in the script editor as "Download all .zip" (disabled when no completed rows).
- **On-demand single-row preview (T1.4).** `POST /v1/providers/{provider_key}/preview` accepts `{text, voice_id, output_format?, params?}` and streams the synthesized audio back without writing anything to the database or artifact root. Cap enforced via `PREVIEW_MAX_CHARS` (default 500). The script editor renders a per-row "Preview" button that plays the result inline (the blob URL is revoked when the page unmounts).
- **Per-provider concurrency limit (T2.7).** New `services_provider_concurrency` module wraps every `provider.synthesize` call in a process-local `BoundedSemaphore` keyed by provider key. Defaults: 4 concurrent calls for `cloud` providers (network-bound), 1 for `self_hosted` (CPU/GPU-bound, single backend). Override per-category via `PROVIDER_CONCURRENCY_CLOUD` / `PROVIDER_CONCURRENCY_SELF_HOSTED`, or per-provider via `PROVIDER_CONCURRENCY` (JSON dict, e.g. `{"openai": 6, "voicevox": 2}`). The active limit per provider is now surfaced in `GET /v1/providers` as `concurrency_limit` so the UI can display it.
- **Production readiness (Epic 4).**
  - **API versioning.** All routes are mounted under `/v1/*` (canonical) and the legacy un-versioned paths (`/jobs`, `/projects`, `/catalog/...`) continue to work for backward compatibility but emit a `Deprecation: true` response header. New integrations should target `/v1`.
  - **Storage backend abstraction.** `backend/src/voiceforge/services/storage.py` defines an `ArtifactStorage` Protocol with two implementations: `LocalArtifactStorage` (default, writes under `ARTIFACT_ROOT`) and `S3ArtifactStorage` (S3 / MinIO / Cloudflare R2 via `boto3`, lazy-imported). Selected via `STORAGE_BACKEND=local|s3` plus `S3_*` environment variables. `LocalArtifactStorage` rejects any key that resolves outside the artifact root.
  - **Production overlay (`docker-compose.prod.yml`).** Adds restart policies, resource limits, structured JSON logging, and removes the Docker socket mount on the API container (masked with `/dev/null` because Compose merges volumes by mount-point). Drops Postgres/Redis host port bindings via `ports: !reset []` (Compose v2.24+).
  - **nginx + multi-stage frontend (`frontend/Dockerfile.prod`, `frontend/nginx.conf`).** Builds the React bundle in a node stage and serves it through nginx with SPA fallback, gzip, and immutable asset caching.
  - **In-process token-bucket rate limiter (`backend/src/voiceforge/rate_limit.py`).** Per-client (API key or IP) bucket. Disabled when `RATE_LIMIT_PER_MINUTE=0`. Returns HTTP 429 with `Retry-After`. Stale buckets are swept once per window to prevent unbounded growth. Only honors the `X-API-Key` discriminator when the header value is in the allowed set, so untrusted callers cannot rotate it to rent fresh quotas.
  - **Prometheus metrics (`backend/src/voiceforge/observability.py`, `/metrics`).** Tracks HTTP request rate, duration, and status; job state transitions; in-flight gauge. Path label is bounded to the matched route template (or a `__unmatched__` sentinel) to prevent cardinality DoS. Metric updates flow exclusively through a single API-side Redis subscriber so worker-originated transitions remain visible to the API's `REGISTRY`. The in-flight gauge is seeded from the database at startup and clamped to ≥ 0 to survive restarts. Disabled when `METRICS_ENABLED=false`.

### Changed
- `services_jobs.process_job` re-checks the job's `status` from the database before each terminal write (cache-hit success, synth success, synth failure) so a concurrent `cancel_job` is no longer overwritten by a stale `succeeded`/`failed`.

### Security
- `LocalArtifactStorage` resolves and validates artifact keys against the storage root — `..`/absolute paths in keys raise `ValueError`.
- `S3ArtifactStorage.exists()` only returns `False` for canonical 404 responses; 403 / network / credential errors propagate so callers don't silently treat inaccessible objects as missing.

## Epic 1 → Epic 3 (merged into `main` ahead of [Unreleased] tag)

### Added
- **Operational safety (Epic 1).** Migrations are now the single source of truth in production: `db.init_db()` only runs `Base.metadata.create_all` when `APP_ENV` is `development` or `test`. A dedicated `migrate` service in `docker-compose.yml` runs `alembic upgrade head` before `api` and `worker` start.
- `backend/VERSION` (1.0.0) and `settings.app_version`. The `/health` endpoint now returns `version`, `app_env`, and `alembic_revision`. Every response carries an `X-App-Version` header.
- Healthchecks on `postgres`, `redis`, and `api`; `depends_on.condition: service_healthy` / `service_completed_successfully` wiring.
- FastAPI lifespan replaces `@app.on_event`. Catalog refresh runs as a background asyncio task with a per-provider `VOICE_CATALOG_REFRESH_TIMEOUT_SECONDS` (default 8s) so a slow provider can't block startup.
- `APP_ALLOWED_ORIGINS` (CSV) drives CORS allowlist; the `*` default is gone.
- Stale-job reaper (`services_jobs.reap_stale_jobs`) runs every `JOB_REAPER_INTERVAL_SECONDS` and marks jobs failed after `JOB_MAX_RUNTIME_SECONDS` (default 900s) so worker crashes no longer leave jobs stuck.
- `scripts/db_backup.sh` / `scripts/db_restore.sh` and Makefile targets `db-backup`, `db-restore`, plus migration ergonomics: `migrate-down`, `migrate-status`, `migrate-history`, `migrate-revision m=`, `migrate-autogenerate m=`, `migrate-reset`, `migrate-docker`.
- **Tooling & quality gate (Epic 2).** Ruff + Black + Mypy configured in `backend/pyproject.toml`; ESLint + Prettier + Vitest configured in `frontend/`. Pre-commit hooks (`.pre-commit-config.yaml`). GitHub Actions CI runs lint, typecheck, and tests for both stacks on every PR. Initial smoke-test suites: 11 pytest + 8 vitest cases.
- **Encryption-at-rest for provider secrets.** `APP_ENCRYPTION_KEY` (Fernet) transparently encrypts secret-flagged fields in `app_settings.value_json` on write and decrypts on read; legacy plaintext rows continue to read cleanly during the rollout window.
- `CHANGELOG.md`, `scripts/bump_version.sh`, and `.github/workflows/release.yml` for tag-driven releases.
- **Feature gaps (Epic 3).**
  - `POST /jobs/{id}/cancel` and `POST /jobs/{id}/retry` so users can stop runaway jobs and re-run failed ones without recreating them. Cancel/retry buttons surface in the Jobs table for cancelable/retryable rows.
  - `GET /jobs` accepts `limit`, `offset`, `status`, `provider_key`, `project_key`, `q` and returns `total/limit/offset` so the UI can paginate and filter.
  - Live SSE stream (`/events/stream`) now consumes a Redis pub/sub channel (`voiceforge:jobs`) instead of polling. State transitions in `services_jobs` publish notifications, so updates land sub-second; a heartbeat fallback keeps the stream alive when Redis is unreachable.
  - Optional API-key auth via `APP_API_KEYS` (CSV). The `X-API-Key` header (or `?api_key=` for SSE) gates everything except `/health`. When the variable is empty, the gate is a no-op for backward compatibility. Frontend reads `VITE_API_KEY` and injects it through `apiFetch` + the `EventSource` URL.
  - HTML5 drag-and-drop reordering for ScriptEditor rows (in addition to the existing up/down buttons).
  - Inline `<audio>` player on the Jobs detail panel so users can preview artifacts without leaving the page.
  - i18n message catalogs split into `src/i18n/en.json` + `src/i18n/vi.json`; `i18n.tsx` only owns the provider/hook surface now.
  - Design tokens (`--vf-color-*`, `--vf-radius-*`, `--vf-space-*`) declared at the top of `styles.css`; new components consume them.
  - `<ErrorBoundary>` wraps the app at the root; `Skeleton` / `SkeletonBlock` components for loading states.
- **Production readiness (Epic 4).**
  - API mounted under `/v1` (canonical) in addition to the legacy un-versioned routes — clients can migrate at their own pace.
  - `prometheus-client` integration: `/metrics` (Prometheus text format) gated by `METRICS_ENABLED`. HTTP request rate / latency, job state transitions, and in-flight gauge are tracked.
  - In-process token-bucket rate limiter (`RATE_LIMIT_PER_MINUTE`, default 0=disabled). Per-client buckets keyed by API key when present, otherwise remote IP. Returns 429 with `Retry-After`.
  - Pluggable artifact storage (`STORAGE_BACKEND=local|s3`). `S3ArtifactStorage` uses `boto3` (S3 / MinIO / R2). Local backend remains the default.
  - `docker-compose.prod.yml` overlay: drops the docker socket from the api container, removes host port bindings for postgres/redis, adds restart policies + memory limits + structured log rotation, and replaces the dev frontend with the multi-stage nginx image.
  - Frontend Dockerfile now ships an `nginx.conf` with SPA fallback (`try_files`), long-lived asset caching, gzip, and a `/healthz` endpoint for the load balancer.

### Deferred
- **JWT auth + workspace boundary (E4.5).** Multi-tenant isolation requires schema changes (users, workspaces, role grants) and is tracked separately. The current API-key gate (Epic 3) covers single-user / per-deployment auth.

### Changed (Epic 1–3)
- `docker-compose.yml` now serializes `migrate → api/worker` and exposes `APP_ALLOWED_ORIGINS` to the API container.
- `services_catalog.refresh_catalog` calls each provider's `list_voices` through a per-call timeout and never raises on provider errors.

### Security (Epic 1–3)
- CORS no longer accepts wildcard origins by default; configure `APP_ALLOWED_ORIGINS` per environment.
- Provider API keys, tokens, and Azure/Google credentials stored in `app_settings` are encrypted at rest when `APP_ENCRYPTION_KEY` is set.

## [1.0.0] - 2025-10-01

### Added
- Initial public release of VoiceForge Studio (multi-engine TTS orchestration with VOICEVOX, Piper, Kokoro, VieNeu, OpenAI, ElevenLabs, Google Cloud TTS, Azure Speech).

[Unreleased]: https://github.com/truongqv12/ntd_audio/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/truongqv12/ntd_audio/releases/tag/v1.0.0
