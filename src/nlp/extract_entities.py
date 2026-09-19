import sys
from pathlib import Path

import spacy

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.reference.company_lookup import resolve_ticker
from src.storage.db import get_connection, get_unprocessed_articles, insert_entity, mark_processed

nlp = spacy.load("en_core_web_sm")

MAX_ENTITY_WORDS = 5  # longer ORG spans are usually headline-fragment misfires, not company names


def extract_orgs(text: str) -> set[str]:
    doc = nlp(text)
    return {
        ent.text
        for ent in doc.ents
        if ent.label_ == "ORG" and len(ent.text.split()) <= MAX_ENTITY_WORDS
    }


def run_once() -> None:
    conn = get_connection()
    articles = get_unprocessed_articles(conn)
    total_entities = 0
    total_resolved = 0

    for article in articles:
        text = f"{article['title']} {article['summary'] or ''}"
        orgs = extract_orgs(text)

        for org in orgs:
            ticker = resolve_ticker(org)
            insert_entity(conn, article["id"], org, ticker)
            total_entities += 1
            total_resolved += ticker is not None

        mark_processed(conn, article["id"])

    conn.commit()
    conn.close()
    print(
        f"Processed {len(articles)} articles: "
        f"{total_entities} entities found, {total_resolved} resolved to a ticker."
    )


if __name__ == "__main__":
    run_once()
