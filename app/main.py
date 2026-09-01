from fastapi import FastAPI

from app.api.routes.rag import router as rag_router


app = FastAPI(
    title="Sales Knowledge Base",
    description="Regenesys Sales Knowledge Base RAG API",
    version="1.0.0",
)


# ============================================================
# Routes
# ============================================================


app.include_router(rag_router)


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