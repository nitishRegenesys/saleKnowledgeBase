from app.retrieval.hybrid import RetrievedChunk


def build_context(
    results: list[RetrievedChunk],
) -> str:
    """
    Convert retrieved chunks into structured context
    for the LLM.
    """

    if not results:
        return ""

    sections = []

    for index, result in enumerate(results, 1):

        sections.append(
            f"""
SOURCE {index}
Title: {result.title}
URL: {result.source_url or "N/A"}
Category: {result.category}
Subcategory: {result.subcategory or "N/A"}

Content:
{result.content}
""".strip()
        )

    return "\n\n".join(sections)