SHELL := /bin/bash

.PHONY: help backend worker frontend docker-up docker-up-gpu docker-up-oss \
        migrate migrate-down migrate-status migrate-history \
        migrate-revision migrate-autogenerate migrate-reset migrate-docker \
        db-backup db-restore version

help:                    ## list available targets
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

# === Local dev ===
backend:                 ## run uvicorn backend with reload
	cd backend && PYTHONPATH=src uvicorn voiceforge.main:app --reload --host 0.0.0.0 --port 8000

worker:                  ## run dramatiq worker
	cd backend && PYTHONPATH=. dramatiq src.voiceforge.tasks

frontend:                ## run vite dev server
	cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port 5173

# === Docker stacks ===
docker-up:               ## docker compose up (default stack)
	docker compose up --build

docker-up-gpu:           ## stack + GPU overlay
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build

docker-up-oss:           ## stack + all OSS engines
	docker compose -f docker-compose.yml -f docker-compose.oss.yml up --build

# === Migrations ===
migrate:                 ## upgrade DB to head (local, against current .env)
	cd backend && PYTHONPATH=. alembic upgrade head

migrate-down:            ## downgrade 1 revision
	cd backend && PYTHONPATH=. alembic downgrade -1

migrate-status:          ## show current alembic revision
	cd backend && PYTHONPATH=. alembic current

migrate-history:         ## list all alembic revisions
	cd backend && PYTHONPATH=. alembic history --verbose

migrate-revision:        ## create empty revision; usage: make migrate-revision m="add foo"
	@if [ -z "$(m)" ]; then echo "Usage: make migrate-revision m=\"message\""; exit 1; fi
	cd backend && PYTHONPATH=. alembic revision -m "$(m)"

migrate-autogenerate:    ## autogenerate revision from models; usage: make migrate-autogenerate m="..."
	@if [ -z "$(m)" ]; then echo "Usage: make migrate-autogenerate m=\"message\""; exit 1; fi
	cd backend && PYTHONPATH=. alembic revision --autogenerate -m "$(m)"

migrate-reset:           ## DEV ONLY: downgrade to base then upgrade head
	@if [ "$(APP_ENV)" = "production" ]; then echo "refusing to reset DB in production"; exit 1; fi
	cd backend && PYTHONPATH=. alembic downgrade base
	cd backend && PYTHONPATH=. alembic upgrade head

migrate-docker:          ## run alembic upgrade head inside running api container
	docker compose run --rm migrate alembic upgrade head

# === Database backup ===
db-backup:               ## pg_dump compose DB to ./backups/<timestamp>.sql.gz
	./scripts/db_backup.sh

db-restore:              ## restore from a backup file; usage: make db-restore f=backups/xxx.sql.gz
	@if [ -z "$(f)" ]; then echo "Usage: make db-restore f=backups/xxx.sql.gz"; exit 1; fi
	./scripts/db_restore.sh $(f)

# === Misc ===
version:                 ## show backend VERSION
	@cat backend/VERSION 2>/dev/null || echo "unknown"
