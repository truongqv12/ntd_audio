# Vận hành

> **Dành cho AI agent:** thay đổi target Makefile, lệnh migration, hoặc script backup là thay đổi public API cho người vận hành. Không đổi tên mà không có alias/redirect.
>
> **Dành cho người đọc:** playbook ngày-2 — backup, migrate, monitor, upgrade, troubleshoot.

## TL;DR

- Backup: `make db-backup` chạy `pg_dump` và ghi vào `./backups/<timestamp>.sql.gz`. Restore bằng `make db-restore f=backups/<file>.sql.gz`.
- Migration: `make migrate` (local) hoặc `make migrate-docker` (compose đang chạy). Auto-generate bằng `make migrate-autogenerate m="..."`.
- Monitor: `/health`, `/metrics`, `/v1/monitor/status`, `/v1/monitor/logs`. Frontend có trang Monitor wrap hai endpoint cuối.
- Versioning: `make bump-{patch,minor,major}` cập nhật `backend/VERSION` và tag. CI release workflow tiếp quản từ đó.

## Backup

```bash
make db-backup
# → backups/2025-04-25-180000.sql.gz
```

Implementation: [`scripts/db_backup.sh`](../../scripts/db_backup.sh) shell vào service `postgres` và chạy `pg_dump | gzip`. File output là **dữ liệu nhạy cảm** — chứa secret provider (đã encrypt nếu `APP_ENCRYPTION_KEY` set, ngược lại plaintext).

Production: lên lịch script trong cron / systemd timer / CI runner và đẩy output lên storage off-host (S3, B2, Tigris). Ví dụ crontab:

```cron
# mỗi 6 giờ, giữ 28 file gần nhất (~7 ngày)
0 */6 * * * cd /srv/ntd_audio && make db-backup && find backups/ -name '*.sql.gz' -mtime +7 -delete
```

## Restore

```bash
make db-restore f=backups/2025-04-25-180000.sql.gz
```

Restore drop database hiện tại và reload từ dump. **Không** rollback artifact storage hoặc state Redis. Sau restore, lưu ý:

- Các job đang chạy sẽ bị reaper đánh dấu fail sau `JOB_MAX_RUNTIME_SECONDS`.
- Generation cache row chỉ valid nếu file artifact vẫn còn trên đĩa / S3.

Để restore point-in-time đúng nghĩa, snapshot phối hợp Postgres + bucket artifact và restore cả hai.

## Migration

| Lệnh | Tác dụng | Khi nào dùng |
|---|---|---|
| `make migrate` | `alembic upgrade head` theo `.env` local. | Local dev. |
| `make migrate-docker` | Như trên nhưng bên trong service `migrate` của Compose. | Upgrade production / staging. |
| `make migrate-status` | `alembic current` — revision hiện tại. | Check trước khi deploy. |
| `make migrate-history` | `alembic history --verbose`. | Audit / debug. |
| `make migrate-down` | Downgrade một revision. | Test rollback local. |
| `make migrate-revision m="..."` | Tạo revision rỗng. | Khi muốn tự viết SQL. |
| `make migrate-autogenerate m="..."` | Diff `models.py` với DB và sinh revision. | Đa số schema change. **Luôn review file sinh ra trước khi commit.** |
| `make migrate-reset` | `downgrade base && upgrade head`. **Từ chối nếu `APP_ENV=production`.** | Reset schema khi dev. |

**Quy tắc kỷ luật**

- Sửa `backend/src/voiceforge/models.py` trước, rồi auto-generate.
- Review diff để tìm drop ngoài ý muốn (autogenerate hơi conservative ở index/constraint — kiểm tra kỹ).
- Migration phải idempotent đủ để chịu retry — nếu apply giữa chừng fail, sau khi sửa phải chạy lại `alembic upgrade head` được.
- Không bao giờ sửa revision đã commit. Thêm revision mới để fix.

## Monitoring

### `/health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "app_env": "production",
  "alembic_revision": "f240e4d",
  "providers": [
    {"key": "voicevox", "reachable": true, "latency_ms": 14, "voices": 24},
    {"key": "openai",   "reachable": true, "latency_ms": 220, "voices": 11}
  ]
}
```

Dùng cho liveness/readiness probe. Endpoint không yêu cầu auth.

### `/metrics` (Prometheus)

Mount khi `METRICS_ENABLED=true`. Series expose:

| Metric | Loại | Label |
|---|---|---|
| `voiceforge_http_requests_total` | counter | `method`, `route`, `status` |
| `voiceforge_http_request_duration_seconds` | histogram | `method`, `route` |
| `voiceforge_jobs_state_transitions_total` | counter | `reason`, `provider_key` |
| `voiceforge_jobs_in_flight` | gauge | — |

Label `route` dùng template route khớp (vd `/v1/jobs/{job_id}`) hoặc `__unmatched__` cho 404 — chống cardinality DoS.

Scrape config tối thiểu:

```yaml
scrape_configs:
  - job_name: ntd_audio
    static_configs:
      - targets: ["api.internal:8000"]
    metrics_path: /metrics
```

Alert mẫu:

```yaml
- alert: NtdAudioJobsBacklog
  expr: voiceforge_jobs_in_flight > 50
  for: 10m
- alert: NtdAudioJobsFailureRateHigh
  expr: rate(voiceforge_jobs_state_transitions_total{reason="failed"}[5m]) > 0.1
  for: 10m
- alert: NtdAudioApiDown
  expr: up{job="ntd_audio"} == 0
  for: 2m
```

### `/v1/monitor/status` và `/v1/monitor/logs`

JSON shape khớp trang Monitor trong app. `logs` nhận query `source` (`api`, `worker`, kèm `voicevox`/`piper`/`kokoro`/`vieneu` khi mount Docker socket). Trong `docker-compose.prod.yml` socket bị mask; engine log không khả dụng theo thiết kế.

## Upgrade

```bash
git fetch
git diff HEAD..origin/main -- CHANGELOG.md backend/alembic/versions/
git pull --ff-only

docker compose pull
docker compose up -d --build migrate         # đợi healthcheck
docker compose up -d --build api worker frontend
```

Service `migrate` có `depends_on.condition: service_completed_successfully` từ `api` và `worker`, nên migration fail sẽ chặn API/worker mới khởi động trên schema lỡ migrate.

Nếu chạy nhiều worker replica, drain bằng cách giảm replica về `0` trước khi migrate, scale lên lại sau khi API mới healthy.

## Versioning

| Lệnh | Tác dụng |
|---|---|
| `make bump-patch` | `1.0.0` → `1.0.1` |
| `make bump-minor` | `1.0.0` → `1.1.0` |
| `make bump-major` | `1.0.0` → `2.0.0` |

Mỗi lệnh bump `backend/VERSION`, đổi heading `[Unreleased]` của `CHANGELOG.md` thành version mới, commit, và tạo tag `vX.Y.Z`. Push tag chạy `.github/workflows/release.yml`, build và publish GitHub Release với trích đoạn changelog.

App report version trong `/health.version` và header `X-App-Version` của mọi response.

## Troubleshooting

### Job mãi ở `queued`

- Worker không chạy: `docker compose ps worker` phải `running`. Restart: `docker compose restart worker`.
- Redis không reachable: `docker compose exec redis redis-cli ping` phải trả `PONG`.
- Queue Dramatiq trống bất thường: trong container redis chạy `redis-cli LLEN voiceforge`.

### Job mãi ở `running`

Reaper đánh dấu fail sau `JOB_MAX_RUNTIME_SECONDS`. Check `voiceforge_jobs_state_transitions_total{reason="reaped_failed"}` và log API có entry `reaper_reaped`.

### `/metrics` có nhưng `voiceforge_jobs_in_flight` không giảm

Bẫy multi-process: deploy trước có thể đã record ở REGISTRY của worker. Verify subscriber metric trên API container:

```bash
docker compose logs api | grep metrics_subscriber
```

Nếu chỉ thấy `metrics_subscriber_error`, Redis không reachable và metric đang đứng yên có chủ đích. Sửa kết nối Redis.

### Frontend báo "Service unavailable" mọi page

Check `APP_ALLOWED_ORIGINS` có origin frontend. Lỗi CORS là nguyên nhân #1.

### `LocalArtifactStorage: artifact key escapes storage root`

Provider trả path resolve ra ngoài `ARTIFACT_ROOT`. Storage layer từ chối đúng. Mở bug — provider không được phép kiểm soát key.
