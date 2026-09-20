import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.nlp import extract_entities


def make_fake_doc(entities):
    doc = MagicMock()
    doc.ents = [MagicMock(text=text, label_=label) for text, label in entities]
    return doc


def test_extract_orgs_filters_non_org_entities():
    fake_doc = make_fake_doc([("Apple", "ORG"), ("Paris", "GPE")])
    with patch.object(extract_entities, "nlp", return_value=fake_doc):
        assert extract_entities.extract_orgs("some text") == {"Apple"}


def test_extract_orgs_filters_long_spans():
    # Regression test for the headline-fragment misfire found in M2
    # ("Marsh & McLennan Stock Underperforming" tagged as one ORG span).
    fake_doc = make_fake_doc(
        [
            ("Apple", "ORG"),
            ("Marsh & McLennan Stock Underperforming Badly", "ORG"),  # 6 words, over the cap
        ]
    )
    with patch.object(extract_entities, "nlp", return_value=fake_doc):
        assert extract_entities.extract_orgs("some text") == {"Apple"}
