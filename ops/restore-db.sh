#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup.sql.gz> [target_db]" >&2
  exit 64
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-}"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 66
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

POSTGRES_DB="${POSTGRES_DB:-lawn}"
POSTGRES_USER="${POSTGRES_USER:-lawn}"
TARGET_DB="${TARGET_DB:-$POSTGRES_DB}"

echo "This will replace all data in database: $TARGET_DB"
echo "Type exactly 'restore-$TARGET_DB' to continue:"
read -r confirm

if [[ "$confirm" != "restore-$TARGET_DB" ]]; then
  echo "Cancelled"
  exit 1
fi

echo "Dropping and recreating schema in $TARGET_DB"
docker exec lawn-db psql -U "$POSTGRES_USER" -d "$TARGET_DB" -v ON_ERROR_STOP=1 \
  -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"

echo "Restoring from $BACKUP_FILE"
gzip -dc "$BACKUP_FILE" | docker exec -i lawn-db psql -U "$POSTGRES_USER" -d "$TARGET_DB" -v ON_ERROR_STOP=1

echo "Restore complete"
