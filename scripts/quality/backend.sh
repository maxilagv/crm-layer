#!/usr/bin/env sh
set -eu

cd apps/api
ruff check .
ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=crm --cov-report=term-missing
