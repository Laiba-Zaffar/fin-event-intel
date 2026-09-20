import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.reference.company_lookup import normalize, resolve_ticker


def test_normalize_strips_legal_suffixes():
    assert normalize("Apple Inc.") == "apple"
    assert normalize("Tesla, Inc.") == "tesla"
    assert normalize("Microsoft Corporation") == "microsoft"


def test_normalize_lowercases_and_strips_punctuation():
    assert normalize("McDonald's") == "mcdonalds"


def test_resolve_ticker_matches_company_name_with_or_without_suffix():
    assert resolve_ticker("Apple") == "AAPL"
    assert resolve_ticker("Apple Inc.") == "AAPL"
    assert resolve_ticker("Tesla, Inc.") == "TSLA"


def test_resolve_ticker_matches_raw_uppercase_ticker():
    assert resolve_ticker("AMD") == "AMD"


def test_resolve_ticker_ignores_lowercase_and_mixed_case_ticker_lookalikes():
    # Regression test: the ticker-matching path used to be case-insensitive
    # by accident (tickers were stored lowercase in the same dict as company
    # names), so any word that happened to collide with a real ticker symbol
    # - regardless of case - would silently resolve to that ticker.
    assert resolve_ticker("coo") is None
    assert resolve_ticker("Coo") is None


def test_resolve_ticker_returns_none_for_unknown_company():
    assert resolve_ticker("Some Random Startup LLC") is None
