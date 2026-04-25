#!/usr/bin/env bash
# Restore a Postgres dump (.sql or .sql.gz) into the compose DB.
# Usage: ./scripts/db_restore.sh backups/voiceforge_20260424_010000.sql.gz
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path-to-dump.sql[.gz]>" >&2
  exit 1
fi

DUMP_FILE="$1"

if [ ! -f "${DUMP_FILE}" ]; then
  echo "Dump file not found: ${DUMP_FILE}" >&2
  exit 1
fi

DB_NAME="${POSTGRES_DB:-voiceforge}"
DB_USER="${POSTGRES_USER:-postgres}"

echo "Restoring ${DUMP_FILE} into ${DB_NAME} as ${DB_USER}..."

if [[ "${DUMP_FILE}" == *.gz ]]; then
  gunzip -c "${DUMP_FILE}" | docker compose exec -T postgres psql -U "${DB_USER}" -d "${DB_NAME}"
else
  docker compose exec -T postgres psql -U "${DB_USER}" -d "${DB_NAME}" < "${DUMP_FILE}"
fi

echo "Restore complete."
