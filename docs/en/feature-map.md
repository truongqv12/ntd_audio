# Feature map

> **For AI agents:** this is the canonical "what exists / what doesn't" reference. Before claiming a feature is missing, search the code; before claiming one is present, run it.
>
> **For humans:** every feature, grouped by where it landed.

## TL;DR

- The product is **operationally ready for self-host** today (Epic 1 → Epic 4 merged).
- "Production-ready for a multi-tenant SaaS" needs the items in [Roadmap](#roadmap).

```mermaid
flowchart TB
  root[ntd_audio]

  root --> e1[Epic 1<br/>Operational safety]
  root --> e2[Epic 2<br/>Tooling & quality]
  root --> e3[Epic 3<br/>Feature gaps]
  root --> e4[Epic 4<br/>Production readiness]
  root --> nx[Next<br/>Open backlog]

  e1 --> e1a[Migration safety]
  e1 --> e1b[Healthchecks]
  e1 --> e1c[Lifespan + reaper]
  e1 --> e1d[Backup/restore scripts]

  e2 --> e2a[Ruff + Black + Mypy]
  e2 --> e2b[ESLint + Prettier + Vitest]
  e2 --> e2c[CI + pre-commit]
  e2 --> e2d[Encryption-at-rest]
  e2 --> e2e[CHANGELOG + release]

  e3 --> e3a[Cancel + retry]
  e3 --> e3b[Pagination + filter]
  e3 --> e3c[Redis pub/sub SSE]
  e3 --> e3d[API-key auth]
  e3 --> e3e[Drag-drop ScriptEditor]
  e3 --> e3f[Inline audio player]
  e3 --> e3g[i18n JSON catalogs]
  e3 --> e3h[Design tokens]
  e3 --> e3i[Error boundary + skeletons]

  e4 --> e4a[/v1 versioning]
  e4 --> e4b[Storage abstraction]
  e4 --> e4c[Prod compose overlay]
  e4 --> e4d[nginx + multi-stage]
  e4 --> e4e[Rate limit]
  e4 --> e4f[Prometheus /metrics]

  nx --> nx1[ArtifactStorage wiring into write_artifact]
  nx --> nx2[JWT / multi-user auth]
  nx --> nx3[Worker scaling + DLQ]
  nx --> nx4[E2E tests]
  nx --> nx5[Provider plugin system]
  nx --> nx6[Helm chart]
  nx --> nx7[Telemetry opt-in]
  nx --> nx8[Artifact GC]
```

## Epic 1 — Operational safety

| Feature | Status | Where |
|---|---|---|
| Migration gate (`init_db` runs `create_all` only in dev/test) | ✅ | `backend/src/voiceforge/db.py` |
| Compose `migrate` service serializes `migrate → api/worker` | ✅ | `docker-compose.yml` |
| `/health` returns version + alembic revision + provider reachability | ✅ | `backend/src/voiceforge/routes_health.py` |
| Postgres / Redis / API healthchecks | ✅ | `docker-compose.yml` |
| FastAPI lifespan with bounded catalog refresh | ✅ | `backend/src/voiceforge/main.py` |
| Stale-job reaper | ✅ | `backend/src/voiceforge/services_jobs.py::reap_stale_jobs` |
| `db_backup.sh` / `db_restore.sh` + Makefile targets | ✅ | `scripts/`, `Makefile` |
| `APP_ALLOWED_ORIGINS` (no wildcard CORS) | ✅ | `backend/src/voiceforge/main.py` |

## Epic 2 — Tooling and quality

| Feature | Status | Where |
|---|---|---|
| Ruff, Black, Mypy | ✅ | `backend/pyproject.toml` |
| ESLint, Prettier | ✅ | `frontend/.eslintrc`, `.prettierrc` |
| pytest smoke suite | ✅ | `backend/tests/` |
| vitest smoke suite | ✅ | `frontend/src/test/` |
| Pre-commit hooks | ✅ | `.pre-commit-config.yaml` |
| GitHub Actions CI (lint + type + test on both stacks) | ✅ | `.github/workflows/ci.yml` |
| Encryption-at-rest for provider secrets (Fernet) | ✅ | `backend/src/voiceforge/security/encryption.py` |
| `CHANGELOG.md` + `bump_version.sh` + release workflow | ✅ | repo root, `scripts/`, `.github/workflows/release.yml` |

## Epic 3 — Feature gaps

| Feature | Status | Where |
|---|---|---|
| Cancel job (`POST /v1/jobs/{id}/cancel`) | ✅ | `backend/src/voiceforge/routes_jobs.py` |
| Retry job (`POST /v1/jobs/{id}/retry`) | ✅ | `backend/src/voiceforge/routes_jobs.py` |
| Concurrent-cancel safety in worker | ✅ | `backend/src/voiceforge/services_jobs.py::_was_canceled_concurrently` |
| Paginated job listing with filters | ✅ | `backend/src/voiceforge/routes_jobs.py` |
| Redis pub/sub-driven SSE | ✅ | `backend/src/voiceforge/routes_events.py`, `events_bus.py` |
| API-key auth (`X-API-Key`, SSE `?api_key=`) | ✅ | `backend/src/voiceforge/security/api_key.py` |
| HTML5 drag-and-drop ScriptEditor reorder | ✅ | `frontend/src/pages/ScriptEditor.tsx` |
| Inline `<audio>` artifact player | ✅ | `frontend/src/components/Jobs.tsx` |
| `i18n/{en,vi}.json` catalogs | ✅ | `frontend/src/i18n/` |
| CSS design tokens | ✅ | `frontend/src/styles.css` |
| `<ErrorBoundary>` + skeleton loaders | ✅ | `frontend/src/components/` |

## Epic 4 — Production readiness

| Feature | Status | Where |
|---|---|---|
| `/v1` mount (with legacy alias + `Deprecation` header) | ✅ | `backend/src/voiceforge/api_router.py` |
| `ArtifactStorage` Protocol + `Local` + `S3` backends | ✅ | `backend/src/voiceforge/services/storage.py` |
| Path-traversal guard on local backend | ✅ | `LocalArtifactStorage._resolve` |
| 404-only swallow on S3 `exists()` | ✅ | `S3ArtifactStorage.exists` |
| `docker-compose.prod.yml` (no host bindings, no Docker socket) | ✅ | repo root |
| Multi-stage frontend Dockerfile + nginx config | ✅ | `frontend/Dockerfile.prod`, `frontend/nginx.conf` |
| Token-bucket rate limiter | ✅ | `backend/src/voiceforge/rate_limit.py` |
| Prometheus `/metrics` with single-subscriber metric pipeline | ✅ | `backend/src/voiceforge/observability.py`, `main.py::_metrics_subscriber` |
| In-flight gauge seeded from DB + clamped to ≥ 0 | ✅ | `main.py::lifespan`, `observability.py::record_job_event` |
| T2.6 — Host capability probe (`GET /v1/system/capabilities`) | ✅ | `services_system.py`, `routes_system.py`, Settings → Host panel |
| T2.8 — `write_artifact` flows through `ArtifactStorage` | ✅ | `storage.py::write_artifact`, `services/storage.py::get_storage` |
| T3.10 — Retention preview/purge (`/v1/admin/retention/{preview,purge}`) | ✅ | `backend/src/voiceforge/services_retention.py`, `routes_retention.py` |
| T3.9 — Provider plugin entry points (`voiceforge.providers` group) | ✅ | `backend/src/voiceforge/provider_registry.py` |
| T3.11 — Playwright smoke harness (`npm run test:e2e`) | ✅ | `frontend/playwright.config.ts`, `frontend/e2e/smoke.spec.ts` |
| T1.5 — Project export bundle (`GET /v1/projects/{key}/export.zip`) | ✅ | `services_project_export.py`, `routes_projects.py` |

## Personal-use roadmap (T1+)

| Feature | Status | Where |
|---|---|---|
| T1.1 — Bulk import TXT/CSV (`POST /v1/projects/{key}/rows/bulk`) | ✅ | `routes_project_rows.py`, `services_bulk_import.py` |
| T1.1 — Project artifacts zip (`GET /v1/projects/{key}/rows/artifacts.zip`) | ✅ | `routes_project_rows.py::download_artifacts_zip` |
| T1.1 — `BulkImportDialog` modal in the script editor | ✅ | `frontend/src/components/BulkImportDialog.tsx` |
| T1.4 — On-demand single-row preview (`POST /v1/providers/{key}/preview`) | ✅ | `routes_providers.py::preview_arbitrary_text` |


## Personal-use roadmap (T1+)

| Feature | Status | Where |
|---|---|---|
| T2.7 — Per-provider concurrency limit (`PROVIDER_CONCURRENCY`) | ✅ | `services_provider_concurrency.py`, `services_jobs.process_job` |

## Personal-use roadmap (T1+)

| Feature | Status | Where |
|---|---|---|
| T1.2 — `speaker_label` on script rows (dialogue mode minimum) | ✅ | `models.ProjectScriptRow.speaker_label`, alembic `20260424_0004` |
| T1.3 — Subtitle download (`.srt` / `.vtt`) | ✅ | `services_subtitles.py`, `routes_project_rows.download_project_subtitles` |

## Roadmap

For the full rationale, acceptance criteria, and migration notes for each item, see [`optimization-and-roadmap.md`](optimization-and-roadmap.md). The table below is a short index.

These are not committed — order is suggestion based on impact, not a guarantee. Vote on issues for ones that matter to your install.

| Item | Why |
|---|---|
| **Wire `ArtifactStorage` into `write_artifact`** | The Protocol exists, but the legacy write path still touches the local FS directly. Operators set `STORAGE_BACKEND=s3` today and get a no-op. |
| **JWT / multi-user auth** | Current API-key gate is single-tenant. Multi-user installs need user accounts, sessions, and per-user audit. |
| **Worker scaling primitives** | Priority queues, dead-letter, per-project concurrency caps, drain-on-deploy. |
| **End-to-end tests** | A Playwright smoke suite that walks the create-job → wait → download flow on a real Compose stack. |
| **Provider plugin system** | Today, adding a provider requires editing the registry. A plugin loader (entry points) lets users ship their own without forking. |
| **Helm chart** | First-class Kubernetes deploy story. The Compose stack maps directly. |
| **Anonymous telemetry (opt-in)** | "How many installs run which engine" — feeds prioritization. Strict opt-in only. |
| **Artifact garbage collection** | Old artifacts and their cache rows accumulate. A configurable retention policy job. |
| **i18n: more locales** | JP / ZH / KR are likely first asks given the engines we ship. |
| **Frontend test coverage** | The smoke suite is intentionally small. Critical paths (job creation, settings, ScriptEditor) deserve component-level coverage. |
