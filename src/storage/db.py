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

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    entity_text TEXT NOT NULL,
    ticker TEXT,
    UNIQUE(article_id, entity_text)
);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
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


def get_unprocessed_articles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT id, title, summary FROM articles WHERE processed = 0")
    return cur.fetchall()


def insert_entity(conn: sqlite3.Connection, article_id: int, entity_text: str, ticker: str | None) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO entities (article_id, entity_text, ticker)
           VALUES (?, ?, ?)""",
        (article_id, entity_text, ticker),
    )


def mark_processed(conn: sqlite3.Connection, article_id: int) -> None:
    conn.execute("UPDATE articles SET processed = 1 WHERE id = ?", (article_id,))
