# Operations

> **For AI agents:** any change to a Makefile target, migration command, or backup script is a public-API change for operators. Don't rename without a redirect/alias.
>
> **For humans:** day-2 playbooks — backup, migrate, monitor, upgrade, troubleshoot.

## TL;DR

- Backups: `make db-backup` runs `pg_dump` and writes to `./backups/<timestamp>.sql.gz`. Restore with `make db-restore f=backups/<file>.sql.gz`.
- Migrations: `make migrate` (local) or `make migrate-docker` (against the running compose). Auto-generate with `make migrate-autogenerate m="..."`.
- Monitoring: `/health`, `/metrics`, `/v1/monitor/status`, `/v1/monitor/logs`. The frontend has a Monitor page that wraps the last two.
- Versioning: `make bump-{patch,minor,major}` updates `backend/VERSION` and tags. CI release workflow takes over from there.

## Backup

```bash
make db-backup
# → backups/2025-04-25-180000.sql.gz
```

Implementation: [`scripts/db_backup.sh`](../../scripts/db_backup.sh) shells into the `postgres` Compose service and runs `pg_dump | gzip`. Treat the resulting file as sensitive — it contains encrypted (or, if `APP_ENCRYPTION_KEY` is empty, plaintext) provider credentials.

For production, schedule the script in cron / a systemd timer / your CI runner, and ship the output to off-host storage (S3, B2, Tigris). Sample crontab:

```cron
# every 6 hours, keep the last 28 (~7 days)
0 */6 * * * cd /srv/ntd_audio && make db-backup && find backups/ -name '*.sql.gz' -mtime +7 -delete
```

## Restore

```bash
make db-restore f=backups/2025-04-25-180000.sql.gz
```

Restore drops the existing database and reloads from the dump. **It does not roll back artifact storage or Redis state.** After a restore, expect:

- Any in-flight jobs to be reaped by `JOB_MAX_RUNTIME_SECONDS`.
- Generation cache rows to be valid only if the artifact files are still on disk / in S3.

For a true point-in-time restore, take coordinated snapshots of Postgres + the artifact bucket and restore both.

## Migrations

| Command | What it does | When to use |
|---|---|---|
| `make migrate` | `alembic upgrade head` against your local `.env`. | Local dev. |
| `make migrate-docker` | Same, but inside the running `migrate` Compose service. | Production / staging upgrades. |
| `make migrate-status` | `alembic current` — show the active revision. | Sanity check before deploys. |
| `make migrate-history` | `alembic history --verbose`. | Audit / debugging. |
| `make migrate-down` | Downgrade one revision. | Local rollback tests. |
| `make migrate-revision m="..."` | Empty Alembic revision. | When you want to write the SQL by hand. |
| `make migrate-autogenerate m="..."` | Diff `models.py` against the DB and emit a revision. | Most schema changes. **Always review the generated file before committing.** |
| `make migrate-reset` | `downgrade base && upgrade head`. **Refuses if `APP_ENV=production`.** | Local schema rewinds during development. |

**Discipline rules**

- Edit `backend/src/voiceforge/models.py` first, then auto-generate the revision.
- Review the diff for unintended drops (Alembic's autogenerate is conservative on indexes/constraints — confirm).
- Migrations must be idempotent enough to survive a retry — if a revision half-applied, you should be able to re-run `alembic upgrade head` after fixing the underlying issue.
- Never edit a committed revision. Add a new one that fixes up.

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

Use this for liveness/readiness probes. The endpoint never requires auth.

### `/metrics` (Prometheus)

Mounted when `METRICS_ENABLED=true`. Series exposed:

| Metric | Type | Labels |
|---|---|---|
| `voiceforge_http_requests_total` | counter | `method`, `route`, `status` |
| `voiceforge_http_request_duration_seconds` | histogram | `method`, `route` |
| `voiceforge_jobs_state_transitions_total` | counter | `reason`, `provider_key` |
| `voiceforge_jobs_in_flight` | gauge | — |

The `route` label uses the matched FastAPI route template (e.g. `/v1/jobs/{job_id}`) or `__unmatched__` for 404s — this caps cardinality.

A minimal scrape config:

```yaml
scrape_configs:
  - job_name: ntd_audio
    static_configs:
      - targets: ["api.internal:8000"]
    metrics_path: /metrics
```

Sample alerts:

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

### `/v1/monitor/status` and `/v1/monitor/logs`

JSON shape mirrors the in-app Monitor page. `logs` accepts a `source` query param (`api`, `worker`, plus `voicevox`/`piper`/`kokoro`/`vieneu` when the Docker socket is mounted). In `docker-compose.prod.yml` the socket is masked; engine logs become unavailable by design.

## Upgrades

```bash
git fetch
git diff HEAD..origin/main -- CHANGELOG.md backend/alembic/versions/
git pull --ff-only

docker compose pull
docker compose up -d --build migrate         # waits for healthcheck
docker compose up -d --build api worker frontend
```

The `migrate` service has `depends_on.condition: service_completed_successfully` from `api` and `worker`, so a failed migration prevents the new API/worker from starting against a half-migrated schema.

If you run replicated workers, drain them by setting their replica count to `0` before the migration runs, then scale back up after the new API is healthy.

## Versioning

| Command | Effect |
|---|---|
| `make bump-patch` | `1.0.0` → `1.0.1` |
| `make bump-minor` | `1.0.0` → `1.1.0` |
| `make bump-major` | `1.0.0` → `2.0.0` |

Each bumps `backend/VERSION`, updates `CHANGELOG.md`'s `[Unreleased]` heading to the new version, commits the change, and creates a `vX.Y.Z` tag. Pushing the tag triggers `.github/workflows/release.yml`, which builds and publishes a GitHub Release with the changelog excerpt.

The application reports its version in `/health.version` and in the `X-App-Version` response header on every request.

## Troubleshooting

### Jobs sit in `queued` forever

- Worker not running: `docker compose ps worker` should show `running`. Restart with `docker compose restart worker`.
- Redis unreachable: `docker compose exec redis redis-cli ping` should return `PONG`.
- Dramatiq queue empty unexpectedly: confirm `redis-cli LLEN voiceforge` from inside the redis container.

### Jobs stuck in `running` forever

The reaper marks them `failed` after `JOB_MAX_RUNTIME_SECONDS`. Check `voiceforge_jobs_state_transitions_total{reason="reaped_failed"}` and the API logs for `reaper_reaped` entries.

### `/metrics` exists but `voiceforge_jobs_in_flight` never decrements

This is the multi-process trap: a previous deploy may have recorded events in the worker's REGISTRY. Verify the API container has the metrics subscriber running:

```bash
docker compose logs api | grep metrics_subscriber
```

If you see only `metrics_subscriber_error`, Redis is unreachable and metrics are stalling intentionally. Fix the Redis connection.

### Frontend shows "Service unavailable" on every page

Check `APP_ALLOWED_ORIGINS` includes your frontend origin. CORS misconfiguration is the #1 cause.

### `LocalArtifactStorage: artifact key escapes storage root`

A provider returned a path that resolves outside `ARTIFACT_ROOT`. The storage layer correctly refuses. File a bug — providers are not supposed to control the key.
