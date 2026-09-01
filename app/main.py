from fastapi import FastAPI

from app.api.routes.rag import router as rag_router


app = FastAPI(
    title="Regenesys Sales Knowledge Base",
    description="Hybrid RAG API for the Regenesys sales knowledge base.",
    version="1.0.0",
)


app.include_router(
    rag_router,
    prefix="/api/v1",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
    }