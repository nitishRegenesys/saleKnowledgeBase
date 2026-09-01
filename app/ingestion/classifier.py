from __future__ import annotations

import re
from urllib.parse import urlparse


def _slug_to_text(value: str) -> str:
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def classify_url(
    url: str | None,
    title: str | None = None,
) -> tuple[str, str | None]:
    """
    Classify a Regenesys/RegAIcademy URL.

    Returns:
        (category, subcategory)
    """

    if not url:
        return "general", None

    path = urlparse(url).path.strip("/").lower()
    parts = [
        part
        for part in path.split("/")
        if part
    ]

    if not parts:
        return "general", None

    # ---------------------------------------------------------
    # Digital Regenesys
    # ---------------------------------------------------------

    if "digital-regenesys" in parts:
        index = parts.index("digital-regenesys")

        subcategory = (
            parts[index + 1]
            if len(parts) > index + 1
            else None
        )

        return (
            "digital_regenesys",
            _slug_to_text(subcategory)
            if subcategory
            else None,
        )

    # ---------------------------------------------------------
    # School of AI
    # ---------------------------------------------------------

    if "school-of-ai" in parts:
        index = parts.index("school-of-ai")

        subcategory = (
            parts[index + 1]
            if len(parts) > index + 1
            else None
        )

        return (
            "school_of_ai",
            _slug_to_text(subcategory)
            if subcategory
            else None,
        )

    # ---------------------------------------------------------
    # Sales Support
    # ---------------------------------------------------------

    if "sales-support" in parts:
        index = parts.index("sales-support")

        subcategory = (
            parts[index + 1]
            if len(parts) > index + 1
            else None
        )

        return (
            "sales_support",
            _slug_to_text(subcategory)
            if subcategory
            else None,
        )

    # ---------------------------------------------------------
    # CRM
    # ---------------------------------------------------------

    if "crm" in parts:
        index = parts.index("crm")

        subcategory = (
            parts[index + 1]
            if len(parts) > index + 1
            else None
        )

        return (
            "crm",
            _slug_to_text(subcategory)
            if subcategory
            else None,
        )

    # ---------------------------------------------------------
    # NQF
    # ---------------------------------------------------------

    if "nqf-level" in parts:
        index = parts.index("nqf-level")

        subcategory = (
            parts[index + 1]
            if len(parts) > index + 1
            else None
        )

        return (
            "nqf_level",
            _slug_to_text(subcategory)
            if subcategory
            else None,
        )

    # ---------------------------------------------------------
    # FLEXI
    # ---------------------------------------------------------

    if "flexi" in parts:
        index = parts.index("flexi")

        subcategory = (
            parts[index + 1]
            if len(parts) > index + 1
            else None
        )

        return (
            "flexi",
            _slug_to_text(subcategory)
            if subcategory
            else None,
        )

    # ---------------------------------------------------------
    # Regenesys Education
    # ---------------------------------------------------------

    if "regenesys-education" in parts:
        index = parts.index("regenesys-education")

        subcategory = (
            parts[index + 1]
            if len(parts) > index + 1
            else None
        )

        return (
            "education",
            _slug_to_text(subcategory)
            if subcategory
            else None,
        )

    # ---------------------------------------------------------
    # Homepage / unknown
    # ---------------------------------------------------------

    return "general", None


def classify_document(
    *,
    url: str | None,
    title: str | None,
) -> dict:
    category, subcategory = classify_url(
        url,
        title,
    )

    return {
        "category": category,
        "subcategory": subcategory,
    }