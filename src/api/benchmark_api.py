import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.storage.db import get_connection

BASE_URL = "http://localhost:8000"
N_REQUESTS = 10


def get_sample_articles(n: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT title, summary FROM articles ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [{"title": title, "summary": summary} for title, summary in rows]


def bench_single(client: httpx.Client, articles: list[dict]) -> None:
    latencies_ms = []
    for article in articles:
        start = time.perf_counter()
        resp = client.post(f"{BASE_URL}/classify", json=article, timeout=30)
        resp.raise_for_status()
        latencies_ms.append((time.perf_counter() - start) * 1000)

    latencies_ms.sort()
    p50 = statistics.median(latencies_ms)
    p99 = latencies_ms[min(int(len(latencies_ms) * 0.99), len(latencies_ms) - 1)]
    print(
        f"/classify (single, n={len(articles)}): "
        f"mean {statistics.mean(latencies_ms):.0f}ms  p50 {p50:.0f}ms  "
        f"p99 {p99:.0f}ms  max {max(latencies_ms):.0f}ms"
    )


def bench_batch(client: httpx.Client, articles: list[dict]) -> None:
    start = time.perf_counter()
    resp = client.post(f"{BASE_URL}/classify_batch", json={"articles": articles}, timeout=60)
    resp.raise_for_status()
    total_ms = (time.perf_counter() - start) * 1000
    print(
        f"/classify_batch (n={len(articles)}): "
        f"total {total_ms:.0f}ms  per-article avg {total_ms / len(articles):.0f}ms"
    )


def run() -> None:
    articles = get_sample_articles(N_REQUESTS)
    with httpx.Client() as client:
        health = client.get(f"{BASE_URL}/health", timeout=5).json()
        print(f"Server health: {health}\n")

        bench_single(client, articles)
        bench_batch(client, articles)


if __name__ == "__main__":
    run()
