from sqlalchemy import select

from app.core.database import SessionLocal
from app.ingestion.chunker import chunk_text
from app.ingestion.service import ExtractedDocument
from app.models import Document, DocumentChunk
from app.rag.embeddings import embed_texts


def save_document(
    extracted: ExtractedDocument,
) -> tuple[Document, bool]:

    chunks = chunk_text(
        extracted.text,
    )

    if not chunks:
        raise ValueError(
            "Cannot save document without chunks."
        )

    embeddings = embed_texts(
        chunks
    )

    if len(chunks) != len(embeddings):
        raise RuntimeError(
            "Chunk/embedding count mismatch."
        )

    with SessionLocal() as session:

        # -----------------------------------------------------
        # Deduplicate using content hash
        # -----------------------------------------------------

        existing = session.scalar(
            select(Document).where(
                Document.content_hash
                == extracted.content_hash
            )
        )

        if existing:
            return existing, False

        # -----------------------------------------------------
        # Document
        # -----------------------------------------------------

        document = Document(
            filename=extracted.filename,
            title=extracted.title,
            source_type=extracted.source_type,
            source_url=extracted.source_url,
            mime_type=extracted.mime_type,
            file_path=extracted.file_path,
            content_hash=extracted.content_hash,
            category=extracted.category,
            subcategory=extracted.subcategory,
            metadata_json=extracted.metadata,
        )

        session.add(document)
        session.flush()

        # -----------------------------------------------------
        # Chunks
        # -----------------------------------------------------

        for chunk_index, (
            content,
            embedding,
        ) in enumerate(
            zip(chunks, embeddings)
        ):
            session.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk_index,
                    content=content,
                    embedding=embedding,
                )
            )

        session.commit()
        session.refresh(document)

        return document, True