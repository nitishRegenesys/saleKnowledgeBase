from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.rag.embeddings import embed_text


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int

    title: str
    source_url: str | None

    content: str

    category: str
    subcategory: str | None

    vector_score: float
    keyword_score: float
    metadata_score: float
    hybrid_score: float


def hybrid_search(
    query: str,
    *,
    limit: int = 5,
    vector_weight: float = 0.55,
    keyword_weight: float = 0.25,
    metadata_weight: float = 0.20,
    category: str | None = None,
    subcategory: str | None = None,
) -> list[RetrievedChunk]:

    # ---------------------------------------------------------
    # Validate query
    # ---------------------------------------------------------

    query = query.strip()

    if not query:
        return []

    # ---------------------------------------------------------
    # Validate limit
    # ---------------------------------------------------------

    if limit <= 0:
        return []

    # ---------------------------------------------------------
    # Validate weights
    # ---------------------------------------------------------

    if (
        vector_weight < 0
        or keyword_weight < 0
        or metadata_weight < 0
    ):
        raise ValueError(
            "Search weights cannot be negative."
        )

    total_weight = (
        vector_weight
        + keyword_weight
        + metadata_weight
    )

    if total_weight <= 0:
        raise ValueError(
            "At least one search weight must be greater than zero."
        )

    vector_weight /= total_weight
    keyword_weight /= total_weight
    metadata_weight /= total_weight

    # ---------------------------------------------------------
    # Create embedding
    # ---------------------------------------------------------

    query_embedding = embed_text(query)

    # ---------------------------------------------------------
    # Database schema
    # ---------------------------------------------------------

    schema = settings.db_schema

    # ---------------------------------------------------------
    # Retrieval SQL
    # ---------------------------------------------------------

    sql = text(
        f"""
        WITH vector_results AS (

            SELECT
                c.id AS chunk_id,
                c.document_id,
                c.content,

                d.title,
                d.source_url,
                d.category,
                d.subcategory,

                1 - (
                    c.embedding
                    <=> CAST(:embedding AS vector)
                ) AS vector_score

            FROM "{schema}".rag_document_chunks c

            JOIN "{schema}".rag_documents d
                ON d.id = c.document_id

            WHERE
                (
                    CAST(:category AS TEXT) IS NULL
                    OR d.category = CAST(:category AS TEXT)
                )

                AND

                (
                    CAST(:subcategory AS TEXT) IS NULL
                    OR d.subcategory = CAST(:subcategory AS TEXT)
                )

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

            JOIN "{schema}".rag_documents d
                ON d.id = c.document_id

            WHERE
                c.search_vector @@
                websearch_to_tsquery(
                    'english',
                    :query
                )

                AND

                (
                    CAST(:category AS TEXT) IS NULL
                    OR d.category = CAST(:category AS TEXT)
                )

                AND

                (
                    CAST(:subcategory AS TEXT) IS NULL
                    OR d.subcategory = CAST(:subcategory AS TEXT)
                )

            ORDER BY
                keyword_score DESC

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

                d.title,
                d.source_url,
                d.category,
                d.subcategory,

                COALESCE(
                    v.vector_score,
                    0
                ) AS vector_score,

                COALESCE(
                    k.keyword_score,
                    0
                ) AS keyword_score,

                (
                    -- -------------------------------------------------
                    -- Programme/title relevance
                    -- -------------------------------------------------

                    CASE

                        -- Exact title = strongest signal
                        WHEN
                            lower(trim(d.title))
                            = lower(trim(:query))
                        THEN 1.00

                        -- Entire query appears in title
                        WHEN
                            lower(d.title)
                            LIKE '%' || lower(:query) || '%'
                        THEN 0.90

                        -- Important programme abbreviations
                        WHEN
                            lower(d.title) LIKE '%mba%'
                            AND lower(:query) LIKE '%mba%'
                        THEN 0.85

                        WHEN
                            lower(d.title) LIKE '%bba%'
                            AND lower(:query) LIKE '%bba%'
                        THEN 0.85

                        WHEN
                            lower(d.title) LIKE '%dbm%'
                            AND lower(:query) LIKE '%dbm%'
                        THEN 0.85

                        WHEN
                            lower(d.title) LIKE '%pdbm%'
                            AND lower(:query) LIKE '%pdbm%'
                        THEN 0.85

                        WHEN
                            lower(d.title) LIKE '%hcbm%'
                            AND lower(:query) LIKE '%hcbm%'
                        THEN 0.85

                        WHEN
                            lower(d.title) LIKE '%pgpm%'
                            AND lower(:query) LIKE '%pgpm%'
                        THEN 0.85

                        WHEN
                            lower(d.title) LIKE '%pgdm%'
                            AND lower(:query) LIKE '%pgdm%'
                        THEN 0.85

                        -- Query contains the programme name
                        WHEN
                            lower(:query)
                            LIKE '%master of business administration%'
                            AND lower(d.title)
                            LIKE '%master of business administration%'
                        THEN 0.85

                        WHEN
                            lower(:query)
                            LIKE '%bachelor of business administration%'
                            AND lower(d.title)
                            LIKE '%bachelor of business administration%'
                        THEN 0.85

                        WHEN
                            lower(:query)
                            LIKE '%doctor of business management%'
                            AND lower(d.title)
                            LIKE '%doctor of business management%'
                        THEN 0.85

                        ELSE 0.0

                    END

                    +

                    -- -------------------------------------------------
                    -- Category relevance
                    -- -------------------------------------------------

                    CASE

                        WHEN
                            CAST(:category AS TEXT) IS NOT NULL
                            AND d.category =
                                CAST(:category AS TEXT)
                        THEN 0.20

                        ELSE 0.0

                    END

                    +

                    -- -------------------------------------------------
                    -- Subcategory relevance
                    -- -------------------------------------------------

                    CASE

                        WHEN
                            CAST(:subcategory AS TEXT) IS NOT NULL
                            AND d.subcategory =
                                CAST(:subcategory AS TEXT)
                        THEN 0.20

                        ELSE 0.0

                    END

                    +

                    -- -------------------------------------------------
                    -- Information-type relevance
                    -- -------------------------------------------------

                    CASE

                        -- NQF question
                        WHEN
                            (
                                lower(:query) LIKE '%nqf%'
                                OR lower(:query) LIKE '%qualification level%'
                                OR lower(:query) LIKE '%level%'
                            )
                            AND
                            lower(c.content) LIKE '%nqf%'
                        THEN 0.35

                        -- Fee question
                        WHEN
                            (
                                lower(:query) LIKE '%fee%'
                                OR lower(:query) LIKE '%fees%'
                                OR lower(:query) LIKE '%cost%'
                                OR lower(:query) LIKE '%price%'
                                OR lower(:query) LIKE '%tuition%'
                            )
                            AND
                            (
                                lower(c.content) LIKE '%fee%'
                                OR lower(c.content) LIKE '%zar%'
                                OR lower(c.content) LIKE '%usd%'
                                OR lower(c.content) LIKE '%monthly%'
                            )
                        THEN 0.35

                        -- Eligibility question
                        WHEN
                            (
                                lower(:query) LIKE '%eligib%'
                                OR lower(:query) LIKE '%admission%'
                                OR lower(:query) LIKE '%entry requirement%'
                            )
                            AND
                            (
                                lower(c.content) LIKE '%eligibility%'
                                OR lower(c.content) LIKE '%requirement%'
                            )
                        THEN 0.35

                        -- Duration question
                        WHEN
                            (
                                lower(:query) LIKE '%duration%'
                                OR lower(:query) LIKE '%how long%'
                            )
                            AND
                            (
                                lower(c.content) LIKE '%duration%'
                                OR lower(c.content) LIKE '%year%'
                                OR lower(c.content) LIKE '%month%'
                            )
                        THEN 0.35

                        ELSE 0.0

                    END

                ) AS metadata_score

            FROM candidate_ids ids

            JOIN "{schema}".rag_document_chunks c
                ON c.id = ids.chunk_id

            JOIN "{schema}".rag_documents d
                ON d.id = c.document_id

            LEFT JOIN vector_results v
                ON v.chunk_id = ids.chunk_id

            LEFT JOIN keyword_results k
                ON k.chunk_id = ids.chunk_id
        ),

        scored AS (

            SELECT
                *,

                (
                    :vector_weight * vector_score
                    +
                    :keyword_weight * keyword_score
                    +
                    :metadata_weight * metadata_score
                ) AS hybrid_score

            FROM combined
        ),

        ranked_documents AS (

            SELECT
                *,

                ROW_NUMBER() OVER (
                    PARTITION BY document_id

                    ORDER BY
                        hybrid_score DESC,
                        vector_score DESC,
                        keyword_score DESC,
                        metadata_score DESC,
                        chunk_id
                ) AS document_rank

            FROM scored
        )

        SELECT
            chunk_id,
            document_id,

            title,
            source_url,

            content,

            category,
            subcategory,

            vector_score,
            keyword_score,
            metadata_score,
            hybrid_score

        FROM ranked_documents

        WHERE document_rank = 1

        ORDER BY
            hybrid_score DESC,
            vector_score DESC,
            keyword_score DESC,
            metadata_score DESC,
            document_id

        LIMIT :limit
        """
    )

    # ---------------------------------------------------------
    # Execute query
    # ---------------------------------------------------------

    with engine.connect() as conn:

        rows = conn.execute(
            sql,
            {
                "embedding": str(
                    query_embedding
                ),

                "query": query,

                "category": category,

                "subcategory": subcategory,

                "limit": limit,

                "candidate_limit": max(
                    limit * 8,
                    30,
                ),

                "vector_weight": vector_weight,

                "keyword_weight": keyword_weight,

                "metadata_weight": metadata_weight,
            },
        ).mappings().all()

    # ---------------------------------------------------------
    # Convert rows
    # ---------------------------------------------------------

    return [
        RetrievedChunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],

            title=row["title"],
            source_url=row["source_url"],

            content=row["content"],

            category=row["category"],
            subcategory=row["subcategory"],

            vector_score=float(
                row["vector_score"]
            ),

            keyword_score=float(
                row["keyword_score"]
            ),

            metadata_score=float(
                row["metadata_score"]
            ),

            hybrid_score=float(
                row["hybrid_score"]
            ),
        )

        for row in rows
    ]