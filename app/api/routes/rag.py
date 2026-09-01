from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.answer import answer_question


router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Question to ask the sales knowledge base.",
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of retrieved documents.",
    )

    category: str | None = Field(
        default=None,
        description="Optional knowledge-base category filter.",
    )

    subcategory: str | None = Field(
        default=None,
        description="Optional knowledge-base subcategory filter.",
    )


class SourceResponse(BaseModel):
    document_id: int
    title: str
    url: str | None
    category: str
    subcategory: str | None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]


@router.post(
    "/ask",
    response_model=AskResponse,
)
def ask(request: AskRequest):

    try:

        result = answer_question(
            request.question,
            limit=request.limit,
            category=request.category,
            subcategory=request.subcategory,
        )

        return {
            "answer": result["answer"],
            "sources": result["sources"][:3],
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"RAG request failed: {exc}",
        )