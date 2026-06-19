FROM python:3.12.7-slim-bookworm AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app/apps/api

RUN python -m venv "$VIRTUAL_ENV"

FROM python-base AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml /app/apps/api/pyproject.toml
COPY apps/api/src /app/apps/api/src

RUN pip install --upgrade pip \
  && pip install -e .

FROM python-base AS runtime

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl libpq5 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY apps/api /app/apps/api
COPY infra/docker/api-entrypoint.sh /app/infra/docker/api-entrypoint.sh

RUN addgroup --system --gid 10001 app \
  && adduser --system --uid 10001 --ingroup app app \
  && mkdir -p /app/apps/api/staticfiles /app/apps/api/private_media \
  && chown -R app:app /app /opt/venv

EXPOSE 8000

FROM runtime AS production
USER app

FROM runtime AS development
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/* \
  && pip install -e ".[dev]"
