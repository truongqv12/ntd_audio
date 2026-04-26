# Development

> **For AI agents:** keep changes scoped. Run lint + typecheck + tests for **both** stacks before opening a PR. The Makefile is the source of truth for commands; don't invent your own.
>
> **For humans:** local setup, the commands you'll use every day, and how the test suite is organized.

## TL;DR

- One-shot setup: `make install-dev` (creates the backend venv, installs frontend deps, installs pre-commit hooks).
- Run locally without Docker: `make backend` (terminal 1), `make worker` (terminal 2), `make frontend` (terminal 3).
- Quality gate: `make lint typecheck test`.
- The full Make target list: `make help`.

## Local setup (without Docker)

```bash
git clone https://github.com/truongqv12/ntd_audio
cd ntd_audio
cp .env.example .env

# Bring up Postgres + Redis only (no API/worker)
docker compose up -d postgres redis migrate

# Install dev deps
make install-dev

# Run the three processes
make backend    # terminal 1: uvicorn + reload
make worker     # terminal 2: dramatiq actor
make frontend   # terminal 3: vite dev server
```

`make backend` reads `DATABASE_URL` from your `.env`. Point it at the Compose Postgres (`postgresql+psycopg://postgres:postgres@localhost:5432/voiceforge`) and you're set.

## Local setup (Docker only)

```bash
docker compose up --build
```

Hot-reload still works for the backend if you mount the source with a `docker-compose.override.yml`:

```yaml
services:
  api:
    command: ["uvicorn", "voiceforge.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    volumes:
      - ./backend/src:/app/src
```

## Makefile targets you'll use

```bash
make help                   # list all
# Local dev
make backend
make worker
make frontend
# Docker
make docker-up
make docker-up-oss
make docker-up-gpu
# Migrations
make migrate
make migrate-status
make migrate-history
make migrate-autogenerate m="add foo column to jobs"
make migrate-revision m="manual SQL change"
make migrate-down
make migrate-reset          # dev only
make migrate-docker         # against running compose
# Backups
make db-backup
make db-restore f=backups/2025-04-25.sql.gz
# Quality
make install-dev
make lint
make format
make typecheck
make test
# Releases
make bump-patch | bump-minor | bump-major
make changelog
```

## Quality gate

CI runs the same commands; passing locally is the prerequisite for opening a PR.

```bash
# backend
cd backend
ruff check src tests
black --check src tests
mypy src
pytest -q

# frontend
cd ../frontend
npm run lint
npm run typecheck
npm test          # vitest
npm run build     # tsc + vite build
```

`make format` auto-fixes Ruff + Black + Prettier formatting. `make lint` is read-only.

## Pre-commit hooks

Installed by `make install-dev`. Hooks: ruff, black, prettier, eslint. They run on staged files. To bypass once (do not commit broken code, but useful when fixing the hook itself):

```bash
SKIP=ruff,black,prettier,eslint git commit -m "..."
```

## Project layout

```
ntd_audio/
├── backend/
│   ├── alembic/                    # migrations
│   ├── src/voiceforge/             # application
│   ├── tests/                      # pytest
│   ├── pyproject.toml              # ruff, black, mypy, deps
│   └── VERSION
├── frontend/
│   ├── src/                        # React + TS
│   │   ├── i18n/                   # en.json + vi.json + provider
│   │   ├── pages/
│   │   ├── components/
│   │   └── styles.css              # design tokens at top
│   ├── nginx.conf                  # used by Dockerfile.prod
│   └── package.json
├── engines/                        # OSS engine sidecar runtimes
│   ├── piper-runtime/
│   ├── kokoro-runtime/
│   └── vieneu-runtime/
├── docs/{en,vi}/                   # this directory
├── scripts/                        # backup, restore, version-bump
├── docker-compose.yml + overlays
├── Makefile
└── .github/workflows/              # ci.yml + release.yml
```

## Tests

### Backend (`backend/tests/`)

`pytest`-based smoke tests for the most-used handlers and services. Each test file uses an isolated SQLite-backed `TestClient` factory; tests are independent.

Add a test when:
- you fix a bug — write a test that fails on `main` and passes on your branch.
- you add an endpoint or change its response shape.
- you add a service function that has multi-step logic (state machines, retries, cache lookups).

### Frontend (`frontend/src/test/`)

`vitest` + `@testing-library/react`. Uses jsdom. The setup file mocks `EventSource` for SSE-aware components.

Add a test when:
- you add a component that has stateful behavior (input, mutation, error states).
- you change a hook used by more than one component.

### What we don't test

- End-to-end (browser-driving). Out of scope for now; see [`feature-map.md`](feature-map.md).
- Engine sidecars. They're owned by upstream projects.

## CI

`.github/workflows/ci.yml` runs on every PR:

```
backend lint  → backend typecheck  → backend tests   ─┐
                                                       ├→ green
frontend lint → frontend typecheck → frontend tests  ─┘
```

`.github/workflows/release.yml` runs on tag push (`vX.Y.Z`):

```
checkout → build wheel + bundle → publish GitHub Release with CHANGELOG excerpt
```

## Debugging tips

- **API not reloading:** kill stale uvicorn workers (`pkill -f voiceforge.main`).
- **Worker not picking up jobs:** confirm Redis is reachable and the queue name matches (`voiceforge`).
- **Mypy complaining about a third-party import:** check `[tool.mypy.overrides]` in `backend/pyproject.toml`. Add an entry rather than `# type: ignore` at the call site.
- **Vitest hangs on SSE-using component:** make sure your test mocks `EventSource` via the existing setup file.
- **Compose merge confusion:** `docker compose -f a.yml -f b.yml config` shows the resolved config. Always check before deploying.
