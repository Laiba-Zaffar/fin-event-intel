import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.nlp.event_labels import EVENT_LABELS
from src.nlp.extract_entities import extract_orgs
from src.nlp.model import build_classifier
from src.reference.company_lookup import resolve_ticker
from src.storage.db import get_article, get_connection, insert_entity, mark_processed, store_classification
from src.streaming.config import GROUP_NAME, STREAM_NAME, ensure_group, get_redis_client

BLOCK_MS = 5000  # how long to wait for a new message before giving up
MIN_IDLE_MS = 30_000  # a message pending this long is assumed abandoned by a dead consumer


def process_article(conn, classifier, article_id: int) -> None:
    article = get_article(conn, article_id)
    if article is None:
        return

    text = f"{article['title']} {article['summary'] or ''}".strip()

    for org in extract_orgs(text):
        insert_entity(conn, article_id, org, resolve_ticker(org))
    mark_processed(conn, article_id)

    # Single-item, not batched: a stream consumer's job is low per-item
    # latency as things arrive, not throughput - batching would mean
    # waiting to accumulate a group first, which defeats the point.
    result = classifier(text, candidate_labels=EVENT_LABELS)
    store_classification(conn, article_id, result["labels"][0], result["scores"][0])
    conn.commit()


def reclaim_stale(client, consumer_name: str):
    """Pick up messages another consumer read but never acked (i.e. it crashed
    mid-processing). Without this, that work would just sit lost in another
    consumer's pending list forever - the whole point of a durable queue is
    that a dead worker doesn't mean dropped work."""
    _next_id, claimed, _deleted = client.xautoclaim(
        STREAM_NAME, GROUP_NAME, consumer_name, min_idle_time=MIN_IDLE_MS, start_id="0"
    )
    return claimed


def run(consumer_name: str, max_messages: int | None = None) -> None:
    client = get_redis_client()
    ensure_group(client)
    conn = get_connection()
    classifier = build_classifier(quantized=False)

    processed = 0
    print(f"[{consumer_name}] listening on '{STREAM_NAME}' (group '{GROUP_NAME}')...")

    reclaimed = reclaim_stale(client, consumer_name)
    if reclaimed:
        print(f"[{consumer_name}] reclaiming {len(reclaimed)} stale message(s) from a dead consumer")
        for message_id, fields in reclaimed:
            article_id = int(fields["article_id"])
            process_article(conn, classifier, article_id)
            client.xack(STREAM_NAME, GROUP_NAME, message_id)
            processed += 1
            print(f"[{consumer_name}] article {article_id}: reclaimed and processed, acked {message_id}")

    while max_messages is None or processed < max_messages:
        response = client.xreadgroup(
            GROUP_NAME, consumer_name, {STREAM_NAME: ">"}, count=1, block=BLOCK_MS
        )
        if not response:
            print(f"[{consumer_name}] no new messages, stopping.")
            break

        for _stream_name, entries in response:
            for message_id, fields in entries:
                article_id = int(fields["article_id"])
                start = time.perf_counter()
                process_article(conn, classifier, article_id)
                latency_ms = (time.perf_counter() - start) * 1000
                client.xack(STREAM_NAME, GROUP_NAME, message_id)
                processed += 1
                print(
                    f"[{consumer_name}] article {article_id}: processed in "
                    f"{latency_ms:.0f}ms, acked {message_id}"
                )

    conn.close()
    print(f"[{consumer_name}] done - processed {processed} message(s).")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "worker-1"
    run(consumer_name=name)
