# POCU Python agent for Google Cloud Run
# Includes Node + Hardhat for Kaggle CSV preprocess (scripts/preprocess-tabular.ts).
#
# Build:
#   docker build -t pocu-agent .
#
# Run locally:
#   docker run --rm -p 8080:8080 --env-file .env -e PORT=8080 pocu-agent
#
# Cloud Run deploy (example):
#   gcloud run deploy pocu-agent \
#     --source . \
#     --region us-central1 \
#     --allow-unauthenticated \
#     --port 8080 \
#     --memory 2Gi \
#     --cpu 2 \
#     --timeout 3600 \
#     --set-env-vars "SUPABASE_URL=...,GROQ_API_KEY=...,ACCOUNT_ID=..."

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    AGENT_EMBEDDED_WORKER=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    build-essential \
    git \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Node deps (Hardhat preprocess during dataset prep)
COPY package.json package-lock.json ./
RUN npm ci

COPY hardhat.config.ts tsconfig.json ./
COPY contracts ./contracts
COPY scripts/preprocess-tabular.ts ./scripts/preprocess-tabular.ts
COPY src ./src

RUN npx hardhat compile

# Python agent
COPY agent/requirements.txt ./agent/requirements.txt
RUN pip install --no-cache-dir -r agent/requirements.txt

COPY agent ./agent

RUN mkdir -p data/kaggle output deployments

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -f "http://127.0.0.1:${PORT}/health" || exit 1

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --app-dir agent"]
