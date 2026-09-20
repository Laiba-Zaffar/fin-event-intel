import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pytest

from src.storage import db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    connection = db.get_connection()
    yield connection
    connection.close()


def make_article(link="https://example.com/a", title="Title"):
    return {
        "source": "test_source",
        "title": title,
        "link": link,
        "summary": "summary",
        "published_at": "2026-01-01T00:00:00+00:00",
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }


def test_insert_article_returns_id_on_success(conn):
    article_id = db.insert_article(conn, make_article())
    assert isinstance(article_id, int)


def test_insert_article_dedupes_by_link(conn):
    first = db.insert_article(conn, make_article(link="https://dup.example/1"))
    second = db.insert_article(conn, make_article(link="https://dup.example/1"))
    assert first is not None
    assert second is None


def test_get_unprocessed_articles_returns_only_unprocessed(conn):
    article_id = db.insert_article(conn, make_article(link="https://a.example/1"))
    assert len(db.get_unprocessed_articles(conn)) == 1
    db.mark_processed(conn, article_id)
    assert len(db.get_unprocessed_articles(conn)) == 0


def test_get_unclassified_articles_returns_only_unclassified(conn):
    article_id = db.insert_article(conn, make_article(link="https://a.example/2"))
    assert len(db.get_unclassified_articles(conn)) == 1
    db.store_classification(conn, article_id, "earnings report", 0.9)
    assert len(db.get_unclassified_articles(conn)) == 0


def test_insert_entity_dedupes_per_article(conn):
    article_id = db.insert_article(conn, make_article(link="https://a.example/3"))
    db.insert_entity(conn, article_id, "Apple", "AAPL")
    db.insert_entity(conn, article_id, "Apple", "AAPL")  # duplicate, should be ignored
    conn.commit()
    count = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE article_id = ?", (article_id,)
    ).fetchone()[0]
    assert count == 1


def test_get_article_returns_row_or_none(conn):
    article_id = db.insert_article(conn, make_article(link="https://a.example/4"))
    assert db.get_article(conn, article_id)["title"] == "Title"
    assert db.get_article(conn, 999999) is None
