from pathlib import Path

from bs4 import BeautifulSoup


def extract_html(path: str | Path) -> dict:
    path = Path(path)

    html = path.read_bytes()

    soup = BeautifulSoup(html, "lxml")

    title = None

    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True,
        )

    for tag in soup(
        ["script", "style", "noscript", "template"]
    ):
        tag.decompose()

    text = soup.get_text(
        "\n",
        strip=True,
    )

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    text = "\n".join(lines)

    return {
        "text": text,
        "title": title or path.stem,
        "metadata": {},
    }
