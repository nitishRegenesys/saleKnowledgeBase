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

    # ---------------------------------------------------------
    # Business School programme list
    # ---------------------------------------------------------

    if (
        "business school" in normalized
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
        "school of ai" in normalized
        and (
            "what programmes" in normalized
            or "which programmes" in normalized
            or "programmes are available" in normalized
            or "programmes available" in normalized
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
    # NQF level
    # ---------------------------------------------------------

    if "nqf" in normalized:

        programme = None

        known_programmes = {
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

        for key, value in known_programmes.items():

            if key in normalized:
                programme = value
                break

        if programme:

            return QueryUnderstanding(
                original_query=question,
                search_query=f"{programme} NQF level",
                intent="fact_lookup",
                entity=programme,
                attribute="nqf_level",
            )

        return QueryUnderstanding(
            original_query=question,
            search_query=question,
            intent="fact_lookup",
            attribute="nqf_level",
        )

    # ---------------------------------------------------------
    # Fee questions
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

        return QueryUnderstanding(
            original_query=question,
            search_query=question,
            intent="fee_lookup",
            attribute="fees",
        )

    # ---------------------------------------------------------
    # Eligibility questions
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

        return QueryUnderstanding(
            original_query=question,
            search_query=question,
            intent="eligibility_lookup",
            attribute="eligibility",
        )

    # ---------------------------------------------------------
    # Duration questions
    # ---------------------------------------------------------

    if any(
        word in normalized
        for word in [
            "duration",
            "how long",
            "length",
        ]
    ):

        return QueryUnderstanding(
            original_query=question,
            search_query=question,
            intent="duration_lookup",
            attribute="duration",
        )

    # ---------------------------------------------------------
    # Programme list without known school
    # ---------------------------------------------------------

    if (
        "what programmes" in normalized
        or "which programmes" in normalized
        or "programmes available" in normalized
        or "programs available" in normalized
    ):

        return QueryUnderstanding(
            original_query=question,
            search_query=question,
            intent="programme_list",
        )

    # ---------------------------------------------------------
    # Default
    # ---------------------------------------------------------

    return QueryUnderstanding(
        original_query=question,
        search_query=question,
        intent="general",
    )
