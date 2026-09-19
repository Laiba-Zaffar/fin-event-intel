import statistics
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.nlp.event_labels import EVENT_LABELS
from src.nlp.model import build_classifier
from src.storage.db import get_connection, get_unclassified_articles, store_classification

BATCH_SIZE = 8


def run_once() -> None:
    conn = get_connection()
    articles = get_unclassified_articles(conn)

    if not articles:
        print("No unclassified articles found.")
        conn.close()
        return

    classifier = build_classifier(quantized=False)
    texts = [f"{a['title']} {a['summary'] or ''}".strip() for a in articles]

    start = time.perf_counter()
    results = classifier(texts, candidate_labels=EVENT_LABELS, batch_size=BATCH_SIZE)
    total_ms = (time.perf_counter() - start) * 1000

    if isinstance(results, dict):  # pipeline returns a single dict for one input
        results = [results]

    for article, result in zip(articles, results):
        store_classification(conn, article["id"], result["labels"][0], result["scores"][0])

    conn.commit()
    conn.close()

    per_article_ms = total_ms / len(articles)
    print(
        f"Classified {len(articles)} articles (fp32 model, batch_size={BATCH_SIZE}).\n"
        f"Total: {total_ms / 1000:.1f}s, avg per article: {per_article_ms:.0f}ms"
    )


if __name__ == "__main__":
    run_once()
