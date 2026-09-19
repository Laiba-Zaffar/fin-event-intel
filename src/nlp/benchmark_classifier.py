import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.nlp.event_labels import EVENT_LABELS
from src.nlp.model import build_classifier
from src.storage.db import get_connection

SAMPLE_SIZE = 4


def get_sample_texts() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT title, summary FROM articles ORDER BY id DESC LIMIT ?", (SAMPLE_SIZE,)
    ).fetchall()
    conn.close()
    return [f"{title} {summary or ''}".strip() for title, summary in rows]


def summarize(name: str, latencies_ms: list[float]) -> None:
    print(
        f"{name:<28} mean {statistics.mean(latencies_ms):7.1f}ms  "
        f"p50 {statistics.median(latencies_ms):7.1f}ms  "
        f"max {max(latencies_ms):7.1f}ms"
    )


def run(mode: str) -> None:
    texts = get_sample_texts()
    print(f"Mode: {mode} | {len(texts)} articles, {len(EVENT_LABELS)} candidate labels")

    quantized = mode.startswith("quantized")
    classifier = build_classifier(quantized=quantized)

    if mode.endswith("batched"):
        start = time.perf_counter()
        classifier(texts, candidate_labels=EVENT_LABELS, batch_size=4)
        total_ms = (time.perf_counter() - start) * 1000
        print(f"total {total_ms:7.1f}ms  per-article avg {total_ms / len(texts):7.1f}ms")
    else:
        latencies = []
        for text in texts:
            start = time.perf_counter()
            classifier(text, candidate_labels=EVENT_LABELS)
            latencies.append((time.perf_counter() - start) * 1000)
        summarize(mode, latencies)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["baseline", "batched", "quantized", "quantized_batched"],
        required=True,
    )
    args = parser.parse_args()
    run(args.mode)
