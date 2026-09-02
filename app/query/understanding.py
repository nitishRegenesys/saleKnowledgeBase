from dataclasses import dataclass


@dataclass
class QueryUnderstanding:
    original_query: str
    search_query: str

    intent: str

    entity: str | None = None
    attribute: str | None = None

    category: str | None = None
    subcategory: str | None = None


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


def _detect_entity(
    normalized: str,
) -> str | None:

    for key, value in KNOWN_PROGRAMMES.items():

        if key in normalized:
            return value

    if "business school" in normalized:
        return "business school"

    if "school of ai" in normalized:
        return "school of ai"

    return None


def understand_query(
    question: str,
) -> QueryUnderstanding:

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    normalized = " ".join(
        question.lower().split()
    )

    entity = _detect_entity(
        normalized
    )

    # ---------------------------------------------------------
    # Business School programme list
    # ---------------------------------------------------------

    if (
        entity == "business school"
        and (
            "what programmes" in normalized
            or "which programmes" in normalized
            or "programmes are available" in normalized
            or "programs are available" in normalized
            or "programmes available" in normalized
            or "programs available" in normalized
        )
    ):

        return QueryUnderstanding(
            original_query=question,
            search_query="business school programmes",
            intent="programme_list",
            entity="business school",
            category="education",
            subcategory="business school",
        )

    # ---------------------------------------------------------
    # School of AI programme list
    # ---------------------------------------------------------

    if (
        entity == "school of ai"
        and (
            "what programmes" in normalized
            or "which programmes" in normalized
            or "programmes are available" in normalized
            or "programmes available" in normalized
            or "programs available" in normalized
            or "programs are available" in normalized
        )
    ):

        return QueryUnderstanding(
            original_query=question,
            search_query="school of ai programmes",
            intent="programme_list",
            entity="school of ai",
            category="school_of_ai",
        )

    # ---------------------------------------------------------
    # NQF
    # ---------------------------------------------------------

    if (
        "nqf" in normalized
        or "qualification level" in normalized
    ):

        search_query = question

        if entity:
            search_query = (
                f"{entity} NQF level"
            )

        return QueryUnderstanding(
            original_query=question,
            search_query=search_query,
            intent="fact_lookup",
            entity=entity,
            attribute="nqf_level",
        )

    # ---------------------------------------------------------
    # Fees
    # ---------------------------------------------------------

    if any(
        word in normalized
        for word in [
            "fee",
            "fees",
            "cost",
            "price",
            "tuition",
        ]
    ):

        search_query = question

        if entity:
            search_query = (
                f"{entity} fees"
            )

        return QueryUnderstanding(
            original_query=question,
            search_query=search_query,
            intent="fee_lookup",
            entity=entity,
            attribute="fees",
        )

    # ---------------------------------------------------------
    # Eligibility / admission
    # ---------------------------------------------------------

    if any(
        phrase in normalized
        for phrase in [
            "eligibility",
            "eligible",
            "admission requirement",
            "admission requirements",
            "entry requirement",
            "entry requirements",
            "requirements",
        ]
    ):

        search_query = question

        if entity:
            search_query = (
                f"{entity} eligibility requirements"
            )

        return QueryUnderstanding(
            original_query=question,
            search_query=search_query,
            intent="eligibility_lookup",
            entity=entity,
            attribute="eligibility",
        )

    # ---------------------------------------------------------
    # Duration
    # ---------------------------------------------------------

    if any(
        phrase in normalized
        for phrase in [
            "duration",
            "how long",
            "length",
        ]
    ):

        search_query = question

        if entity:
            search_query = (
                f"{entity} duration"
            )

        return QueryUnderstanding(
            original_query=question,
            search_query=search_query,
            intent="duration_lookup",
            entity=entity,
            attribute="duration",
        )

    # ---------------------------------------------------------
    # Credits
    # ---------------------------------------------------------

    if any(
        word in normalized
        for word in [
            "credit",
            "credits",
        ]
    ):

        search_query = question

        if entity:
            search_query = (
                f"{entity} credits"
            )

        return QueryUnderstanding(
            original_query=question,
            search_query=search_query,
            intent="fact_lookup",
            entity=entity,
            attribute="credits",
        )

    # ---------------------------------------------------------
    # Programme list
    # ---------------------------------------------------------

    if (
        "what programmes" in normalized
        or "which programmes" in normalized
        or "programmes available" in normalized
        or "programs available" in normalized
        or "what programs" in normalized
        or "which programs" in normalized
    ):

        return QueryUnderstanding(
            original_query=question,
            search_query=question,
            intent="programme_list",
            entity=entity,
        )

    # ---------------------------------------------------------
    # General programme/entity question
    # ---------------------------------------------------------

    return QueryUnderstanding(
        original_query=question,
        search_query=question,
        intent="general",
        entity=entity,
    )