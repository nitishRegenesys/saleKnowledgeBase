from app.ingestion.classifier import classify_document
from app.ingestion.chunker import normalize_text
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path


@dataclass
class ExtractedDocument:
    filename: str
    title: str
    text: str

    source_type: str
    mime_type: str | None = None
    source_url: str | None = None
    file_path: str | None = None

    content_hash: str = ""

    category: str = "general"
    subcategory: str | None = None

    metadata: dict = field(default_factory=dict)


def calculate_file_hash(path: str | Path) -> str:
    path = Path(path)

    digest = sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def ingest_file(
    path: str | Path,
    *,
    source_type: str = "upload",
    source_url: str | None = None,
) -> ExtractedDocument:

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    from app.ingestion.extractors.registry import get_extractor

    extractor = get_extractor(path)

    result = extractor(path)

    text = result.get("text", "").strip()

    if not text:
        raise ValueError(
            f"No text could be extracted from: {path.name}"
        )

    text = normalize_text(text)

    classification = classify_document(
        title=title,
        text=text,
    )


    title = result.get("title") or path.stem

    content_hash = calculate_file_hash(path)

    from app.ingestion.classifier import classify_document

    classification = classify_document(
        url=source_url,
        title=title,
    )

    metadata = {
        **result.get("metadata", {}),
        **classification,
    }

    return ExtractedDocument(
        filename=path.name,
        title=title,
        text=text,
        source_type=source_type,
        source_url=source_url,
        file_path=str(path),
        content_hash=content_hash,
        category=classification["category"],
        subcategory=classification["subcategory"],
        metadata=metadata,
    )
