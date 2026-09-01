from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.classifier import classify_document
from app.ingestion.persistence import save_document
from app.ingestion.service import ExtractedDocument


CRAWL_ROOT = Path(
    "../universal-web-scraper/regaicademy-full/pages"
)


def load_page(page_path: Path) -> ExtractedDocument:
    data = json.loads(
        page_path.read_text(
            encoding="utf-8"
        )
    )

    text = data.get("text", "").strip()

    if not text:
        raise ValueError(
            f"No text found in {page_path}"
        )

    title = data.get("title") or page_path.stem
    url = data.get("url")

    classification = classify_document(
        url=url,
        title=title,
    )

    # page.json does not contain the original file hash,
    # so use the extracted text as the ingestion identity.
    import hashlib

    content_hash = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    metadata = {
        "crawler": "universal-web-scraper",
        "page_json": str(page_path),
        "content_file": str(
            page_path.parent / "content.txt"
        ),
        "final_url": data.get("final_url"),
        "crawl_depth": data.get("depth"),
        "headings": data.get("headings", []),
        "discovered_links": data.get(
            "discovered_links",
            [],
        ),
        "discovered_embeds": data.get(
            "discovered_embeds",
            [],
        ),
        "google_slides_ids": data.get(
            "google_slides_ids",
            [],
        ),
    }

    return ExtractedDocument(
        filename=page_path.parent.name,
        title=title,
        text=text,
        source_type="project1_scraper",
        mime_type="text/html",
        source_url=url,
        file_path=str(
            page_path.parent / "content.txt"
        ),
        content_hash=content_hash,
        category=classification["category"],
        subcategory=classification["subcategory"],
        metadata=metadata,
    )


def ingest_all():
    if not CRAWL_ROOT.exists():
        raise FileNotFoundError(
            f"Crawl directory not found: {CRAWL_ROOT}"
        )

    pages = sorted(
        CRAWL_ROOT.glob("*/page.json")
    )

    print("=" * 80)
    print("BULK INGESTION")
    print("=" * 80)
    print("SOURCE:", CRAWL_ROOT)
    print("PAGES FOUND:", len(pages))
    print()

    inserted = 0
    skipped = 0
    failed = 0

    for index, page_path in enumerate(
        pages,
        start=1,
    ):
        try:
            extracted = load_page(page_path)

            ""

            document, created = save_document(
                extracted
            )

            if created:
                inserted += 1
                status = "INSERTED"
            else:
                skipped += 1
                status = "EXISTS"

            print(
                f"[{index:02d}/{len(pages):02d}] "
                f"{status:8} | "
                f"{extracted.category:20} | "
                f"{extracted.title}"
            )

            """"""

        except ValueError as exc:
            skipped += 1

            print(
                f"[{index:02d}/{len(pages):02d}] "
                f"SKIP | {exc}"
            )

        except Exception as exc:
            failed += 1

            print(
                f"[{index:02d}/{len(pages):02d}] "
                f"FAILED | "
                f"{page_path.name} | "
                f"{type(exc).__name__}: {exc}"
            )

    print()
    print("=" * 80)
    print("BULK INGESTION COMPLETE")
    print("=" * 80)
    print("PAGES:", len(pages))
    print("PROCESSED:", inserted)
    print("SKIPPED:", skipped)
    print("FAILED:", failed)


if __name__ == "__main__":
    ingest_all()