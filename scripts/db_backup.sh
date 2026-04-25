#!/usr/bin/env bash
# Dump the compose Postgres DB to ./backups/voiceforge_<timestamp>.sql.gz
# Reads target DB/user from compose env (defaults to voiceforge/postgres).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p backups
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="backups/voiceforge_${STAMP}.sql.gz"

DB_NAME="${POSTGRES_DB:-voiceforge}"
DB_USER="${POSTGRES_USER:-postgres}"

echo "Dumping ${DB_NAME} as ${DB_USER} to ${OUT}..."
docker compose exec -T postgres pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${OUT}"

SIZE="$(du -h "${OUT}" | cut -f1)"
echo "Backup written: ${OUT} (${SIZE})"
