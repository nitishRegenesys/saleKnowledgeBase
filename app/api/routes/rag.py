import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.rag.answer import (
    answer_question,
    answer_question_stream,
)
from app.rag.conversation_service import (
    add_message,
    create_session,
    get_messages,
    session_exists,
    list_sessions,
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

class SessionResponse(BaseModel):

    session_id: str
    title: str
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):

    sessions: list[SessionResponse]


class ConversationMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str


class ConversationResponse(BaseModel):
    session_id: str
    messages: list[ConversationMessageResponse]


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
# SESSIONS
# ============================================================


@router.get(
    "/sessions",
    response_model=SessionListResponse,
)
def get_sessions() -> SessionListResponse:

    try:

        sessions = list_sessions()

    except Exception as exc:

        print(
            "SESSION LIST ERROR:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load "
                "conversation sessions."
            ),
        ) from exc

    return SessionListResponse(
        sessions=[
            SessionResponse(
                session_id=session["session_id"],
                title=session["title"],
                created_at=session["created_at"],
                updated_at=session["updated_at"],
            )
            for session in sessions
        ]
    )

# ============================================================
# GET CONVERSATION
# ============================================================


@router.get(
    "/sessions/{session_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    session_id: str,
) -> ConversationResponse:

    # ---------------------------------------------------------
    # Validate session
    # ---------------------------------------------------------

    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation session not found.",
        )

    # ---------------------------------------------------------
    # Load messages
    # ---------------------------------------------------------

    try:

        messages = get_messages(
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
                "conversation."
            ),
        ) from exc

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return ConversationResponse(
        session_id=session_id,
        messages=[
            ConversationMessageResponse(
                role=message.role,
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            for message in messages
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


# ============================================================
# CHAT STREAM (SSE) — streaming answer for voice turns
# ============================================================


@router.post(
    "/chat/stream",
)
async def chat_stream(
    request: ChatRequest,
) -> StreamingResponse:

    # ---------------------------------------------------------
    # Resolve / create the session (mirrors the /chat logic)
    # ---------------------------------------------------------

    if not request.session_id or not session_exists(
        request.session_id
    ):
        session_id = create_session()
    else:
        session_id = request.session_id

    try:

        previous_messages = get_messages(
            session_id
        )

    except Exception as exc:

        print(
            "CONVERSATION STREAM LOAD ERROR:",
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
    # SSE event generator
    # ---------------------------------------------------------

    async def event_generator():

        try:

            async for event in answer_question_stream(
                request.message,
                limit=request.limit,
                category=request.category,
                subcategory=request.subcategory,
                conversation_history=conversation_history,
            ):

                if event["type"] == "delta":

                    payload = {
                        "type": "delta",
                        "text": event["text"],
                    }

                else:

                    answer = event["answer"]

                    add_message(
                        session_id,
                        "user",
                        request.message,
                    )

                    add_message(
                        session_id,
                        "assistant",
                        answer,
                    )

                    payload = {
                        "type": "done",
                        "session_id": session_id,
                        "answer": answer,
                        "sources": event["sources"],
                    }

                yield (
                    f"data: "
                    f"{json.dumps(payload)}\n\n"
                )

        except Exception as exc:

            print(
                "CHAT STREAM ERROR:",
                repr(exc),
            )

            payload = {
                "type": "error",
                "detail": (
                    "Unable to process "
                    "the conversation."
                ),
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )