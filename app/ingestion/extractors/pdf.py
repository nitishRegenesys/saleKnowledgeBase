from pathlib import Path

from pypdf import PdfReader


def extract_pdf(path: str | Path) -> dict:
    path = Path(path)

    reader = PdfReader(path)

    pages = []

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        pages.append(
            {
                "page_number": index + 1,
                "text": text.strip(),
            }
        )

    full_text = "\n\n".join(
        page["text"]
        for page in pages
        if page["text"]
    )

    return {
        "text": full_text,
        "title": path.stem,
        "metadata": {
            "page_count": len(reader.pages),
            "pages": pages,
        },
    }
