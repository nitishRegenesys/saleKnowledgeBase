from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatMessage:
    role: str
    content: str
    created_at: datetime


@dataclass
class Conversation:
    session_id: str
    messages: list[ChatMessage]