# Self-hosting

> **For AI agents:** changing defaults here can lock real users out of their data. Treat each env var as part of a public contract. New variables must default to off / safe and must be documented in `.env.example` in the same PR.
>
> **For humans:** how to run `ntd_audio` on your own infrastructure, from "laptop" to "exposed to the internet."

## TL;DR

- Local dev: `cp .env.example .env && docker compose up --build`. That's it.
- Public-facing: layer `docker-compose.prod.yml` and set `APP_API_KEYS`, `APP_ENCRYPTION_KEY`, `APP_ALLOWED_ORIGINS`, `RATE_LIMIT_PER_MINUTE`. Terminate TLS at your reverse proxy.
- Engines are opt-in via Compose overlays. The base stack runs without any of them — useful when you only need cloud providers.

## Compose stacks

| File | Purpose |
|---|---|
| `docker-compose.yml` | Base: postgres, redis, migrate, api, worker, frontend |
| `docker-compose.prod.yml` | Production hardening (apply on top of base) |
| `docker-compose.oss.yml` | All four OSS engines |
| `docker-compose.voicevox.yml` (in base) | VOICEVOX CPU image |
| `docker-compose.gpu.yml` | VOICEVOX GPU image (replaces CPU) |
| `docker-compose.piper.yml` | Piper runtime sidecar |
| `docker-compose.kokoro.yml` | Kokoro runtime sidecar |
| `docker-compose.vieneu.yml` | VieNeu-TTS runtime sidecar |

Compose merges the files left-to-right. Lists (`ports`, `volumes`, `command`) **append** by default; the prod overlay uses `!reset []` (Compose v2.24+) to actually drop entries.

## Environment variables

The committed `.env.example` is the schema. Every variable below has a default unless marked **required**.

### Core

| Var | Default | What it does |
|---|---|---|
| `APP_ENV` | `development` | Gates `db.init_db()`. In `production`, only Alembic owns the schema. |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Where the API listens inside its container. |
| `APP_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:4173` | CSV of CORS origins. Empty = no CORS allowed (recommended for production behind a same-origin proxy). |
| `APP_API_KEYS` | empty | CSV of API keys. Empty disables auth (open access — fine for single-user local). |
| `APP_ENCRYPTION_KEY` | empty | Fernet key for encrypting provider secrets in `app_settings`. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `DATABASE_URL` | bundled postgres | SQLAlchemy URL. The default points at the Compose `postgres` service. |
| `REDIS_URL` | bundled redis | Dramatiq + pub/sub. |
| `LOG_LEVEL` | `INFO` | Backend log verbosity. |
| `LOG_FILE_PATH` | `/data/logs/voiceforge.log` | Rotating file log path. |

### Storage

| Var | Default | What it does |
|---|---|---|
| `ARTIFACT_ROOT` | `/data/artifacts` | Where audio artifacts land for the local backend. |
| `CACHE_ROOT` | `/data/cache` | Generation cache directory. |
| `STORAGE_BACKEND` | `local` | `local` or `s3`. |
| `S3_BUCKET` | empty | Required when `STORAGE_BACKEND=s3`. |
| `S3_REGION` | empty | AWS region or MinIO region (e.g. `us-east-1`). |
| `S3_ENDPOINT_URL` | empty | Set for MinIO / R2 / non-AWS endpoints. |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | empty | Credentials. Prefer IAM roles in AWS-native deployments. |
| `S3_PREFIX` | empty | Optional prefix appended to every object key. |

### Reliability

| Var | Default | What it does |
|---|---|---|
| `JOB_MAX_RUNTIME_SECONDS` | `900` | After this, the reaper marks a stuck job `failed`. |
| `JOB_REAPER_INTERVAL_SECONDS` | `60` | How often the reaper runs. |
| `JOB_REAPER_ENABLED` | `true` | Disable only for local debugging. |
| `RATE_LIMIT_PER_MINUTE` | `120` | Per-client token bucket. `0` disables. |

### Observability

| Var | Default | What it does |
|---|---|---|
| `METRICS_ENABLED` | `true` | Mounts `/metrics` and starts the Redis subscriber that records job transitions. |
| `EVENT_STREAM_HEARTBEAT_SECONDS` | `15` | SSE heartbeat cadence. |

### Catalog refresh

| Var | Default | What it does |
|---|---|---|
| `VOICE_CATALOG_REFRESH_ON_START` | `true` | Refresh voice catalog at API startup (in the background). |
| `VOICE_CATALOG_REFRESH_TIMEOUT_SECONDS` | `8` | Per-provider timeout so a slow provider can't block startup. |

### Provider env vars

See [`providers.md`](providers.md). Each engine has its own block. Empty values keep the engine disabled.

## Production overlay

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

What it changes:

- `restart: unless-stopped` on all long-lived services.
- Resource limits via `deploy.resources.limits` (Postgres 1g, Redis 256m, API 1g — adjust to your hardware).
- Structured JSON logs.
- **Postgres and Redis host port bindings removed** (`ports: !reset []`). Internal Compose networking still works.
- **Docker socket mount removed** from the API container by masking `/var/run/docker.sock` with `/dev/null`. The Monitor page's engine log tail will not work in production — that's the intended trade-off.

## Production checklist

```
[ ] APP_API_KEYS is a CSV of strong random keys (≥ 32 bytes each).
[ ] APP_ENCRYPTION_KEY is set (a Fernet key).
[ ] APP_ALLOWED_ORIGINS lists your frontend origin(s) only.
[ ] RATE_LIMIT_PER_MINUTE is set to your provider quota / users.
[ ] STORAGE_BACKEND=s3 if you want artifacts off the host disk.
[ ] METRICS_ENABLED=true and /metrics is restricted to your Prometheus scraper at the proxy layer.
[ ] HTTPS terminates at your reverse proxy. nginx config in frontend/nginx.conf is a starting point — add TLS, HSTS, CSP at the edge.
[ ] docker-compose.prod.yml is layered on top of the base.
[ ] You have a tested db_backup.sh schedule (cron / systemd timer / managed Postgres snapshot).
[ ] You've upgrade-tested the migration path on a staging copy of production data.
```

## Reverse proxy

The bundled `frontend/nginx.conf` (used by `Dockerfile.prod`) handles SPA fallback, gzip, and static asset caching. It does **not** terminate TLS. Put your TLS proxy (Caddy, Traefik, AWS ALB, Cloudflare) in front and forward to nginx on port 80.

A minimal Caddy block:

```caddy
voiceforge.example.com {
  reverse_proxy /api/*  api:8000
  reverse_proxy /v1/*   api:8000
  reverse_proxy /health api:8000
  reverse_proxy /metrics api:8000  # restrict by source IP if exposing
  reverse_proxy /events/* api:8000
  reverse_proxy * frontend:80
}
```

## OS / hardware sizing

The base stack runs comfortably on 2 CPU / 4 GB RAM for a single user. Add ~1 GB per active OSS engine sidecar (Kokoro is the heaviest because of model weights). For sustained throughput, run multiple worker replicas:

```yaml
# in docker-compose.override.yml
services:
  worker:
    deploy:
      replicas: 3
```

## Upgrades

```bash
git fetch && git pull --ff-only
docker compose pull
docker compose up -d --build migrate     # waits for healthcheck
docker compose up -d --build api worker frontend
```

The `migrate` service runs `alembic upgrade head` to completion before `api`/`worker` restart (`depends_on.condition: service_completed_successfully`). If migration fails, the API does not restart — fix the migration and re-run before users see a degraded service.

See [`operations.md`](operations.md) for backup/restore, monitoring, and rollback playbooks.
