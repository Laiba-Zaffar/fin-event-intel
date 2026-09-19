import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from dateutil import parser as dateparser

FEED_TIMEOUT_SECONDS = 10

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.ingest.rss_sources import RSS_FEEDS
from src.storage.db import get_connection, insert_article


def parse_published(entry) -> str | None:
    raw = entry.get("published") or entry.get("updated")
    if not raw:
        return None
    try:
        return dateparser.parse(raw).astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None


def fetch_feed(source: str, url: str) -> list[dict]:
    socket.setdefaulttimeout(FEED_TIMEOUT_SECONDS)
    try:
        parsed = feedparser.parse(url)
    except Exception as exc:
        print(f"  [warn] {source}: request failed ({exc})")
        return []
    finally:
        socket.setdefaulttimeout(None)

    if parsed.bozo and not parsed.entries:
        print(f"  [warn] {source}: failed to parse ({parsed.bozo_exception})")
        return []

    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "source": source,
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", "").strip(),
            "summary": entry.get("summary", "").strip(),
            "published_at": parse_published(entry),
            "fetched_at": now,
        }
        for entry in parsed.entries
        if entry.get("link")
    ]


def run_once() -> None:
    conn = get_connection()
    total_new = 0

    for source, url in RSS_FEEDS.items():
        articles = fetch_feed(source, url)
        new_count = sum(insert_article(conn, a) for a in articles)
        total_new += new_count
        print(f"  {source}: {len(articles)} fetched, {new_count} new")

    conn.close()
    print(f"Done. {total_new} new articles stored.")


if __name__ == "__main__":
    run_once()
