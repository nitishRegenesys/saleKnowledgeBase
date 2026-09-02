from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.answer import answer_question
from app.rag.conversation_service import (
    add_message,
    create_session,
    get_messages,
    session_exists,
)


router = APIRouter(
    prefix="/api/v1/rag",
    tags=["RAG"],
)


# ============================================================
# Request models
# ============================================================


class AskRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    category: str | None = None

    subcategory: str | None = None


class ChatRequest(BaseModel):

    session_id: str | None = None

    message: str = Field(
        ...,
        min_length=1,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    category: str | None = None

    subcategory: str | None = None


# ============================================================
# Response models
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


class ChatResponse(BaseModel):

    session_id: str
    answer: str
    sources: list[SourceResponse]


# ============================================================
# ASK
# ============================================================


@router.post(
    "/ask",
    response_model=AskResponse,
)
def ask_question(
    request: AskRequest,
) -> AskResponse:

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


# ============================================================
# CHAT
# ============================================================


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
) -> ChatResponse:

    # ---------------------------------------------------------
    # Create or validate conversation session
    # ---------------------------------------------------------

    if request.session_id:

        session_id = request.session_id

        if not session_exists(
            session_id
        ):
            raise HTTPException(
                status_code=404,
                detail=(
                    "Conversation session "
                    "not found."
                ),
            )

    else:

        try:

            session_id = create_session()

        except Exception as exc:

            print(
                "SESSION CREATE ERROR:",
                repr(exc),
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Unable to create "
                    "conversation session."
                ),
            ) from exc

    # ---------------------------------------------------------
    # Load previous conversation
    # ---------------------------------------------------------

    try:

        previous_messages = get_messages(
            session_id
        )

    except Exception as exc:

        print(
            "CONVERSATION LOAD ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load "
                "conversation history."
            ),
        ) from exc

    conversation_history = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in previous_messages
    ]

    # ---------------------------------------------------------
    # Generate answer
    # ---------------------------------------------------------

    try:

        result = answer_question(
            request.message,
            limit=request.limit,
            category=request.category,
            subcategory=request.subcategory,
            conversation_history=conversation_history,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        print(
            "CHAT ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process "
                "the conversation."
            ),
        ) from exc

    # ---------------------------------------------------------
    # Save user message
    # ---------------------------------------------------------

    try:

        add_message(
            session_id,
            "user",
            request.message,
        )

    except Exception as exc:

        print(
            "USER MESSAGE SAVE ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save "
                "user message."
            ),
        ) from exc

    # ---------------------------------------------------------
    # Save assistant message
    # ---------------------------------------------------------

    try:

        add_message(
            session_id,
            "assistant",
            result["answer"],
        )

    except Exception as exc:

        print(
            "ASSISTANT MESSAGE SAVE ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save "
                "assistant message."
            ),
        ) from exc

    # ---------------------------------------------------------
    # Return
    # ---------------------------------------------------------

    return ChatResponse(
        session_id=session_id,
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