# Kiến trúc

> **Dành cho AI agent:** đây là các bất biến cần tôn trọng khi sửa code. Đọc trước khi chỉnh bất cứ thứ gì đi qua biên giới process (API ↔ worker), schema, hoặc engine bên ngoài.
>
> **Dành cho người đọc:** topology hệ thống, vai trò từng thành phần, và vòng đời của một job synthesis.

## TL;DR

- Năm process chạy dài: **api**, **worker**, **postgres**, **redis**, **frontend**. Các engine sidecar (**voicevox**, **piper-runtime**, **kokoro-runtime**, **vieneu-runtime**) bật/tắt qua Compose overlay.
- **PostgreSQL** giữ toàn bộ state bền (job, project, voice catalog, artifact metadata, app settings).
- **Redis** chở hai thứ: queue Dramatiq và channel pub/sub `voiceforge:jobs` để fan out state changes cho SSE và metrics.
- Chỉ **API** export Prometheus. Mọi thay đổi state từ worker đến được REGISTRY của API thông qua subscriber loop trên Redis.
- **Storage** plug được: local filesystem mặc định; S3-compatible (S3, MinIO, Cloudflare R2) khi `STORAGE_BACKEND=s3`.

## Topology

```mermaid
flowchart LR
  subgraph clients[Client]
    browser([Browser])
    cli([API client / CLI])
  end

  subgraph edge[Edge]
    nginx[nginx<br/>SPA + reverse proxy]
  end

  subgraph app[Application processes]
    api[api<br/>FastAPI :8000]
    worker[worker<br/>Dramatiq]
  end

  subgraph data[Data plane]
    pg[(postgres :5432)]
    redis[(redis :6379)]
  end

  subgraph engines[Engine sidecar]
    voicevox[voicevox]
    piper[piper-runtime]
    kokoro[kokoro-runtime]
    vieneu[vieneu-runtime]
  end

  subgraph storage[Lưu trữ artifact]
    local[(Local FS)]
    s3[(S3 / MinIO / R2)]
  end

  browser --> nginx
  cli --> nginx
  nginx -->|HTTP + SSE| api

  api <-->|SQL| pg
  api -->|enqueue| redis
  api <-->|pub/sub| redis

  worker -->|dequeue| redis
  worker -->|publish| redis
  worker <-->|SQL| pg
  worker -->|HTTP| voicevox
  worker -->|HTTP| piper
  worker -->|HTTP| kokoro
  worker -->|HTTP| vieneu
  worker -->|HTTPS| cloud((Cloud TTS<br/>OpenAI · ElevenLabs<br/>Google · Azure))
  worker --> local
  worker --> s3
```

## Vòng đời job

```mermaid
sequenceDiagram
  participant U as Client
  participant A as API
  participant DB as PostgreSQL
  participant R as Redis
  participant W as Worker
  participant E as Engine
  participant S as Storage

  U->>A: POST /v1/jobs
  A->>DB: INSERT job(status=queued)
  A->>R: ENQUEUE process_job(id)
  A->>R: PUBLISH voiceforge:jobs {reason=created}
  A-->>U: 201 Created (id, status=queued)

  R->>W: deliver task
  W->>DB: SELECT job WHERE id=:id
  W->>DB: UPDATE status=running
  W->>R: PUBLISH {reason=started}

  alt Cache hit
    W->>DB: SELECT generation_cache
    W->>DB: refresh status (kiểm tra cancel)
    W->>DB: UPDATE status=succeeded
    W->>R: PUBLISH {reason=succeeded}
  else Synth path
    W->>E: synthesize(text, voice, params)
    E-->>W: audio bytes
    W->>S: ghi artifact
    W->>DB: INSERT artifact, INSERT cache row
    W->>DB: refresh status (kiểm tra cancel)
    W->>DB: UPDATE status=succeeded
    W->>R: PUBLISH {reason=succeeded}
  end

  Note over A,R: API subscriber nhận mọi reason
  R-->>A: SSE snapshot signature đổi → push
```

## Biên giới process: chia sẻ và không chia sẻ

| Tài nguyên | API | Worker | Ghi chú |
|---|---|---|---|
| Pool kết nối PostgreSQL | có | có | pool độc lập; transaction không thấy commit chưa được commit của bên khác |
| Kết nối Redis | có | có | cả hai publish; chỉ API subscribe cho metrics + SSE |
| Prometheus `REGISTRY` | có (expose `/metrics`) | có (không bao giờ scrape) | **không bao giờ** record metric ở worker — sẽ biến mất |
| In-memory rate-limit bucket | có | n/a | rate limit chỉ có nghĩa trước HTTP |
| Cache catalog ở module level | có | có (độc lập) | refresh chỉ ở API; worker đọc lại từ DB |
| Filesystem artifact | khi `STORAGE_BACKEND=local` | khi `STORAGE_BACKEND=local` | cả hai phải mount cùng volume |

## Cấu trúc `backend/src/voiceforge/`

```
main.py                 FastAPI app, lifespan, middleware, /metrics
api_router.py           build router /v1 + alias legacy
routes_jobs.py          POST/GET/cancel/retry job
routes_events.py        SSE
routes_health.py        /health, /version
schemas.py              Pydantic v2 input/output
models.py               SQLAlchemy ORM
enums.py                JobStatus, ArtifactKind, ...
db.py                   engine, SessionLocal, init_db
config.py               settings (pydantic-settings)
events_bus.py           helper Redis pub/sub
observability.py        Prometheus counters / gauges / histograms
rate_limit.py           middleware token-bucket
security/api_key.py     dependency check X-API-Key
security/encryption.py  Fernet wrap/unwrap cho secret
services/storage.py     ArtifactStorage Protocol + Local + S3
services_jobs.py        process_job, cancel_job, retry_job, reap_stale_jobs
services_catalog.py     refresh_catalog, voice search
services_app_settings.py settings theo namespace
services_projects.py    project CRUD + ensure_project
tasks.py                actor Dramatiq gọi process_job
providers/              adapter cloud + OSS
```

## Vì sao tách worker process

- **Cô lập dependency.** SDK cloud (Google, Azure) và SDK OSS engine kéo theo nhiều native dependency. Giữ chúng ngoài API container giảm kích thước image và thời gian khởi động.
- **Cô lập lỗi.** Một provider treo HTTP call vô hạn — vấn đề đó nằm trong worker, không kéo API down.
- **Hình thái scale.** Synthesis là CPU-bound (OSS) hoặc latency-bound (cloud). Scale worker theo chiều ngang độc lập với API request load.

## Vì sao mỗi OSS engine một sidecar riêng

- Mỗi engine có dependency graph Python riêng (Piper cần `piper-tts`, Kokoro cần `kokoro` + `torch`, VieNeu dùng SDK riêng). Trộn lại tạo xung đột pin.
- Mỗi engine có lifecycle download model riêng (Piper tải voice, Kokoro tải weights HuggingFace).
- Compose overlay bật/tắt từng engine độc lập.

## Chiến lược SSE

- Browser mở `GET /v1/events/stream` và nhận event `snapshot` ngay lập tức.
- Server chờ pub/sub Redis trên channel `voiceforge:jobs`. Mỗi message mang `reason` (`created`/`started`/`succeeded`/`failed`/`canceled`/`retried`/`reaped_failed`) và payload tùy chọn.
- Heartbeat phát mỗi `EVENT_STREAM_HEARTBEAT_SECONDS` (mặc định 15s). Nếu signature snapshot không đổi từ lần push trước, chỉ gửi `event: heartbeat` — browser không phải reconcile.
- Hàm `_snapshot_with_signature()` đọc signature **trước** rồi đọc snapshot trong cùng một DB session, đảm bảo client không nhận được snapshot có signature đi trước data.

## Hủy job và state đồng thời

`cancel_job` chạy trong process API và commit `status=canceled` độc lập với `process_job` đang chạy ở worker. Không có cơ chế phối hợp, worker có thể overwrite `canceled` bằng `succeeded`/`failed` cũ. Cách xử lý:

- `services_jobs._was_canceled_concurrently(db, job)` gọi `db.refresh(job, attribute_names=["status"])` để thấy commit của API (Read Committed isolation đủ).
- Worker gọi nó trước mỗi terminal write: cache-hit success, synth success, synth failure.

## Chọn storage backend

```mermaid
flowchart TD
  start[write_artifact gọi] --> cfg{STORAGE_BACKEND}
  cfg -->|local| local_resolve["LocalArtifactStorage<br/>_resolve(key)"]
  cfg -->|s3| s3_put["S3ArtifactStorage<br/>boto3.put_object"]
  local_resolve --> traversal{key thoát ra<br/>khỏi ARTIFACT_ROOT?}
  traversal -->|có| raise[ValueError]
  traversal -->|không| write_local[ghi trong root]
  s3_put --> done[ok]
  write_local --> done
```

## Observability

```mermaid
flowchart LR
  api_mw[API middleware] -->|HTTP latency,<br/>status, route| reg[(REGISTRY ở API)]
  worker_event[Worker job event] --> pub[publish_jobs_changed] --> redis[(Redis<br/>voiceforge:jobs)]
  api_event[API job event] --> pub
  redis --> sub[_metrics_subscriber<br/>trong API lifespan]
  sub -->|record_job_event| reg
  reg --> metrics[/metrics<br/>Prometheus scrape/]
```

Thiết kế single-subscriber là then chốt: mọi state transition — bất kể process nào phát sinh — đều đi qua REGISTRY của API. Gauge in-flight được seed từ database lúc startup và clamp `≥ 0` để khởi động lại không bao giờ ra số âm.

## Mặt cấu hình

Toàn bộ cấu hình điều khiển bằng biến môi trường. Tham khảo [`self-hosting.md`](self-hosting.md) cho danh sách đầy đủ. Module `config.py` load qua pydantic-settings; default giữ ở mức an toàn cho cài đặt single-user local.

## Các quyết định chủ động trì hoãn

Đây là khoảng trống cố ý; xem [`feature-map.md`](feature-map.md) để biết trạng thái:

- **Auth multi-user.** Hiện một CSV `APP_API_KEYS` chia sẻ chung cho cả API; chưa có model user hay workspace isolation.
- **Worker scaling.** Dramatiq hỗ trợ nhiều replica, nhưng priority queue, dead-letter, và per-project concurrency cap chưa làm.
- **Telemetry.** Không thu thập số liệu sử dụng ẩn danh.
