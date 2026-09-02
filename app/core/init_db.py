from sqlalchemy import text

from app.core.config import settings
from app.core.database import Base, engine
from app.models import (Document, DocumentChunk,Conversation, Message)


def init_db():
    schema = settings.db_schema

    print(f"Database schema: {schema}")

    with engine.begin() as conn:

        # pgvector must already be installed in the database.
        vector_version = conn.execute(
            text("""
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
            """)
        ).scalar()

        if not vector_version:
            raise RuntimeError(
                "pgvector extension is not installed. "
                "Ask the database administrator to install it."
            )

        print(f"pgvector: {vector_version}")

        # The schema must already exist.
        schema_exists = conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.schemata
                    WHERE schema_name = :schema
                )
            """),
            {"schema": schema},
        ).scalar()

        if not schema_exists:
            raise RuntimeError(
                f"Database schema '{schema}' does not exist. "
                "Create it or ask the database administrator to grant "
                "permission to create it."
            )

        # Verify that the application user can use the schema.
        has_usage = conn.execute(
            text("""
                SELECT has_schema_privilege(
                    current_user,
                    :schema,
                    'USAGE'
                )
            """),
            {"schema": schema},
        ).scalar()

        if not has_usage:
            raise RuntimeError(
                f"User '{settings.db_user}' does not have USAGE "
                f"permission on schema '{schema}'."
            )

        print(f"Schema available: {schema}")

    # SQLAlchemy models define the schema and table names.
    Base.metadata.create_all(engine)

    documents_table = f'"{schema}"."rag_documents"'
    chunks_table = f'"{schema}"."rag_document_chunks"'

    with engine.begin() as conn:

        # PostgreSQL full-text search.
        #
        # search_vector is generated from chunk content.
        conn.execute(
            text(f"""
                ALTER TABLE {chunks_table}
                ADD COLUMN IF NOT EXISTS search_vector tsvector
                GENERATED ALWAYS AS (
                    to_tsvector(
                        'english',
                        coalesce(content, '')
                    )
                ) STORED
            """)
        )

        # Keyword-search index.
        conn.execute(
            text(f"""
                CREATE INDEX IF NOT EXISTS
                ix_rag_document_chunks_search_vector
                ON {chunks_table}
                USING GIN (search_vector)
            """)
        )

        # Vector similarity index.
        conn.execute(
            text(f"""
                CREATE INDEX IF NOT EXISTS
                ix_rag_document_chunks_embedding
                ON {chunks_table}
                USING hnsw (embedding vector_cosine_ops)
            """)
        )

        # Print final table locations.
        print()
        print("RAG TABLE LOCATIONS:")
        print(f"  {schema}.rag_documents")
        print(f"  {schema}.rag_document_chunks")


if __name__ == "__main__":
    print("Initializing RAG database...")
    init_db()
    print("DATABASE INITIALIZED")