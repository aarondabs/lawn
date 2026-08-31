#!/usr/bin/env sh
# test.sh — run the API test suite against lawn_test, then the web component tests.
#
# Starts the DB if not already running, then runs pytest inside a
# source-mounted container (no image rebuild needed after code changes).
# Web tests (vitest) run in the source-mounted web container; deps must be
# installed (docker compose run --rm --no-deps web npm install) after any
# package.json change.
#
# First-time setup: run ops/init-test-db.sh once to create lawn_test and
# apply migrations. Re-run it any time the schema changes.
#
# Usage:
#   ./ops/test.sh              # run API + web tests
#   ./ops/test.sh -k reminder  # run API tests matching a keyword (skips web)
#   ./ops/test.sh -v           # verbose output (skips web)
#   ./ops/test.sh -x           # stop on first failure (skips web)
#   ./ops/test.sh api|web      # run only that half
set -eu

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.dev.yml"

cd "$(dirname "$0")/.."

RUN_API=1
RUN_WEB=1
if [ "${1:-}" = "api" ]; then RUN_WEB=0; shift; fi
if [ "${1:-}" = "web" ]; then RUN_API=0; shift; fi
# Extra pytest args imply a focused API run.
if [ "$#" -gt 0 ]; then RUN_WEB=0; fi

if [ "$RUN_API" = "1" ]; then
  echo "==> Ensuring DB is running..."
  $COMPOSE up -d db

  echo ""
  echo "==> Running API tests..."
  $COMPOSE run --rm api-test python -m pytest -q "$@"
fi

if [ "$RUN_WEB" = "1" ]; then
  echo ""
  echo "==> Running web tests..."
  $COMPOSE run --rm --no-deps web sh -c "npm run test"
fi
