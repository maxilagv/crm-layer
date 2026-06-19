FROM node:22.11.0-bookworm-slim AS base

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

WORKDIR /app

RUN corepack enable \
  && corepack prepare pnpm@9.15.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY packages ./packages
COPY apps/web/package.json ./apps/web/package.json

RUN pnpm install --frozen-lockfile

FROM base AS production

ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY . .
RUN pnpm --filter @ai-crm/web build \
  && chown -R node:node /app

USER node
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["pnpm", "start"]

FROM base AS development

COPY . .
EXPOSE 3000
