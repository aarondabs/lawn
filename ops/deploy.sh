#!/usr/bin/env sh
# deploy.sh — rebuild and redeploy the lawn app from current source.
#
# Always rebuilds images so the running containers match the code on disk.
# Only uses docker-compose.yml (production). Never picks up dev overrides.
#
# Usage (from repo root or ops/):
#   ./ops/deploy.sh              # rebuild and redeploy all services
#   ./ops/deploy.sh api          # rebuild and redeploy api only
#   ./ops/deploy.sh web          # rebuild and redeploy web only
#   ./ops/deploy.sh api web      # rebuild and redeploy specific services
#
# Run from the host or from code-server with the host Docker socket.
set -eu

COMPOSE="docker compose -f docker-compose.yml"

cd "$(dirname "$0")/.."

# Warn if docker-compose.override.yml exists — it auto-merges and can silently
# switch services to dev mode. It should not exist in production.
if [ -f docker-compose.override.yml ]; then
  echo "WARNING: docker-compose.override.yml detected."
  echo "  This file auto-merges with any 'docker compose' command and may activate"
  echo "  dev mode (npm run dev, bind mounts). Remove it to prevent surprises:"
  echo "    rm /opt/apps/lawn/docker-compose.override.yml"
  echo ""
fi

if [ "$#" -eq 0 ]; then
  SERVICES=""
else
  SERVICES="$*"
fi

echo "==> Building images..."
# shellcheck disable=SC2086
$COMPOSE build $SERVICES

echo ""
echo "==> Deploying containers..."
# shellcheck disable=SC2086
$COMPOSE up -d $SERVICES

echo ""
echo "==> Running database migrations..."
$COMPOSE exec -T api python -m alembic upgrade head

echo ""
echo "==> Done. Current status:"
$COMPOSE ps
