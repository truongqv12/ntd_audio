# Phát triển

> **Dành cho AI agent:** giữ scope thay đổi nhỏ. Chạy lint + typecheck + test cho **cả hai** stack trước khi mở PR. Makefile là source of truth cho lệnh; không tự bịa.
>
> **Dành cho người đọc:** setup local, lệnh dùng hằng ngày, và tổ chức bộ test.

## TL;DR

- Setup một lần: `make install-dev` (tạo venv backend, install dep frontend, install pre-commit hook).
- Chạy local không Docker: `make backend` (terminal 1), `make worker` (terminal 2), `make frontend` (terminal 3).
- Quality gate: `make lint typecheck test`.
- Danh sách Make target đầy đủ: `make help`.

## Setup local (không Docker)

```bash
git clone https://github.com/truongqv12/ntd_audio
cd ntd_audio
cp .env.example .env

# Bật chỉ Postgres + Redis (không API/worker)
docker compose up -d postgres redis migrate

# Install dev dep
make install-dev

# Chạy ba process
make backend    # terminal 1: uvicorn + reload
make worker     # terminal 2: dramatiq actor
make frontend   # terminal 3: vite dev server
```

`make backend` đọc `DATABASE_URL` từ `.env`. Trỏ về Postgres của Compose (`postgresql+psycopg://postgres:postgres@localhost:5432/voiceforge`) là chạy được.

## Setup local (chỉ Docker)

```bash
docker compose up --build
```

Hot reload backend vẫn được nếu mount source qua `docker-compose.override.yml`:

```yaml
services:
  api:
    command: ["uvicorn", "voiceforge.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    volumes:
      - ./backend/src:/app/src
```

## Make target dùng hằng ngày

```bash
make help                   # list tất cả
# Local dev
make backend
make worker
make frontend
# Docker
make docker-up
make docker-up-oss
make docker-up-gpu
# Migration
make migrate
make migrate-status
make migrate-history
make migrate-autogenerate m="add foo column to jobs"
make migrate-revision m="manual SQL change"
make migrate-down
make migrate-reset          # chỉ dev
make migrate-docker         # với compose đang chạy
# Backup
make db-backup
make db-restore f=backups/2025-04-25.sql.gz
# Quality
make install-dev
make lint
make format
make typecheck
make test
# Release
make bump-patch | bump-minor | bump-major
make changelog
```

## Quality gate

CI chạy đúng các lệnh này; pass local là tiền đề mở PR.

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

`make format` auto-fix Ruff + Black + Prettier. `make lint` chỉ đọc.

## Pre-commit hook

Cài bởi `make install-dev`. Hook: ruff, black, prettier, eslint. Chạy trên file đã staged. Bypass một lần (không nên commit code lỗi, chỉ tiện khi sửa hook):

```bash
SKIP=ruff,black,prettier,eslint git commit -m "..."
```

## Layout project

```
ntd_audio/
├── backend/
│   ├── alembic/                    # migration
│   ├── src/voiceforge/             # application
│   ├── tests/                      # pytest
│   ├── pyproject.toml              # ruff, black, mypy, deps
│   └── VERSION
├── frontend/
│   ├── src/                        # React + TS
│   │   ├── i18n/                   # en.json + vi.json + provider
│   │   ├── pages/
│   │   ├── components/
│   │   └── styles.css              # design tokens ở đầu file
│   ├── nginx.conf                  # dùng bởi Dockerfile.prod
│   └── package.json
├── engines/                        # OSS engine sidecar
│   ├── piper-runtime/
│   ├── kokoro-runtime/
│   └── vieneu-runtime/
├── docs/{en,vi}/                   # thư mục này
├── scripts/                        # backup, restore, version-bump
├── docker-compose.yml + overlay
├── Makefile
└── .github/workflows/              # ci.yml + release.yml
```

## Test

### Backend (`backend/tests/`)

Smoke test `pytest`-based cho handler và service phổ biến nhất. Mỗi file dùng `TestClient` factory cô lập trên SQLite; test độc lập.

Thêm test khi:
- fix bug — viết test fail trên `main` và pass trên branch.
- thêm endpoint hoặc đổi response shape.
- thêm function service có logic nhiều bước (state machine, retry, cache lookup).

### Frontend (`frontend/src/test/`)

`vitest` + `@testing-library/react`. Dùng jsdom. Setup file mock `EventSource` cho component dùng SSE.

Thêm test khi:
- thêm component có hành vi stateful (input, mutation, error).
- đổi hook dùng bởi nhiều component.

### Cái gì không test

- End-to-end (browser-driving). Hiện ngoài scope; xem [`feature-map.md`](feature-map.md).
- Engine sidecar. Thuộc upstream.

## CI

`.github/workflows/ci.yml` chạy mỗi PR:

```
backend lint  → backend typecheck  → backend tests   ─┐
                                                       ├→ green
frontend lint → frontend typecheck → frontend tests  ─┘
```

`.github/workflows/release.yml` chạy khi push tag (`vX.Y.Z`):

```
checkout → build wheel + bundle → publish GitHub Release với CHANGELOG excerpt
```

## Mẹo debug

- **API không reload:** kill uvicorn cũ (`pkill -f voiceforge.main`).
- **Worker không nhận job:** confirm Redis reachable và queue name khớp (`voiceforge`).
- **Mypy phàn nàn về import bên thứ ba:** check `[tool.mypy.overrides]` trong `backend/pyproject.toml`. Thêm entry thay vì `# type: ignore` ở chỗ gọi.
- **Vitest treo trên component dùng SSE:** đảm bảo test mock `EventSource` qua setup file đã có.
- **Confused về Compose merge:** `docker compose -f a.yml -f b.yml config` show config đã resolve. Luôn check trước khi deploy.
