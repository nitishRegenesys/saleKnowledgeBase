from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    """
    Clean extracted text while preserving useful structure.
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive whitespace while keeping paragraph boundaries.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Split document text into overlapping chunks.

    Chunk size and overlap are character-based.
    We prefer paragraph/sentence boundaries when possible.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size"
        )

    text = normalize_text(text)

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[start:end]

        # If we're not at the end, try to end naturally.
        if end < text_length:
            boundary = max(
                chunk.rfind("\n\n"),
                chunk.rfind(". "),
                chunk.rfind("? "),
                chunk.rfind("! "),
            )

            # Don't create tiny chunks just to find a boundary.
            if boundary >= chunk_size * 0.6:
                end = start + boundary + 1
                chunk = text[start:end]

        chunk = chunk.strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        # Overlap from the previous chunk.
        start = max(
            end - chunk_overlap,
            start + 1,
        )

    return chunks