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

  nx --> nx1[Wire ArtifactStorage vào write_artifact]
  nx --> nx2[JWT / multi-user auth]
  nx --> nx3[Worker scaling + DLQ]
  nx --> nx4[E2E test]
  nx --> nx5[Provider plugin system]
  nx --> nx6[Helm chart]
  nx --> nx7[Telemetry opt-in]
  nx --> nx8[Artifact GC]
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

## Roadmap

Rationale đầy đủ, acceptance criteria, và ghi chú migration cho mỗi mục có trong [`optimization-and-roadmap.md`](optimization-and-roadmap.md). Bảng dưới đây là index ngắn.

Đây là backlog chưa commit — thứ tự là gợi ý theo impact, không phải cam kết. Vote issue để nhấn ưu tiên.

| Mục | Lý do |
|---|---|
| **Wire `ArtifactStorage` vào `write_artifact`** | Protocol có sẵn nhưng đường ghi cũ vẫn đụng FS local trực tiếp. Operator set `STORAGE_BACKEND=s3` hôm nay là no-op. |
| **JWT / multi-user auth** | Gate API-key hiện tại single-tenant. Cài đặt multi-user cần user account, session, audit per-user. |
| **Primitive scale worker** | Priority queue, dead-letter, per-project concurrency cap, drain-on-deploy. |
| **End-to-end test** | Bộ smoke Playwright đi qua flow create-job → wait → download trên Compose stack thật. |
| **Provider plugin system** | Hôm nay thêm provider phải sửa registry. Plugin loader (entry point) cho user ship engine riêng mà không fork. |
| **Helm chart** | Story deploy Kubernetes first-class. Compose stack map sang gần như 1-1. |
| **Telemetry ẩn danh (opt-in)** | "Bao nhiêu install chạy engine nào" — feed prioritization. Strict opt-in. |
| **Garbage collection artifact** | Artifact và cache row cũ tích tụ. Job retention policy có cấu hình. |
| **i18n: thêm locale** | JP / ZH / KR là khả năng cao do engine ship. |
| **Tăng frontend test coverage** | Bộ smoke cố tình nhỏ. Critical path (tạo job, settings, ScriptEditor) đáng có test ở mức component. |
