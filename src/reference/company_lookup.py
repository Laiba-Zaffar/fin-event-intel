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
def load_lookup() -> tuple[dict[str, str], dict[str, str]]:
    name_lookup = {}
    ticker_lookup = {}
    with open(SP500_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = normalize(row["Security"])
            if key:
                name_lookup[key] = row["Symbol"]
            ticker_lookup[row["Symbol"]] = row["Symbol"]
    return name_lookup, ticker_lookup


def resolve_ticker(entity_text: str) -> str | None:
    name_lookup, ticker_lookup = load_lookup()
    stripped = entity_text.strip()

    # spaCy sometimes tags the raw ticker itself (e.g. "AMD") as the ORG span.
    # Case-sensitive on purpose - matching lowercase/mixed-case text against
    # a ticker would turn any ordinary word that happens to collide with a
    # real symbol into a false positive (this used to be broken: the old
    # lookup stored tickers lowercase in the same dict as company names, so
    # the "uppercase only" check below never actually mattered).
    if stripped.isupper() and stripped.isalpha():
        hit = ticker_lookup.get(stripped)
        if hit:
            return hit

    return name_lookup.get(normalize(entity_text))
