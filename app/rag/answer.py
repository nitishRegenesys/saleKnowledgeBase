from app.llm.factory import get_llm
from app.rag.context import build_context
from app.retrieval.hybrid import hybrid_search
from app.query.understanding import understand_query


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
5. Combine multiple sources when relevant.
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


# =============================================================
# Query classification helpers
# =============================================================

def _is_programme_list_question(
    question: str,
) -> bool:

    q = question.lower()

    list_phrases = (
        "what programmes",
        "which programmes",
        "programmes are available",
        "programs are available",
        "what courses",
        "which courses",
        "what offerings",
        "what qualifications",
    )

    return any(
        phrase in q
        for phrase in list_phrases
    )


def _contains_programme_identifier(
    question: str,
) -> bool:

    q = question.lower()

    identifiers = (
        "mba",
        "bba",
        "dbm",
        "pdbm",
        "hcbm",
        "pgpm",
        "pgdm",
        "bfs",
        "bcomppe",
        "bcompt",
        "pdia",
        "pdpm",
        "bpm",
        "mpm",
        "ndpa",
        "adpm",
        "hcpm",
        "bitid",
        "bsc",
        "hcss",
        "pdds",
        "ai for developers",
        "ai for executives",
        "ai fluency",
        "ai agentic",
        "artificial intelligence",
        "software developer",
        "cybersecurity analyst",
        "data science practitioner",
    )

    return any(
        identifier in q
        for identifier in identifiers
    )


def _filter_relevant_results(
    question: str,
    results,
) -> list:

    if not results:
        return []

    # ---------------------------------------------------------
    # Broad programme-list questions need multiple documents.
    # Keep the retrieval ranking intact.
    # ---------------------------------------------------------

    if _is_programme_list_question(question):
        return results

    # ---------------------------------------------------------
    # Specific programme questions.
    #
    # If the question identifies a programme, keep the
    # strongest matching document(s) rather than passing
    # unrelated semantically similar documents to the LLM.
    # ---------------------------------------------------------

    if _contains_programme_identifier(question):

        q = question.lower()

        programme_results = []

        for result in results:

            title = (
                result.title or ""
            ).lower()

            content = (
                result.content or ""
            ).lower()

            # Strong title match.
            if any(
                identifier in title
                for identifier in (
                    "mba",
                    "bba",
                    "dbm",
                    "pdbm",
                    "hcbm",
                    "pgpm",
                    "pgdm",
                    "bfs",
                    "bcomppe",
                    "bcompt",
                    "pdia",
                    "pdpm",
                    "bpm",
                    "mpm",
                    "ndpa",
                    "adpm",
                    "hcpm",
                    "bitid",
                    "bsc",
                    "hcss",
                    "pdds",
                )
                if identifier in q
            ):
                programme_results.append(result)
                continue

            # Full programme-name matches.
            programme_names = (
                (
                    "master of business administration",
                    "master of business administration",
                ),
                (
                    "bachelor of business administration",
                    "bachelor of business administration",
                ),
                (
                    "doctor of business management",
                    "doctor of business management",
                ),
                (
                    "postgraduate diploma in business management",
                    "postgraduate diploma in business management",
                ),
                (
                    "higher certificate in business management",
                    "higher certificate in business management",
                ),
                (
                    "postgraduate diploma in project management",
                    "postgraduate diploma in project management",
                ),
                (
                    "postgraduate diploma in digital marketing",
                    "postgraduate diploma in digital marketing",
                ),
            )

            for query_name, title_name in programme_names:

                if (
                    query_name in q
                    and title_name in title
                ):
                    programme_results.append(result)
                    break

        # -----------------------------------------------------
        # If we found an exact programme document, use only
        # those documents.
        # -----------------------------------------------------

        if programme_results:
            return programme_results

    # ---------------------------------------------------------
    # No deterministic programme match.
    #
    # Keep the best retrieval result(s), but don't flood the
    # LLM with the entire candidate set.
    # ---------------------------------------------------------

    return results[: min(len(results), 3)]


def _build_sources(
    results,
) -> list[dict]:

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

    return sources


# =============================================================
# Main answer function
# =============================================================

def answer_question(
    question: str,
    *,
    limit: int = 5,
    category: str | None = None,
    subcategory: str | None = None,
) -> dict:

    # ---------------------------------------------------------
    # Validate
    # ---------------------------------------------------------

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    # ---------------------------------------------------------
    # Understand query
    # ---------------------------------------------------------

    understanding = understand_query(
        question
    )

    # Explicit API filters override automatic filters.
    effective_category = (
        category
        if category is not None
        else understanding.category
    )

    effective_subcategory = (
        subcategory
        if subcategory is not None
        else understanding.subcategory
    )

    # ---------------------------------------------------------
    # Hybrid retrieval
    # ---------------------------------------------------------

    results = hybrid_search(
        understanding.search_query,
        limit=limit,
        category=effective_category,
        subcategory=effective_subcategory,
    )

    # ---------------------------------------------------------
    # Relevance filtering
    # ---------------------------------------------------------

    relevant_results = _filter_relevant_results(
        question,
        results,
    )

    # ---------------------------------------------------------
    # Build context
    # ---------------------------------------------------------

    context = build_context(
        relevant_results
    )

    # ---------------------------------------------------------
    # No useful context
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

The API will provide source documents
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
    # Sources should match the context sent to the LLM
    # ---------------------------------------------------------

    sources = _build_sources(
        relevant_results
    )

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return {
        "answer": answer,
        "sources": sources,
        "results": relevant_results,
    }