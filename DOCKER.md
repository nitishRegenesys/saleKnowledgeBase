# Running saleKnowledgeBase in Docker

The RAG backend (`app/`) **and** the React UI (`frontend/`) run in **one
container** on port **8000**: `npm run build` output is baked into the image and
served by FastAPI itself (`app/main.py` mounts `frontend/dist`), so there is a
single process and a single URL.

```
browser ──► http://localhost:8000/            FastAPI + StaticFiles  (UI)
            http://localhost:8000/api/v1/rag/*  RAG over Postgres/pgvector + AWS Bedrock
            ws://localhost:8000/api/v1/voice/ws relay ──► voice-engine container :8001
```

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | 3 stages: Vite build → Python venv + CPU torch + baked embedding model → runtime |
| `.dockerignore` | Keeps venvs, `node_modules`, `frontend/dist`, `.git` and `.env` out of the build |
| `docker-compose.yml` | The single `sale-knowledge-base` service (port 8000, `.env`, voice URL) |

## Run

```powershell
cd d:\tg-imp\saleKnowledgeBase
docker compose config          # optional: review the merged environment
docker compose build           # first build takes several minutes (torch + model download)
docker compose up -d
docker compose logs -f sale-knowledge-base   # expect: "Embedding model loaded."
```

```powershell
curl.exe -s http://localhost:8000/health                  # {"status":"ok"}
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:8000/   # 200 (the UI)
curl.exe -s http://localhost:8000/api/v1/voice/health      # {"voice_available":true}
```

Open <http://localhost:8000> for the UI. The previous workflow (host `uvicorn`
on 8000 + `npm run dev` on 5173) still works unchanged.

## What differs from running on the host

| Setting | Host | Container | Why |
|---------|------|-----------|-----|
| `VOICE_ENGINE_URL` | `http://localhost:8001` | `http://host.docker.internal:8001` | the gateway runs in its own container (published on host loopback `127.0.0.1:8001`) |
| Frontend API base | hardcoded `http://localhost:8000` | page origin (`window.location.origin`) | UI + API share one origin; override with `--build-arg VITE_API_BASE_URL=...` |
| Embedding model | downloaded on first start | baked into the image (`/opt/hf-cache`) | fast, offline-capable startup |

Everything else (`DB_*` RDS credentials, `AWS_API_KEY`, `AWS_BEDROCK_REGION`,
`LLM_*`) comes straight from the repo `.env` via `env_file:` — nothing else
changes.

The voice-engine container needs **no** change: its `FACILITATOR_API_URL`
(`http://host.docker.internal:8000`) resolves to this container's published
port, which is also how this container reaches the gateway.

## Operational notes

* **Port 8000 is host-loopback only** (`127.0.0.1:8000:8000`) — the UI is not
  exposed to the LAN, matching the voice-engine container's convention.
* **One uvicorn worker on purpose.** Sessions are stored in Postgres, so extra
  workers are correct but each one loads its own copy of the embedding model
  (~1.5 GB RAM). Give the container at least 3–4 GB.
* **Image size** ≈ 2.9 GB measured (slim base, CPU-only torch wheel `torch==2.13.0+cpu`,
  ~440 MB of baked model cache, doc extractors + scipy/scikit-learn/pandas).
* **Changing the model**: rebuild with `docker compose build --build-arg EMBEDDING_MODEL=<hf-id>`
  and keep `EMBEDDING_MODEL` in `.env` in sync, otherwise the container downloads
  the new model at startup.
* **Database prerequisites** (unchanged): the RDS instance must be reachable from
  Docker's egress IP, the `vector` (pgvector) extension must be installed, and the
  `user_nitishk` schema must already exist. Bootstrap tables/indexes with:
  `docker compose run --rm sale-knowledge-base python -m app.core.init_db`.
* **Ingestion scripts** (`app/ingestion/*`, e.g. `python -m app.ingestion.bulk`)
  read a crawler folder **outside** the repo (`../universal-web-scraper/...`).
  Run them on the host, or bind-mount that folder into the container and adjust
  the path — the image does not ship it.
* Running `uvicorn app.main:app` directly on the host now also serves the UI when
  `frontend/dist` exists locally (the mount is conditional on that directory).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Container exits at startup with a psycopg/pgvector error | RDS security group / credentials, or the `vector` extension or `user_nitishk` schema is missing |
| `"voice_available": false` | the voice-engine container is not running (`cd voice-engine; docker compose up -d`), or `VOICE_ENGINE_URL` is wrong |
| UI loads but every request fails | open the app via `http://localhost:8000` (not `:5173`) so the same-origin API base applies; a custom origin needs `--build-arg VITE_API_BASE_URL=...` |
| Port 8000 already in use | stop the host `uvicorn ... --port 8000` before `docker compose up -d` |
| Slow first response | the model is loading; the baked cache should make this a few seconds — check `docker compose logs` |
| Changed `.env`, nothing happened | `docker compose up -d --force-recreate` |
