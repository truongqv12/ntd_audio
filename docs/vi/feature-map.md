# Bản đồ tính năng

> **Dành cho AI agent:** đây là tham chiếu chính thức "có gì / không có gì". Trước khi tuyên bố tính năng thiếu, search code; trước khi tuyên bố có, hãy chạy thử.
>
> **Dành cho người đọc:** mọi tính năng, nhóm theo nơi nó land.

## TL;DR

- Sản phẩm **đủ vận hành cho self-host** ngay hôm nay (Epic 1 → Epic 4 đã merge).
- "Production-ready cho SaaS multi-tenant" cần các mục trong [Roadmap](#roadmap).

```mermaid
flowchart TB
  root[ntd_audio]

  root --> e1[Epic 1<br/>Operational safety]
  root --> e2[Epic 2<br/>Tooling & quality]
  root --> e3[Epic 3<br/>Feature gaps]
  root --> e4[Epic 4<br/>Production readiness]
  root --> nx[Tiếp theo<br/>Backlog mở]

  e1 --> e1a[Migration safety]
  e1 --> e1b[Healthcheck]
  e1 --> e1c[Lifespan + reaper]
  e1 --> e1d[Script backup/restore]

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
  e3 --> e3g[i18n JSON catalog]
  e3 --> e3h[Design token]
  e3 --> e3i[Error boundary + skeleton]

  e4 --> e4a[/v1 versioning]
  e4 --> e4b[Storage abstraction]
  e4 --> e4c[Prod compose overlay]
  e4 --> e4d[nginx + multi-stage]
  e4 --> e4e[Rate limit]
  e4 --> e4f[Prometheus /metrics]

  root --> personal[Personal-use roadmap<br/>T1–T3]
  personal --> p1[T1.1 Bulk import TXT/CSV]
  personal --> p2[T1.2 Multi-voice / dialogue]
  personal --> p3[T1.3 Subtitle .srt/.vtt]
  personal --> p4[T1.4 Inline preview]
  personal --> p5[T1.5 Project export bundle]
  personal --> p6[T2.6 GPU/CPU auto-detect]
  personal --> p7[T2.7 Per-provider concurrency]
  personal --> p8[T2.8 ArtifactStorage wired]
  personal --> p9[T3.9 Provider plugin entry points]
  personal --> p10[T3.10 Retention preview/purge]
  personal --> p11[T3.11 Playwright smoke harness]

  nx --> nx1[Conversation-mode multi-voice UX]
  nx --> nx2[Đường đọc S3 / presigned URL]
  nx --> nx3[Subtitle import + đóng vào export.zip]
  nx --> nx4[Telemetry device per-engine]
  nx --> nx5[Lưu override concurrency vào Settings]
```

## Epic 1 — Operational safety

| Tính năng | Trạng thái | Ở đâu |
|---|---|---|
| Migration gate (`init_db` chỉ `create_all` ở dev/test) | ✅ | `backend/src/voiceforge/db.py` |
| Service Compose `migrate` serialize `migrate → api/worker` | ✅ | `docker-compose.yml` |
| `/health` trả version + alembic revision + reachability provider | ✅ | `backend/src/voiceforge/routes_health.py` |
| Healthcheck Postgres / Redis / API | ✅ | `docker-compose.yml` |
| FastAPI lifespan với refresh catalog có timeout | ✅ | `backend/src/voiceforge/main.py` |
| Stale-job reaper | ✅ | `backend/src/voiceforge/services_jobs.py::reap_stale_jobs` |
| `db_backup.sh` / `db_restore.sh` + Make target | ✅ | `scripts/`, `Makefile` |
| `APP_ALLOWED_ORIGINS` (không CORS wildcard) | ✅ | `backend/src/voiceforge/main.py` |

## Epic 2 — Tooling & quality

| Tính năng | Trạng thái | Ở đâu |
|---|---|---|
| Ruff, Black, Mypy | ✅ | `backend/pyproject.toml` |
| ESLint, Prettier | ✅ | `frontend/.eslintrc`, `.prettierrc` |
| Bộ smoke test pytest | ✅ | `backend/tests/` |
| Bộ smoke test vitest | ✅ | `frontend/src/test/` |
| Pre-commit hook | ✅ | `.pre-commit-config.yaml` |
| GitHub Actions CI (lint + type + test cả hai stack) | ✅ | `.github/workflows/ci.yml` |
| Encryption-at-rest cho secret provider (Fernet) | ✅ | `backend/src/voiceforge/security/encryption.py` |
| `CHANGELOG.md` + `bump_version.sh` + release workflow | ✅ | repo root, `scripts/`, `.github/workflows/release.yml` |

## Epic 3 — Feature gap

| Tính năng | Trạng thái | Ở đâu |
|---|---|---|
| Cancel job (`POST /v1/jobs/{id}/cancel`) | ✅ | `backend/src/voiceforge/routes_jobs.py` |
| Retry job (`POST /v1/jobs/{id}/retry`) | ✅ | `backend/src/voiceforge/routes_jobs.py` |
| An toàn cancel đồng thời ở worker | ✅ | `backend/src/voiceforge/services_jobs.py::_was_canceled_concurrently` |
| List job có phân trang + filter | ✅ | `backend/src/voiceforge/routes_jobs.py` |
| SSE driven by Redis pub/sub | ✅ | `backend/src/voiceforge/routes_events.py`, `events_bus.py` |
| API-key auth (`X-API-Key`, SSE `?api_key=`) | ✅ | `backend/src/voiceforge/security/api_key.py` |
| Drag-and-drop reorder ScriptEditor | ✅ | `frontend/src/pages/ScriptEditor.tsx` |
| Inline `<audio>` player artifact | ✅ | `frontend/src/components/Jobs.tsx` |
| Catalog `i18n/{en,vi}.json` | ✅ | `frontend/src/i18n/` |
| CSS design token | ✅ | `frontend/src/styles.css` |
| `<ErrorBoundary>` + skeleton loader | ✅ | `frontend/src/components/` |

## Epic 4 — Production readiness

| Tính năng | Trạng thái | Ở đâu |
|---|---|---|
| Mount `/v1` (kèm alias legacy + header `Deprecation`) | ✅ | `backend/src/voiceforge/api_router.py` |
| Protocol `ArtifactStorage` + backend `Local` + `S3` | ✅ | `backend/src/voiceforge/services/storage.py` |
| Chặn path traversal trên backend local | ✅ | `LocalArtifactStorage._resolve` |
| Chỉ swallow 404 trong S3 `exists()` | ✅ | `S3ArtifactStorage.exists` |
| `docker-compose.prod.yml` (không host binding, không Docker socket) | ✅ | repo root |
| Multi-stage frontend Dockerfile + cấu hình nginx | ✅ | `frontend/Dockerfile.prod`, `frontend/nginx.conf` |
| Token-bucket rate limiter | ✅ | `backend/src/voiceforge/rate_limit.py` |
| Prometheus `/metrics` với pipeline metric single-subscriber | ✅ | `backend/src/voiceforge/observability.py`, `main.py::_metrics_subscriber` |
| Gauge in-flight seed từ DB + clamp ≥ 0 | ✅ | `main.py::lifespan`, `observability.py::record_job_event` |

## Personal-use roadmap (T1–T3)

Tất cả mục dưới đây được bổ sung trên Epic 4 để phù hơp hơn với hình dạng triển khai **single-user, single-host Docker**. Xem [`optimization-and-roadmap.md`](optimization-and-roadmap.md) để có acceptance criteria và ghi chú migration gốc.

| Tính năng | Trạng thái | Vị trí |
|---|---|---|
| T1.1 — Bulk import TXT/CSV (`POST /v1/projects/{key}/rows/bulk`) | ✅ | `routes_project_rows.py`, `services_bulk_import.py` |
| T1.1 — Project artifacts zip (`GET /v1/projects/{key}/rows/artifacts.zip`) | ✅ | `routes_project_rows.py::download_artifacts_zip` |
| T1.1 — Modal `BulkImportDialog` trong script editor | ✅ | `frontend/src/components/BulkImportDialog.tsx` |
| T1.2 — `speaker_label` trên script row (dialogue mode tối thiểu) | ✅ | `models.ProjectScriptRow.speaker_label`, alembic `20260424_0004` |
| T1.3 — Subtitle output `.srt` / `.vtt` (`GET /v1/projects/{key}/rows/subtitles`) | ✅ | `services_subtitles.py`, `routes_project_rows.download_project_subtitles` |
| T1.4 — Preview 1 row on-demand (`POST /v1/providers/{key}/preview`) | ✅ | `routes_providers.py::preview_arbitrary_text` |
| T1.5 — Bundle export project (`GET /v1/projects/{key}/export.zip`) | ✅ | `services_project_export.py`, `routes_projects.py` |
| T2.6 — Probe capability host (`GET /v1/system/capabilities`) | ✅ | `services_system.py`, `routes_system.py`, Settings → panel Host |
| T2.7 — Concurrency limit per-provider (`PROVIDER_CONCURRENCY`) | ✅ | `services_provider_concurrency.py`, `services_jobs.process_job` |
| T2.8 — `write_artifact` route qua `ArtifactStorage` | ✅ | `storage.py::write_artifact`, `services/storage.py::get_storage` |
| T3.9 — Provider plugin entry points (group `voiceforge.providers`) | ✅ | `backend/src/voiceforge/provider_registry.py` |
| T3.10 — Retention preview/purge (`/v1/admin/retention/{preview,purge}`) | ✅ | `backend/src/voiceforge/services_retention.py`, `routes_retention.py` |
| T3.11 — Harness Playwright smoke (`npm run test:e2e`) | ✅ | `frontend/playwright.config.ts`, `frontend/e2e/smoke.spec.ts` |

## Roadmap (backlog mở)

Rationale đầy đủ, acceptance criteria, và ghi chú migration cho mỗi mục có trong [`optimization-and-roadmap.md`](optimization-and-roadmap.md). Bảng dưới đây là index ngắn cho công việc **chưa** thực hiện.

Đây là backlog chưa commit — thứ tự là gợi ý theo impact, không phải cam kết. Các mục multi-user / SaaS (JWT, Helm, telemetry, worker DLQ) cố tình không có mặt ở đây — xem phần "Out of scope" trong `optimization-and-roadmap.md`.

| Mục | Lý do |
|---|---|
| **Conversation-mode multi-voice UX** | `speaker_label` hôm nay chỉ là string. Panel nặng hơn để map `speaker_label → provider_voice_id` và auto-fill khi thêm row mới vẫn deferred. |
| **Đường đọc S3 / presigned URL** | T2.8 wire **đường ghi** qua `ArtifactStorage`. Đường đọc (`artifact_absolute_path` + `FileResponse`) vẫn local-fs only. |
| **Subtitle import + đóng vào export.zip** | Bundle T1.5 chưa kèm `subtitles/` lẫn TXT/CSV gốc. Kèm `POST /v1/projects/import` là follow-up tự nhiên. |
| **Telemetry device per-engine** | Hôm nay `/v1/system/capabilities` báo cáo thứ mà container **API** thấy. Báo cáo mỗi engine đã load trên device nào (CPU vs CUDA) là mở rộng để mở. |
| **Lưu override concurrency vào Settings** | Limit T2.7 hiện driven by env. Panel Settings → "Performance" lưu override vào `app_settings` sẽ bớt phải reload env. |
| **i18n: thêm locale** | JP / ZH / KR là khả năng cao do engine ship. |
| **Tăng frontend test coverage** | Bộ smoke cố tình nhỏ. Critical path (tạo job, settings, ScriptEditor) đáng có test ở mức component. |
