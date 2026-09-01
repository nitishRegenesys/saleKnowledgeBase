import json
from pathlib import Path

from app.ingestion.service import ExtractedDocument
from app.ingestion.classifier import classify_document
from app.ingestion.chunker import normalize_text
from app.ingestion.service import calculate_file_hash


def load_project1_page(
    page_dir: str | Path,
) -> ExtractedDocument:

    page_dir = Path(page_dir)

    content_path = page_dir / "content.txt"
    page_json_path = page_dir / "page.json"

    if not content_path.exists():
        raise FileNotFoundError(
            content_path
        )

    if not page_json_path.exists():
        raise FileNotFoundError(
            page_json_path
        )

    text = content_path.read_text(
        encoding="utf-8"
    )

    text = normalize_text(text)

    if not text:
        raise ValueError(
            f"No text in {content_path}"
        )

    page_data = json.loads(
        page_json_path.read_text(
            encoding="utf-8"
        )
    )

    title = (
        page_data.get("title")
        or page_dir.name
    )

    classification = classify_document(
        title=title,
        text=text,
    )

    return ExtractedDocument(
        filename=content_path.name,
        title=title,
        text=text,
        source_type="project1_scraper",
        mime_type="text/plain",
        source_url=(
            page_data.get("final_url")
            or page_data.get("url")
        ),
        file_path=str(content_path),
        content_hash=calculate_file_hash(
            content_path
        ),
        category=classification.category,
        subcategory=classification.subcategory,
        metadata={
            "project1_page_dir": str(page_dir),
            "crawl_depth": page_data.get(
                "depth"
            ),
            "crawled_at": page_data.get(
                "crawled_at"
            ),
            "headings": page_data.get(
                "headings",
                [],
            ),
            "discovered_links": page_data.get(
                "discovered_links",
                [],
            ),
            "discovered_images": page_data.get(
                "discovered_images",
                [],
            ),
            "discovered_embeds": page_data.get(
                "discovered_embeds",
                [],
            ),
        },
    )
