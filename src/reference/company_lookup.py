import csv
import re
from functools import lru_cache
from pathlib import Path

SP500_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "reference" / "sp500.csv"

SUFFIX_PATTERN = re.compile(
    r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|group|holdings|the)\b\.?",
    re.IGNORECASE,
)


def normalize(name: str) -> str:
    name = SUFFIX_PATTERN.sub("", name)
    name = re.sub(r"[^a-z0-9 ]", "", name.lower())
    return re.sub(r"\s+", " ", name).strip()


@lru_cache(maxsize=1)
def load_lookup() -> dict[str, str]:
    lookup = {}
    with open(SP500_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = normalize(row["Security"])
            if key:
                lookup[key] = row["Symbol"]
            lookup[row["Symbol"].lower()] = row["Symbol"]
    return lookup


def resolve_ticker(entity_text: str) -> str | None:
    lookup = load_lookup()
    # spaCy sometimes tags the raw ticker itself (e.g. "AMD") as the ORG span
    if entity_text.strip().upper() == entity_text.strip() and entity_text.strip().isalpha():
        hit = lookup.get(entity_text.strip().lower())
        if hit:
            return hit
    return lookup.get(normalize(entity_text))
