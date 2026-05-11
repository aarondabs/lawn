#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

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
TEST_DB_NAME="${TEST_DB_NAME:-${POSTGRES_DB}_test}"

echo "Ensuring test database exists: $TEST_DB_NAME"

exists="$({
  docker exec lawn-db psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$TEST_DB_NAME'";
} | tr -d '[:space:]')"

if [[ "$exists" != "1" ]]; then
  docker exec lawn-db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$TEST_DB_NAME\""
  echo "Created database: $TEST_DB_NAME"
else
  echo "Database already exists: $TEST_DB_NAME"
fi

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "POSTGRES_PASSWORD is required in $ENV_FILE" >&2
  exit 1
fi

TEST_DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${TEST_DB_NAME}"

echo "Running migrations on $TEST_DB_NAME"
docker exec -e DATABASE_URL="$TEST_DATABASE_URL" lawn-api alembic upgrade head

echo "Test DB ready: $TEST_DB_NAME"
