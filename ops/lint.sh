#!/usr/bin/env sh
# lint.sh — lint + typecheck both halves of the app inside their containers.
#
# Runs against source-mounted containers, so it checks your working tree with no image rebuild.
# ruff config lives in api/pyproject.toml; eslint config in web/eslint.config.mjs.
#
# Usage:
#   ./ops/lint.sh          # check API (ruff) + web (eslint + tsc); non-zero exit on any problem
#   ./ops/lint.sh --fix    # additionally apply ruff/eslint autofixes to the working tree
#   ./ops/lint.sh api      # API only
#   ./ops/lint.sh web      # web only
set -eu

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
cd "$(dirname "$0")/.."

FIX=""
TARGET="all"
for arg in "$@"; do
  case "$arg" in
    --fix) FIX="1" ;;
    api|web) TARGET="$arg" ;;
    *) echo "unknown arg: $arg" >&2; exit 64 ;;
  esac
done

rc=0

if [ "$TARGET" = "all" ] || [ "$TARGET" = "api" ]; then
  echo "==> API: ruff"
  if [ -n "$FIX" ]; then
    $COMPOSE run --rm --no-deps api-test ruff check --fix . || rc=1
    $COMPOSE run --rm --no-deps api-test ruff format . || rc=1
  else
    $COMPOSE run --rm --no-deps api-test ruff check . || rc=1
  fi
fi

if [ "$TARGET" = "all" ] || [ "$TARGET" = "web" ]; then
  echo "==> web: eslint"
  if [ -n "$FIX" ]; then
    $COMPOSE run --rm --no-deps web sh -c "npx eslint . --fix" || rc=1
  else
    $COMPOSE run --rm --no-deps web sh -c "npx eslint ." || rc=1
  fi
  echo "==> web: tsc --noEmit"
  $COMPOSE run --rm --no-deps web sh -c "npx tsc --noEmit" || rc=1
fi

[ "$rc" -eq 0 ] && echo "All checks passed." || echo "Lint/typecheck found problems."
exit "$rc"
