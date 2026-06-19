FROM node:22.11.0-bookworm-slim AS deps

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
ENV PUPPETEER_SKIP_DOWNLOAD=true

WORKDIR /app

RUN corepack enable \
  && corepack prepare pnpm@9.15.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/wa-bridge/package.json ./apps/wa-bridge/package.json

RUN pnpm install --frozen-lockfile --filter @ai-crm/wa-bridge...

FROM node:22.11.0-bookworm-slim AS production

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
ENV NODE_ENV=production
ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    chromium \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
  && rm -rf /var/lib/apt/lists/*

COPY --from=deps /app/node_modules /app/node_modules
COPY --from=deps /app/apps/wa-bridge/node_modules /app/apps/wa-bridge/node_modules
COPY apps/wa-bridge ./apps/wa-bridge

RUN mkdir -p /app/apps/wa-bridge/.wwebjs_auth \
  && chown -R node:node /app

USER node
WORKDIR /app/apps/wa-bridge
CMD ["node", "index.mjs"]
