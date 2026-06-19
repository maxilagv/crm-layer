#!/usr/bin/env sh
set -eu

cp -n .env.example .env 2>/dev/null || true
pnpm install
(cd apps/api && python -m pip install -e ".[dev]")
docker compose -f docker-compose.local.yml build
