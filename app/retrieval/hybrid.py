from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.rag.embeddings import embed_text


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    content: str
    category: str
    subcategory: str | None
    vector_score: float
    keyword_score: float
    hybrid_score: float


def hybrid_search(
    query: str,
    *,
    limit: int = 5,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> list[RetrievedChunk]:

    if not query.strip():
        return []

    if limit <= 0:
        return []

    if vector_weight < 0 or keyword_weight < 0:
        raise ValueError(
            "Search weights cannot be negative."
        )

    total_weight = (
        vector_weight + keyword_weight
    )

    if total_weight <= 0:
        raise ValueError(
            "At least one search weight must be greater than zero."
        )

    vector_weight /= total_weight
    keyword_weight /= total_weight

    query_embedding = embed_text(query)

    schema = settings.db_schema

    sql = text(
        f"""
        WITH vector_results AS (
            SELECT
                c.id AS chunk_id,
                c.document_id,
                c.content,
                d.category,
                d.subcategory,

                1 - (
                    c.embedding
                    <=> CAST(:embedding AS vector)
                ) AS vector_score

            FROM "{schema}".rag_document_chunks c

            JOIN "{schema}".rag_documents d
                ON d.id = c.document_id

            ORDER BY
                c.embedding
                <=> CAST(:embedding AS vector)

            LIMIT :candidate_limit
        ),

        keyword_results AS (
            SELECT
                c.id AS chunk_id,

                ts_rank_cd(
                    c.search_vector,
                    websearch_to_tsquery(
                        'english',
                        :query
                    )
                ) AS keyword_score

            FROM "{schema}".rag_document_chunks c

            WHERE c.search_vector @@
                websearch_to_tsquery(
                    'english',
                    :query
                )

            ORDER BY keyword_score DESC

            LIMIT :candidate_limit
        ),

        candidate_ids AS (
            SELECT chunk_id
            FROM vector_results

            UNION

            SELECT chunk_id
            FROM keyword_results
        ),

        combined AS (
            SELECT
                ids.chunk_id,
                c.document_id,
                c.content,
                d.category,
                d.subcategory,

                COALESCE(
                    v.vector_score,
                    0
                ) AS vector_score,

                COALESCE(
                    k.keyword_score,
                    0
                ) AS keyword_score

            FROM candidate_ids ids

            JOIN "{schema}".rag_document_chunks c
                ON c.id = ids.chunk_id

            JOIN "{schema}".rag_documents d
                ON d.id = c.document_id

            LEFT JOIN vector_results v
                ON v.chunk_id = ids.chunk_id

            LEFT JOIN keyword_results k
                ON k.chunk_id = ids.chunk_id
        )

        SELECT
            chunk_id,
            document_id,
            content,
            category,
            subcategory,
            vector_score,
            keyword_score,

            (
                :vector_weight * vector_score
                +
                :keyword_weight * keyword_score
            ) AS hybrid_score

        FROM combined

        ORDER BY hybrid_score DESC

        LIMIT :limit
        """
    )

    with engine.connect() as conn:

        rows = conn.execute(
            sql,
            {
                "embedding": str(
                    query_embedding
                ),
                "query": query,
                "limit": limit,
                "candidate_limit": max(
                    limit * 5,
                    20,
                ),
                "vector_weight": vector_weight,
                "keyword_weight": keyword_weight,
            },
        )

        return [
            RetrievedChunk(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                content=row.content,
                category=row.category,
                subcategory=row.subcategory,
                vector_score=float(
                    row.vector_score
                ),
                keyword_score=float(
                    row.keyword_score
                ),
                hybrid_score=float(
                    row.hybrid_score
                ),
            )
            for row in rows
        ]
