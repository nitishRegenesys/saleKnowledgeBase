from app.llm.factory import get_llm
from app.rag.context import build_context
from app.retrieval.hybrid import hybrid_search


SYSTEM_PROMPT = """
You are a sales knowledge assistant for Regenesys.

Answer the user's question using ONLY the information
provided in the retrieved knowledge-base context.

Rules:

1. Do not invent information.
2. Do not use outside knowledge.
3. If the answer is not supported by the context, say:
   "I couldn't find that information in the knowledge base."
4. Prefer precise information over assumptions.
5. Combine multiple retrieved sources when relevant.
6. Preserve distinctions between:
   - programmes
   - schools
   - categories
   - fees
   - admission requirements
   - NQF levels
   - duration
   - delivery mode
   - certificates
   - other programme details
7. Do not infer missing information.
8. If sources contain conflicting information, explicitly say
   that the retrieved sources contain conflicting information.
9. Do not claim information that is not explicitly supported
   by the retrieved context.
10. When answering programme-list questions, include only
    programmes supported by the retrieved context.
11. Do not generate source numbers or citation markers.
    Sources are returned separately by the API.
""".strip()


def answer_question(
    question: str,
    *,
    limit: int = 5,
    category: str | None = None,
    subcategory: str | None = None,
) -> dict:

    # ---------------------------------------------------------
    # Validate question
    # ---------------------------------------------------------

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    # ---------------------------------------------------------
    # Retrieve
    # ---------------------------------------------------------

    results = hybrid_search(
        question,
        limit=limit,
        category=category,
        subcategory=subcategory,
    )

    # ---------------------------------------------------------
    # Build context
    # ---------------------------------------------------------

    context = build_context(results)

    # ---------------------------------------------------------
    # No results
    # ---------------------------------------------------------

    if not context:

        return {
            "answer": (
                "I couldn't find that information "
                "in the knowledge base."
            ),
            "sources": [],
            "results": [],
        }

    # ---------------------------------------------------------
    # LLM prompt
    # ---------------------------------------------------------

    user_prompt = f"""
    Retrieved knowledge-base context:

    {context}

    User question:

    {question}

    Answer the question using ONLY the retrieved
    knowledge-base context.

    Do not use outside knowledge.

    Do not add source numbers, source markers,
    citations, or references such as [Source 1],
    【Source 1】, or (Source 1).

    The API will provide the source documents
    separately.

    If the context does not contain enough information
    to answer the question, say:

    "I couldn't find that information in the knowledge base."
    """.strip()
    # ---------------------------------------------------------
    # Generate answer
    # ---------------------------------------------------------

    llm = get_llm()

    answer = llm.generate(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # ---------------------------------------------------------
    # Build unique sources
    # ---------------------------------------------------------

    sources = []

    seen = set()

    for result in results:

        key = (
            result.document_id,
            result.source_url,
        )

        if key in seen:
            continue

        seen.add(key)

        sources.append(
            {
                "document_id": result.document_id,
                "title": result.title,
                "url": result.source_url,
                "category": result.category,
                "subcategory": result.subcategory,
            }
        )

    # ---------------------------------------------------------
    # Return response
    # ---------------------------------------------------------

    return {
        "answer": answer,
        "sources": sources,
        "results": results,
    }