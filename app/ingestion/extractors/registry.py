from pathlib import Path
from typing import Callable

from app.ingestion.extractors.pdf import extract_pdf
from app.ingestion.extractors.docx import extract_docx
from app.ingestion.extractors.pptx import extract_pptx
from app.ingestion.extractors.xlsx import extract_xlsx
from app.ingestion.extractors.html import extract_html
from app.ingestion.extractors.text import extract_text, extract_csv


Extractor = Callable[[str | Path], dict]


EXTRACTORS: dict[str, Extractor] = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
    ".xlsx": extract_xlsx,
    ".html": extract_html,
    ".htm": extract_html,
    ".txt": extract_text,
    ".csv": extract_csv,
}


def get_extractor(path: str | Path) -> Extractor:
    path = Path(path)

    suffix = path.suffix.lower()

    extractor = EXTRACTORS.get(suffix)

    if extractor is None:
        raise ValueError(
            f"Unsupported file type: {suffix or '[no extension]'}"
        )

    return extractor
