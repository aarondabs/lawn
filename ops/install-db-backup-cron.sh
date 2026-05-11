#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_APP_DIR="${HOST_APP_DIR:-/opt/apps/lawn}"
BACKUP_SCRIPT="$HOST_APP_DIR/ops/backup-db.sh"
LOG_DIR="$ROOT_DIR/ops/private/db-backups"
CRON_SCHEDULE="${CRON_SCHEDULE:-30 3 * * *}"
CRON_FILE="${CRON_FILE:-/host/etc/cron.d/lawn-db-backup}"
CRON_USER="${CRON_USER:-dabs}"

mkdir -p "$LOG_DIR"

mkdir -p /host/etc/cron.d

cron_line="$CRON_SCHEDULE $CRON_USER PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin $BACKUP_SCRIPT >> $HOST_APP_DIR/ops/private/db-backups/backup.log 2>&1"

{
  echo "# Managed by ops/install-db-backup-cron.sh"
  echo "$cron_line"
} > "$CRON_FILE"

chmod 0644 "$CRON_FILE"

echo "Installed host cron file: $CRON_FILE"
echo "$cron_line"
