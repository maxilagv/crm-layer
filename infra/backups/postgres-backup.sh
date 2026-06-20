#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
S3_PREFIX="${BACKUP_S3_PREFIX:-crm-layer/postgres}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

tmp_file="${BACKUP_DIR}/postgres-${timestamp}.sql.gz.tmp"
final_file="${BACKUP_DIR}/postgres-${timestamp}.sql.gz"

pg_dump --no-owner --no-acl "$DATABASE_URL" | gzip -9 > "$tmp_file"
mv "$tmp_file" "$final_file"

find "$BACKUP_DIR" -type f -name "postgres-*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
  export AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID:-${S3_ACCESS_KEY_ID:-${AWS_ACCESS_KEY_ID:-}}}"
  export AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY:-${S3_SECRET_ACCESS_KEY:-${AWS_SECRET_ACCESS_KEY:-}}}"
  export AWS_DEFAULT_REGION="${BACKUP_S3_REGION:-${S3_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}}"
  endpoint_args=()
  if [ -n "${BACKUP_S3_ENDPOINT_URL:-}" ]; then
    endpoint_args=(--endpoint-url "$BACKUP_S3_ENDPOINT_URL")
  elif [ -n "${S3_ENDPOINT_URL:-}" ]; then
    endpoint_args=(--endpoint-url "$S3_ENDPOINT_URL")
  fi
  aws "${endpoint_args[@]}" s3 cp \
    "$final_file" \
    "s3://${BACKUP_S3_BUCKET}/${S3_PREFIX}/$(basename "$final_file")"
fi

echo "backup_created=$final_file"
