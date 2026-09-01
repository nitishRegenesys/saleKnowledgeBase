from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.answer import answer_question


router = APIRouter(
    prefix="/api/v1/rag",
    tags=["RAG"],
)


# ============================================================
# Request
# ============================================================


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Question to ask the knowledge base.",
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of retrieved sources.",
    )

    category: str | None = Field(
        default=None,
        description="Optional knowledge-base category filter.",
    )

    subcategory: str | None = Field(
        default=None,
        description="Optional knowledge-base subcategory filter.",
    )


# ============================================================
# Response
# ============================================================


class SourceResponse(BaseModel):
    document_id: int
    title: str
    url: str | None
    category: str
    subcategory: str | None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]


# ============================================================
# Ask
# ============================================================


@router.post(
    "/ask",
    response_model=AskResponse,
)
def ask_question(request: AskRequest) -> AskResponse:

    try:
        result = answer_question(
            request.question,
            limit=request.limit,
            category=request.category,
            subcategory=request.subcategory,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        # Keep internal details out of the API response.
        print(
            "RAG ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process the "
                "knowledge-base query."
            ),
        ) from exc

    return AskResponse(
        answer=result["answer"],
        sources=[
            SourceResponse(
                document_id=source["document_id"],
                title=source["title"],
                url=source["url"],
                category=source["category"],
                subcategory=source["subcategory"],
            )
            for source in result["sources"]
        ],
    )