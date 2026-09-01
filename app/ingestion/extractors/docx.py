from pathlib import Path

from docx import Document as DocxDocument


def extract_docx(path: str | Path) -> dict:
    path = Path(path)

    document = DocxDocument(path)

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    text = "\n\n".join(paragraphs)

    return {
        "text": text,
        "title": path.stem,
        "metadata": {
            "paragraph_count": len(paragraphs),
        },
    }
