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
14. If the resolved subject is clear from the conversation,
    retrieve information specifically about that subject.
""".strip()


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

    if not lines:
        return ""

    return "\n".join(lines)


def _resolve_search_query(
    question: str,
    conversation_history: list[dict] | None,
) -> str:

    """
    Resolve conversational references before retrieval.

    Example:

        Previous:
            USER: What is the MBA?

        Current:
            What is its duration?

    Becomes approximately:

        What is the duration of the MBA?
    """

    if not conversation_history:
        return question

    history = _build_history(
        conversation_history
    )

    if not history:
        return question

    llm = get_llm()

    prompt = f"""
Conversation history:

{history}

Current user question:

{question}

Determine the standalone search query needed to retrieve
the correct information from a knowledge base.

Resolve references such as:
- it
- its
- they
- their
- that
- this
- that programme
- this programme
- the course

Use the conversation history only to resolve what the user
is referring to.

Do not answer the question.

Return ONLY the rewritten standalone search query.

Example:

Conversation:
USER: What is the MBA?
ASSISTANT: The MBA is an NQF Level 9 programme.

Current question:
What is its duration?

Return:
What is the duration of the MBA?
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

    # ---------------------------------------------------------
    # Validate
    # ---------------------------------------------------------

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    # ---------------------------------------------------------
    # Resolve conversational references
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
    # Query understanding
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
    # Retrieval
    # ---------------------------------------------------------

    results = hybrid_search(
        understanding.search_query,
        limit=limit,
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
    # Conversation history
    # ---------------------------------------------------------

    history_text = _build_history(
        conversation_history
    )

    if history_text:

        history_section = (
            "\n\nConversation history:\n\n"
            + history_text
        )

    else:

        history_section = ""

    # ---------------------------------------------------------
    # LLM prompt
    # ---------------------------------------------------------

    user_prompt = f"""
Retrieved knowledge-base context:

{context}

{history_section}

Current user question:

{question}

Resolved search query:

{search_query}

Answer the current user question using ONLY the
retrieved knowledge-base context.

Conversation history may be used to understand what
the user is referring to.

Do not use outside knowledge.

Do not add source numbers, source markers,
citations, or references such as [Source 1],
【Source 1】, or (Source 1).

The API provides source documents separately.

If the retrieved context does not contain enough
information to answer the question, say:

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
    # Sources
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
    # Return
    # ---------------------------------------------------------

    return {
        "answer": answer,
        "sources": sources,
        "results": results,
    }