# Changelog

All notable changes to VoiceForge Studio are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- `docker-compose.yml` now serializes `migrate → api/worker` and exposes `APP_ALLOWED_ORIGINS` to the API container.
- `services_catalog.refresh_catalog` calls each provider's `list_voices` through a per-call timeout and never raises on provider errors.

### Security
- CORS no longer accepts wildcard origins by default; configure `APP_ALLOWED_ORIGINS` per environment.
- Provider API keys, tokens, and Azure/Google credentials stored in `app_settings` are encrypted at rest when `APP_ENCRYPTION_KEY` is set.

## [1.0.0] - 2025-10-01

### Added
- Initial public release of VoiceForge Studio (multi-engine TTS orchestration with VOICEVOX, Piper, Kokoro, VieNeu, OpenAI, ElevenLabs, Google Cloud TTS, Azure Speech).

[Unreleased]: https://github.com/truongqv12/ntd_audio/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/truongqv12/ntd_audio/releases/tag/v1.0.0
