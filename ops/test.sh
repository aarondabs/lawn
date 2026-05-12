#!/usr/bin/env sh
# test.sh — run the API test suite against lawn_test.
#
# Starts the DB if not already running, then runs pytest inside a
# source-mounted container (no image rebuild needed after code changes).
#
# First-time setup: run ops/init-test-db.sh once to create lawn_test and
# apply migrations. Re-run it any time the schema changes.
#
# Usage:
#   ./ops/test.sh              # run all tests
#   ./ops/test.sh -k reminder  # run tests matching a keyword
#   ./ops/test.sh -v           # verbose output
#   ./ops/test.sh -x           # stop on first failure
set -eu

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.dev.yml"

cd "$(dirname "$0")/.."

echo "==> Ensuring DB is running..."
$COMPOSE up -d db

echo ""
echo "==> Running tests..."
$COMPOSE run --rm api-test python -m pytest -q "$@"
