
# ---------------------------------------------------------------------------
# Stage 1 — build the React frontend
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /frontend

# Install dependencies first so this layer is cached across source changes
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Optional absolute API origin for the built bundle. Empty = same origin
# (window.location.origin), which is what the single container wants.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python dependencies (venv) + the embedding model
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS builder

# build-essential: gcc + make + libc6-dev (assert.h etc.) — `gcc` alone is not
#   enough on slim images, which is what broke psycopg2's source build.
# libpq-dev: psycopg2 in requirements.txt has no cp313 wheel and builds from source.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt ./

RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --upgrade pip \
    && /venv/bin/pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

# Bake the embeddings model into the image: instant startup, works offline and
# keeps the first request from blocking on a ~440 MB Hugging Face download.
# Keep this in sync with EMBEDDING_MODEL in .env (build with
# --build-arg EMBEDDING_MODEL=... if that ever changes).
ARG EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
ENV HF_HOME=/opt/hf-cache \
    HF_HUB_DISABLE_TELEMETRY=1 \
    EMBEDDING_MODEL=${EMBEDDING_MODEL}

RUN /venv/bin/python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['EMBEDDING_MODEL'])"

# ---------------------------------------------------------------------------
# Stage 3 — runtime
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

# Non-root user (same convention as the sibling images in this workspace)
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Runtime library for psycopg2 / psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv
# --chown: the cache must stay writable (Hugging Face writes lock files)
COPY --chown=appuser:appuser --from=builder /opt/hf-cache /opt/hf-cache

WORKDIR /app

COPY --chown=appuser:appuser app /app/app
RUN mkdir -p /app/frontend && chown appuser:appuser /app/frontend
COPY --from=frontend --chown=appuser:appuser /frontend/dist /app/frontend/dist

ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf-cache \
    EMBEDDING_MODEL=BAAI/bge-base-en-v1.5

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
