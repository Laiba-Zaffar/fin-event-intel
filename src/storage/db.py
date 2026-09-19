import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "news.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    summary TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0
);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def insert_article(conn: sqlite3.Connection, article: dict) -> bool:
    try:
        conn.execute(
            """INSERT INTO articles (source, title, link, summary, published_at, fetched_at)
               VALUES (:source, :title, :link, :summary, :published_at, :fetched_at)""",
            article,
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # link already seen — RSS feeds repeat entries across polls
        return False
