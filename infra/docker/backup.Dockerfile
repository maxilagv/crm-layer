FROM alpine:3.20.3

RUN apk add --no-cache aws-cli bash findutils gzip postgresql16-client

WORKDIR /scripts
COPY infra/backups/postgres-backup.sh /scripts/postgres-backup.sh
COPY infra/backups/postgres-restore.sh /scripts/postgres-restore.sh

RUN addgroup -S backup \
  && adduser -S -G backup backup \
  && mkdir -p /backups \
  && chmod +x /scripts/postgres-backup.sh /scripts/postgres-restore.sh \
  && chown -R backup:backup /backups /scripts

USER backup
