from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.rag import router as rag_router
from app.api.routes.voice import router as voice_router


# ============================================================
# App
# ============================================================

app = FastAPI(
    title="Sales Knowledge Base",
    description="Regenesys Sales Knowledge Base RAG API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Routes
# ============================================================

app.include_router(rag_router)
app.include_router(voice_router)


# ============================================================
# Health
# ============================================================

@app.get(
    "/health",
    tags=["Health"],
)
def health() -> dict[str, str]:
    return {
        "status": "ok",
    }