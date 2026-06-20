#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

if [ "$#" -ne 1 ]; then
  echo "usage: postgres-restore.sh /backups/postgres-YYYYmmddTHHMMSSZ.sql.gz" >&2
  exit 2
fi

backup_file="$1"
if [ ! -f "$backup_file" ]; then
  echo "backup not found: $backup_file" >&2
  exit 2
fi

gunzip -c "$backup_file" | psql --single-transaction "$DATABASE_URL"
echo "restore_completed=$backup_file"
