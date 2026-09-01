from pathlib import Path

import pandas as pd


def extract_text(path: str | Path) -> dict:
    path = Path(path)

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    return {
        "text": text.strip(),
        "title": path.stem,
        "metadata": {},
    }


def extract_csv(path: str | Path) -> dict:
    path = Path(path)

    dataframe = pd.read_csv(path)

    text = dataframe.to_csv(
        index=False,
    )

    return {
        "text": text.strip(),
        "title": path.stem,
        "metadata": {
            "row_count": len(dataframe),
            "column_count": len(dataframe.columns),
            "columns": list(dataframe.columns),
        },
    }
