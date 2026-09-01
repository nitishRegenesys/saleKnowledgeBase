from collections import defaultdict
from datetime import datetime, timezone

from app.rag.conversation import ChatMessage


# Temporary in-memory storage.
#
# We will replace this with PostgreSQL persistence
# in the next step.

_sessions: dict[str, list[ChatMessage]] = defaultdict(list)


def get_messages(
    session_id: str,
) -> list[ChatMessage]:

    return list(
        _sessions.get(
            session_id,
            [],
        )
    )


def add_message(
    session_id: str,
    role: str,
    content: str,
) -> ChatMessage:

    message = ChatMessage(
        role=role,
        content=content,
        created_at=datetime.now(
            timezone.utc
        ),
    )

    _sessions[session_id].append(
        message
    )

    return message


def clear_session(
    session_id: str,
) -> None:

    _sessions.pop(
        session_id,
        None,
    )