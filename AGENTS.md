# AGENTS.md

> **For AI agents:** This is the canonical entry point when working in `ntd_audio`. Read this **before** touching code. It defines invariants, common pitfalls, and the expected workflow. Project-specific knowledge lives under `docs/en/` (and mirrored in `docs/vi/`).

> **For humans:** This file is written for AI coding assistants (Claude Code, Cursor, Devin, etc.). It's a stricter superset of typical contributor guidelines. Humans should read [`CONTRIBUTING.md`](CONTRIBUTING.md) instead.

## TL;DR

- `ntd_audio` is a **self-host-first** TTS orchestration platform. Treat that as a hard constraint when proposing changes.
- The repo has **two top-level stacks**: `backend/` (FastAPI + SQLAlchemy + Dramatiq) and `frontend/` (React + Vite + TS). They share `docker-compose.yml` and `Makefile`.
- **PostgreSQL is the source of truth.** Migrations are owned by Alembic. `db.init_db()` only runs `create_all` in `development`/`test`.
- **Never push to `main`.** Open a PR from `devin/<timestamp>-<topic>`.
- The repo has lint/typecheck/test gates in CI. Get them green locally **before** opening the PR.

## Read these in order

1. [`docs/en/architecture.md`](docs/en/architecture.md) — system topology, where the API/worker/engines fit, sequence diagrams.
2. [`docs/en/development.md`](docs/en/development.md) — local setup, lint/test commands, Makefile targets.
3. [`docs/en/api.md`](docs/en/api.md) — versioning (`/v1`), auth, rate-limit, SSE, metrics.
4. [`docs/en/database.md`](docs/en/database.md) — schema, ERD, migration discipline.
5. [`docs/en/feature-map.md`](docs/en/feature-map.md) — what exists, what's planned.

## Hard rules

### 1. Think before coding

- State assumptions explicitly. If the task is ambiguous, name the ambiguity and ask one question.
- If multiple interpretations exist, present them — do not pick silently.
- If a simpler approach exists, push back. Bias toward minimum viable change.

### 2. Surgical changes only

- Touch only what the task requires.
- Do not "improve" adjacent code, comments, or formatting.
- Match the surrounding style even if it's not what you'd write.
- If you remove an import/var/function, make sure it's because **your** change orphaned it — not because it was already dead.

### 3. Verify, don't assume

Every change must trace to one of: a passing test, a `--dry-run`/`config` check, or a manual reproduction. The acceptable evidence is in [`docs/en/development.md`](docs/en/development.md). Common ones:

- **Backend behavior:** `cd backend && pytest -q` (and add a test if the change is observable).
- **Backend types:** `cd backend && mypy src`.
- **Backend lint:** `cd backend && ruff check src tests && black --check src tests`.
- **Frontend:** `cd frontend && npm run lint && npm run typecheck && npm test`.
- **Compose merges:** `docker compose -f docker-compose.yml -f docker-compose.<x>.yml config`.
- **App boots:** `PYTHONPATH=backend/src python -c "from voiceforge.main import app"`.

### 4. Migration discipline

- Schema changes go through **Alembic only**. Never edit `models.py` and rely on `create_all` to catch up.
- Generate revisions with `make migrate-autogenerate m="<message>"`, review the diff, then commit.
- Never `alembic stamp`/`alembic downgrade` against a deployed database without coordinating with the maintainer.

### 5. Secrets discipline

- Never commit `.env`. The committed `.env.example` is the schema.
- Provider credentials in the `app_settings` table are encrypted at rest when `APP_ENCRYPTION_KEY` is set. Treat them as sensitive even when reading.
- API keys in `APP_API_KEYS` (CSV) gate everything except `/health`. The frontend reads `VITE_API_KEY`.

### 6. Process boundaries matter

The API and the Dramatiq worker are **separate processes**. They share Postgres + Redis but **not** in-memory state. Concretely:

- Prometheus `REGISTRY` is per-process. Cross-process counters must flow via Redis (see `_metrics_subscriber` in `main.py`).
- Rate-limit buckets, log handlers, and any module-level cache do **not** carry between API and worker.
- A change that "works" in the API may silently break the worker (or vice versa). Run both when in doubt: `docker compose up api worker`.

## PR workflow

1. Branch off `main`: `git checkout -b devin/$(date +%s)-<topic>`.
2. Make focused commits with imperative subjects (`fix(scope): summary`).
3. Run lint/typecheck/test for both stacks.
4. Push, open PR. Set the description from `.github/PULL_REQUEST_TEMPLATE.md` (or the existing template). Do not include private sessions/credentials.
5. Wait for CI. Address review comments **in their own threads**.

## When in doubt

- Open the actual code path. Do not infer behavior from filenames or doc claims.
- Cross-reference [`CHANGELOG.md`](CHANGELOG.md) — the most recent entries describe live behavior; older docs may lag.
- Ask in the PR or session before committing a fix you're not sure about.

## See also

- [`CLAUDE.md`](CLAUDE.md) — short alias of this file for tools that look for it by name.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — human-facing version of the workflow.
- [`SECURITY.md`](SECURITY.md) — how to report a vulnerability.
