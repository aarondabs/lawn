#!/usr/bin/env sh
set -eu

# Recreate containers so updated .env values are injected.
# NOTE: This does NOT rebuild images. Use ops/deploy.sh when source code has
# changed — it rebuilds images before restarting so containers always run
# the current code.
#
# Usage:
#   ./ops/reload-env.sh            # recreate api only (fast path)
#   ./ops/reload-env.sh all        # recreate api, web, and db
#   ./ops/reload-env.sh api web    # recreate specific services

BASE_FILES="-f docker-compose.yml"

if [ "$#" -eq 0 ]; then
  SERVICES="api"
elif [ "$1" = "all" ]; then
  SERVICES="api web db"
else
  SERVICES="$*"
fi

cd "$(dirname "$0")/.."

echo "Recreating services: $SERVICES"
# shellcheck disable=SC2086
docker compose $BASE_FILES up -d --force-recreate $SERVICES

echo "Done. Current status:"
# shellcheck disable=SC2086
docker compose $BASE_FILES ps
