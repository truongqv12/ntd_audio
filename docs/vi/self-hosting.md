# Self-hosting

> **Dành cho AI agent:** đổi default ở đây có thể khoá user thật khỏi data của họ. Coi mỗi env var là một phần của public contract. Biến mới phải default tắt / an toàn và phải được ghi vào `.env.example` trong cùng PR.
>
> **Dành cho người đọc:** chạy `ntd_audio` trên hạ tầng riêng — từ "máy laptop" đến "phơi mặt ra Internet".

## TL;DR

- Local dev: `cp .env.example .env && docker compose up --build`. Hết.
- Public: xếp chồng `docker-compose.prod.yml` và set `APP_API_KEYS`, `APP_ENCRYPTION_KEY`, `APP_ALLOWED_ORIGINS`, `RATE_LIMIT_PER_MINUTE`. TLS chấm dứt ở reverse proxy.
- Engine bật theo nhu cầu qua Compose overlay. Stack base chạy được mà không cần engine nào — phù hợp khi chỉ dùng cloud provider.

## Các stack Compose

| File | Mục đích |
|---|---|
| `docker-compose.yml` | Base: postgres, redis, migrate, api, worker, frontend |
| `docker-compose.prod.yml` | Hardening cho production (xếp lên trên base) |
| `docker-compose.oss.yml` | Tất cả 4 OSS engine |
| `docker-compose.gpu.yml` | VOICEVOX bản GPU (thay bản CPU) |
| `docker-compose.piper.yml` | Sidecar Piper |
| `docker-compose.kokoro.yml` | Sidecar Kokoro |
| `docker-compose.vieneu.yml` | Sidecar VieNeu-TTS |

Compose merge file từ trái sang phải. List (`ports`, `volumes`, `command`) **append** mặc định; overlay prod dùng `!reset []` (Compose v2.24+) để thực sự bỏ entry.

## Biến môi trường

`.env.example` là schema tham chiếu. Mọi biến dưới đây có default trừ khi đánh dấu **bắt buộc**.

### Core

| Biến | Default | Mô tả |
|---|---|---|
| `APP_ENV` | `development` | Quyết định `db.init_db()`. Trong `production`, chỉ Alembic làm chủ schema. |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Cổng API listen trong container. |
| `APP_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:4173` | CSV CORS origin. Rỗng = không cho CORS (nên dùng trong production khi proxy cùng origin). |
| `APP_API_KEYS` | rỗng | CSV API key. Rỗng = tắt auth (mở, phù hợp single-user local). |
| `APP_ENCRYPTION_KEY` | rỗng | Khóa Fernet để encrypt secret provider trong `app_settings`. Sinh bằng `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `DATABASE_URL` | postgres bundled | URL SQLAlchemy. Default trỏ đến service `postgres` trong Compose. |
| `REDIS_URL` | redis bundled | Dramatiq + pub/sub. |
| `LOG_LEVEL` | `INFO` | Verbosity log backend. |
| `LOG_FILE_PATH` | `/data/logs/voiceforge.log` | Đường dẫn file log rotating. |

### Storage

| Biến | Default | Mô tả |
|---|---|---|
| `ARTIFACT_ROOT` | `/data/artifacts` | Nơi lưu artifact audio cho backend local. |
| `CACHE_ROOT` | `/data/cache` | Thư mục generation cache. |
| `STORAGE_BACKEND` | `local` | `local` hoặc `s3`. |
| `S3_BUCKET` | rỗng | Bắt buộc khi `STORAGE_BACKEND=s3`. |
| `S3_REGION` | rỗng | Region AWS hoặc MinIO (vd `us-east-1`). |
| `S3_ENDPOINT_URL` | rỗng | Đặt cho MinIO / R2 / endpoint không phải AWS. |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | rỗng | Credentials. Trong AWS native nên dùng IAM role. |
| `S3_PREFIX` | rỗng | Prefix tùy chọn thêm vào mỗi object key. |

### Reliability

| Biến | Default | Mô tả |
|---|---|---|
| `JOB_MAX_RUNTIME_SECONDS` | `900` | Sau giới hạn này, reaper đánh dấu job kẹt là `failed`. |
| `JOB_REAPER_INTERVAL_SECONDS` | `60` | Tần suất chạy reaper. |
| `JOB_REAPER_ENABLED` | `true` | Chỉ tắt khi debug local. |
| `RATE_LIMIT_PER_MINUTE` | `120` | Token bucket per client. `0` = tắt. |

### Observability

| Biến | Default | Mô tả |
|---|---|---|
| `METRICS_ENABLED` | `true` | Mount `/metrics` và bật subscriber Redis ghi job transitions. |
| `EVENT_STREAM_HEARTBEAT_SECONDS` | `15` | Tần suất heartbeat SSE. |

### Refresh catalog

| Biến | Default | Mô tả |
|---|---|---|
| `VOICE_CATALOG_REFRESH_ON_START` | `true` | Refresh voice catalog lúc API startup (chạy nền). |
| `VOICE_CATALOG_REFRESH_TIMEOUT_SECONDS` | `8` | Timeout per-provider để provider chậm không block startup. |

### Env var cho provider

Xem [`providers.md`](providers.md). Mỗi engine có khối riêng. Giá trị rỗng = engine tắt.

## Overlay production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Thay đổi:

- `restart: unless-stopped` cho mọi service chạy dài.
- Resource limits qua `deploy.resources.limits` (Postgres 1g, Redis 256m, API 1g — chỉnh theo hardware).
- Log JSON có cấu trúc.
- **Bỏ binding host port của Postgres và Redis** (`ports: !reset []`). Internal Compose networking vẫn hoạt động.
- **Bỏ mount Docker socket** ở API container bằng cách mask `/var/run/docker.sock` bằng `/dev/null`. Tail log engine trong Monitor sẽ không hoạt động ở production — đó là trade-off cố ý.

## Checklist production

```
[ ] APP_API_KEYS là CSV các key random mạnh (≥ 32 byte mỗi key).
[ ] APP_ENCRYPTION_KEY đã đặt (khóa Fernet).
[ ] APP_ALLOWED_ORIGINS chỉ liệt kê origin frontend của bạn.
[ ] RATE_LIMIT_PER_MINUTE đặt theo quota provider / user.
[ ] STORAGE_BACKEND=s3 nếu muốn artifact ngoài đĩa host.
[ ] METRICS_ENABLED=true và /metrics chỉ mở cho Prometheus scrape ở proxy.
[ ] HTTPS chấm dứt ở reverse proxy. nginx.conf trong frontend là điểm khởi đầu — thêm TLS, HSTS, CSP ở edge.
[ ] docker-compose.prod.yml xếp lên trên base.
[ ] Có lịch db_backup.sh đã test (cron / systemd timer / managed Postgres snapshot).
[ ] Đã thử upgrade migration trên bản copy production.
```

## Reverse proxy

`frontend/nginx.conf` (dùng bởi `Dockerfile.prod`) lo SPA fallback, gzip, cache static asset. Nó **không** chấm dứt TLS. Đặt TLS proxy (Caddy, Traefik, AWS ALB, Cloudflare) phía trước rồi forward về nginx port 80.

Block Caddy tối thiểu:

```caddy
voiceforge.example.com {
  reverse_proxy /api/*  api:8000
  reverse_proxy /v1/*   api:8000
  reverse_proxy /health api:8000
  reverse_proxy /metrics api:8000  # restrict theo source IP nếu phơi ra
  reverse_proxy /events/* api:8000
  reverse_proxy * frontend:80
}
```

## Sizing OS / hardware

Stack base chạy thoải mái 2 CPU / 4 GB RAM cho một user. Cộng ~1 GB cho mỗi OSS engine sidecar (Kokoro nặng nhất do model weights). Để tăng throughput, chạy nhiều worker replica:

```yaml
# trong docker-compose.override.yml
services:
  worker:
    deploy:
      replicas: 3
```

## Upgrade

```bash
git fetch && git pull --ff-only
docker compose pull
docker compose up -d --build migrate     # đợi healthcheck
docker compose up -d --build api worker frontend
```

Service `migrate` chạy `alembic upgrade head` xong trước khi `api`/`worker` restart (`depends_on.condition: service_completed_successfully`). Migration fail = API không khởi động — sửa migration rồi chạy lại.

Xem [`operations.md`](operations.md) cho backup/restore, monitoring, rollback playbook.
