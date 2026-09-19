from pathlib import Path

import requests

SP500_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
    "master/data/constituents.csv"
)
OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "reference" / "sp500.csv"


def fetch() -> None:
    response = requests.get(SP500_CSV_URL, timeout=15)
    response.raise_for_status()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(response.text)
    line_count = response.text.count("\n")
    print(f"Saved {line_count} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    fetch()
