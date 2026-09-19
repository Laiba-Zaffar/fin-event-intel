import statistics
import sys
import time
from pathlib import Path

from transformers import pipeline

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.nlp.event_labels import EVENT_LABELS
from src.storage.db import get_connection, get_unclassified_articles, store_classification

MODEL_NAME = "valhalla/distilbart-mnli-12-3"


def run_once() -> None:
    classifier = pipeline("zero-shot-classification", model=MODEL_NAME)

    conn = get_connection()
    articles = get_unclassified_articles(conn)
    latencies_ms = []

    for article in articles:
        text = f"{article['title']} {article['summary'] or ''}".strip()

        start = time.perf_counter()
        result = classifier(text, candidate_labels=EVENT_LABELS)
        latencies_ms.append((time.perf_counter() - start) * 1000)

        top_label = result["labels"][0]
        top_score = result["scores"][0]
        store_classification(conn, article["id"], top_label, top_score)

    conn.commit()
    conn.close()

    if latencies_ms:
        print(
            f"Classified {len(articles)} articles using {MODEL_NAME}.\n"
            f"Latency (ms) — mean: {statistics.mean(latencies_ms):.1f}, "
            f"p50: {statistics.median(latencies_ms):.1f}, "
            f"max: {max(latencies_ms):.1f}"
        )
    else:
        print("No unclassified articles found.")


if __name__ == "__main__":
    run_once()
