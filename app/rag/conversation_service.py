from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.conversation import Conversation, Message


def create_session() -> str:
    """
    Create and persist a new conversation session.
    """

    session_id = uuid4()
    now = datetime.now(timezone.utc)

    db = SessionLocal()

    try:
        conversation = Conversation(
            id=session_id,
            created_at=now,
            updated_at=now,
        )

        db.add(conversation)
        db.commit()

        return str(session_id)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def session_exists(
    session_id: str,
) -> bool:
    """
    Check whether a conversation exists.
    """

    try:
        conversation_id = UUID(session_id)
    except ValueError:
        return False

    db = SessionLocal()

    try:
        result = db.execute(
            select(Conversation.id)
            .where(
                Conversation.id == conversation_id
            )
        )

        return result.scalar_one_or_none() is not None

    finally:
        db.close()


def get_messages(
    session_id: str,
) -> list[Message]:
    """
    Load conversation messages from PostgreSQL.
    """

    try:
        conversation_id = UUID(session_id)
    except ValueError:
        return []

    db = SessionLocal()

    try:
        result = db.execute(
            select(Message)
            .where(
                Message.conversation_id
                == conversation_id
            )
            .order_by(
                Message.created_at.asc(),
                Message.id.asc(),
            )
        )

        return list(
            result.scalars().all()
        )

    finally:
        db.close()


def add_message(
    session_id: str,
    role: str,
    content: str,
) -> Message:
    """
    Persist a message and update the
    conversation timestamp.
    """

    conversation_id = UUID(session_id)

    now = datetime.now(timezone.utc)

    db = SessionLocal()

    try:
        conversation = db.execute(
            select(Conversation)
            .where(
                Conversation.id
                == conversation_id
            )
        ).scalar_one_or_none()

        if conversation is None:
            raise ValueError(
                f"Conversation session "
                f"{session_id} does not exist."
            )

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=now,
        )

        conversation.updated_at = now

        db.add(message)

        db.commit()

        db.refresh(message)

        return message

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def clear_session(
    session_id: str,
) -> None:
    """
    Delete a conversation and its messages.
    """

    try:
        conversation_id = UUID(session_id)
    except ValueError:
        return

    db = SessionLocal()

    try:
        conversation = db.execute(
            select(Conversation)
            .where(
                Conversation.id
                == conversation_id
            )
        ).scalar_one_or_none()

        if conversation is not None:
            db.delete(conversation)
            db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()