from app.llm.factory import get_llm
from app.rag.context import build_context
from app.retrieval.hybrid import hybrid_search
from app.query.understanding import understand_query


SYSTEM_PROMPT = """
You are a sales knowledge assistant for Regenesys.

Answer the user's question using ONLY the information
provided in the retrieved knowledge-base context and
relevant conversation history.

Rules:

1. Do not invent information.
2. Do not use outside knowledge.
3. If the answer is not supported by the knowledge base,
   say:
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
12. Conversation history may be used to resolve references
    such as "it", "its", "that programme", or "the course".
13. Conversation history must never be treated as factual
    knowledge. The retrieved knowledge base is the source
    of truth.
""".strip()


KNOWN_PROGRAMMES = {
    "mba": "MBA",
    "bba": "BBA",
    "dbm": "DBM",
    "pdbm": "PDBM",
    "hcbm": "HCBM",
    "pgpm": "PGPM",
    "pgdm": "PGDM",
    "pdds": "PDDS",
    "bsc": "BSC",
    "bitid": "BITID",
    "hcss": "HCSS",
}


def _build_history(
    conversation_history: list[dict] | None,
) -> str:

    if not conversation_history:
        return ""

    lines = []

    for message in conversation_history:

        role = message.get(
            "role",
            "",
        )

        content = message.get(
            "content",
            "",
        ).strip()

        if not content:
            continue

        lines.append(
            f"{role.upper()}: {content}"
        )

    return "\n".join(lines)


def _find_programme_in_history(
    conversation_history: list[dict] | None,
) -> str | None:

    if not conversation_history:
        return None

    # Search recent messages first.
    for message in reversed(
        conversation_history
    ):

        content = message.get(
            "content",
            "",
        ).lower()

        for key, programme in KNOWN_PROGRAMMES.items():

            if key in content:
                return programme

    return None


def _resolve_search_query(
    question: str,
    conversation_history: list[dict] | None,
) -> str:

    """
    Resolve simple conversational references.

    Examples:

        What is the MBA?
        What is its duration?

    becomes:

        What is the duration of the MBA?

    We first use deterministic programme detection.
    LLM resolution is only used when no programme can
    be identified from the recent conversation.
    """

    if not conversation_history:
        return question

    history = _build_history(
        conversation_history
    )

    if not history:
        return question

    programme = _find_programme_in_history(
        conversation_history
    )

    if programme:

        normalized = " ".join(
            question.lower().split()
        )

        reference_words = [
            "it",
            "its",
            "they",
            "their",
            "this",
            "that",
            "this programme",
            "that programme",
            "the programme",
            "this course",
            "that course",
            "the course",
        ]

        has_reference = any(
            word in normalized
            for word in reference_words
        )

        if has_reference:

            resolved = question

            replacements = {
                "its": f"the {programme}'s",
                "it": f"the {programme}",
                "their": f"the {programme}'s",
                "they": f"the {programme}",
                "this programme": f"the {programme}",
                "that programme": f"the {programme}",
                "the programme": f"the {programme}",
                "this course": f"the {programme}",
                "that course": f"the {programme}",
                "the course": f"the {programme}",
                "this": f"the {programme}",
                "that": f"the {programme}",
            }

            # Longest phrases first.
            for old, new in sorted(
                replacements.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            ):

                if old in normalized:

                    resolved = normalized.replace(
                        old,
                        new,
                    )

                    break

            return resolved

    # ---------------------------------------------------------
    # Fallback LLM resolution
    # ---------------------------------------------------------

    llm = get_llm()

    prompt = f"""
Conversation history:

{history}

Current user question:

{question}

Rewrite the current question as a standalone
knowledge-base search query.

Resolve conversational references such as:
- it
- its
- they
- their
- this
- that
- this programme
- that programme
- the course

Use conversation history only to determine what
the user is referring to.

Do not answer the question.

Return ONLY the rewritten search query.
""".strip()

    try:

        resolved = llm.generate(
            system_prompt=(
                "You rewrite conversational questions "
                "into standalone search queries."
            ),
            user_prompt=prompt,
        )

        resolved = resolved.strip()

        if resolved:
            return resolved

    except Exception as exc:

        print(
            "QUERY RESOLUTION ERROR:",
            repr(exc),
        )

    return question


def answer_question(
    question: str,
    *,
    limit: int = 5,
    category: str | None = None,
    subcategory: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    # ---------------------------------------------------------
    # Resolve conversation
    # ---------------------------------------------------------

    search_query = _resolve_search_query(
        question,
        conversation_history,
    )

    print(
        "SEARCH QUERY:",
        search_query,
    )

    # ---------------------------------------------------------
    # Understand query
    # ---------------------------------------------------------

    understanding = understand_query(
        search_query
    )

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
    # Retrieve
    # ---------------------------------------------------------

    results = hybrid_search(
        understanding.search_query,
        limit=limit,
        entity=understanding.entity,
        category=effective_category,
        subcategory=effective_subcategory,
    )

    # ---------------------------------------------------------
    # Context
    # ---------------------------------------------------------

    context = build_context(
        results
    )

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
    # History
    # ---------------------------------------------------------

    history_text = _build_history(
        conversation_history
    )

    history_section = ""

    if history_text:

        history_section = (
            "\n\nConversation history:\n\n"
            + history_text
        )

    # ---------------------------------------------------------
    # Prompt
    # ---------------------------------------------------------

    user_prompt = f"""
Retrieved knowledge-base context:

{context}

{history_section}

Current user question:

{question}

Resolved search query:

{search_query}

Answer the current question using ONLY the
retrieved knowledge-base context.

Conversation history may be used only to understand
what the user is referring to.

Do not use outside knowledge.

Do not add source numbers, source markers,
citations, or references.

The API provides source documents separately.

If the retrieved context does not contain enough
information to answer the question, say:

"I couldn't find that information in the knowledge base."
""".strip()

    # ---------------------------------------------------------
    # Generate
    # ---------------------------------------------------------

    llm = get_llm()

    answer = llm.generate(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # ---------------------------------------------------------
    # Sources
    # ---------------------------------------------------------

    sources = []

    seen = set()

    for result in results:

        # For programme-specific fact questions,
        # prefer documents whose title matches the
        # resolved entity.
        if understanding.entity:
            entity = understanding.entity.lower()

            title = (
                result.title or ""
            ).lower()

            entity_matches = (
                entity in title
                or (
                    entity == "mba"
                    and "master of business administration" in title
                )
                or (
                    entity == "bba"
                    and "bachelor of business administration" in title
                )
                or (
                    entity == "dbm"
                    and "doctor of business management" in title
                )
            )

            if (
                understanding.intent
                in {
                    "duration_lookup",
                    "fee_lookup",
                    "eligibility_lookup",
                    "fact_lookup",
                }
                and not entity_matches
            ):
                continue

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

    return {
        "answer": answer,
        "sources": sources,
        "results": results,
    }
