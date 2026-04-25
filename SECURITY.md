# Security policy

## Reporting a vulnerability

> **Do not open a public GitHub issue for security reports.**

Please email **truongqv13@gmail.com** with:

- A description of the vulnerability.
- Steps to reproduce, including version/commit if possible.
- The impact you observed or expect.
- Your contact information for follow-up.

A maintainer will acknowledge receipt within **5 business days** and aim to provide a remediation plan within **30 days** for valid reports. Coordinated disclosure is preferred — please do not publish details until a fix has been released.

## Scope

In-scope:

- The `backend/` FastAPI service and its handlers.
- The Dramatiq worker (`backend/src/voiceforge/tasks.py`).
- The `frontend/` React app.
- Default `docker-compose*.yml` configurations shipped from the repo.
- Migration scripts under `backend/alembic/`.

Out of scope:

- Third-party TTS provider services (OpenAI, ElevenLabs, Google Cloud TTS, Azure Speech, etc.). Report those upstream.
- The bundled OSS engine images (`voicevox`, `piper`, `kokoro`, `vieneu`). Report those upstream as well.
- Vulnerabilities that require a malicious admin already authenticated as `APP_API_KEYS` holder, except for privilege escalation across workspaces.
- DoS via legitimate but expensive synthesis requests; rate limiting (`RATE_LIMIT_PER_MINUTE`) is the operator's responsibility.

## Hardening expectations for self-host operators

The defaults in `docker-compose.yml` are **for local development**. Before exposing an instance to the public internet:

1. Apply `docker-compose.prod.yml` — drops Postgres/Redis host port bindings and removes the Docker socket mount.
2. Set `APP_API_KEYS` to a non-empty CSV. Without it, all routes except `/health` are open.
3. Set `APP_ENCRYPTION_KEY` (Fernet 32-byte URL-safe base64). Provider secrets in the database are stored plaintext otherwise.
4. Set `APP_ALLOWED_ORIGINS` to the actual frontend origin(s). The default empty list disables wildcard CORS.
5. Set `RATE_LIMIT_PER_MINUTE` to a sensible bound for your provider quota.
6. Enable HTTPS at the reverse proxy. The bundled nginx config in `frontend/nginx.conf` is a starting point, not a hardened production config — terminate TLS in front of it.
7. Restrict access to `/metrics` (when `METRICS_ENABLED=true`) at the proxy layer. The endpoint is unauthenticated by design so Prometheus can scrape it.

See [`docs/en/self-hosting.md`](docs/en/self-hosting.md) for the full production checklist.

## Supported versions

Only `main` is supported. Tagged releases get backports for security issues only when the report lands within the same minor version.
