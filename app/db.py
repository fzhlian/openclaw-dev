from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app.models import AI_DISCLAIMER, CREDIBILITY_DISCLAIMER
from app.utils import json_dumps, load_json_if_present, utc_now_iso


ARTICLE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL UNIQUE,
    title TEXT,
    source TEXT,
    author TEXT,
    language TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    raw_html_path TEXT,
    extracted_text_path TEXT,
    summary TEXT,
    main_threads_json TEXT,
    credibility_score INTEGER,
    credibility_level TEXT,
    credibility_reasons_json TEXT,
    credibility_risks_json TEXT,
    ai_likelihood_score INTEGER,
    ai_likelihood_level TEXT,
    ai_reasons_json TEXT,
    ai_limitations_json TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

DELIVERY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_date TEXT NOT NULL,
    article_ids_json TEXT NOT NULL,
    target_chat_id TEXT NOT NULL,
    target_thread_id TEXT,
    message_count INTEGER NOT NULL,
    delivery_method TEXT NOT NULL,
    delivery_status TEXT NOT NULL,
    external_message_ids_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);
"""

SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def connect_db(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(ARTICLE_TABLE_SQL)
    conn.execute(DELIVERY_TABLE_SQL)
    conn.execute(SETTINGS_TABLE_SQL)
    conn.commit()


def get_settings(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, value, utc_now_iso()),
    )
    conn.commit()


def set_settings(conn: sqlite3.Connection, values: dict[str, str]) -> None:
    if not values:
        return
    now = utc_now_iso()
    conn.executemany(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        [(key, value, now) for key, value in values.items()],
    )
    conn.commit()


def get_article_by_hash(conn: sqlite3.Connection, article_hash: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM articles WHERE url_hash = ?", (article_hash,)).fetchone()


def get_article_by_id(conn: sqlite3.Connection, article_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()


def create_article_stub(
    conn: sqlite3.Connection,
    *,
    url: str,
    url_hash: str,
    fetched_at: str,
    status: str = "extracting",
) -> int:
    now = utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO articles (
            url, url_hash, fetched_at, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (url, url_hash, fetched_at, status, now, now),
    )
    conn.commit()
    return int(cursor.lastrowid)


def mark_article_status(
    conn: sqlite3.Connection,
    article_id: int,
    status: str,
    *,
    error_message: str | None = None,
) -> None:
    conn.execute(
        "UPDATE articles SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
        (status, error_message, utc_now_iso(), article_id),
    )
    conn.commit()


def update_article_success(
    conn: sqlite3.Connection,
    article_id: int,
    *,
    article: dict[str, Any],
    summary: str,
    main_threads: list[str],
    credibility: dict[str, Any],
    ai_likelihood: dict[str, Any],
    status: str = "queued",
) -> None:
    conn.execute(
        """
        UPDATE articles
        SET title = ?, source = ?, author = ?, language = ?, published_at = ?,
            fetched_at = ?, raw_html_path = ?, extracted_text_path = ?, summary = ?,
            main_threads_json = ?, credibility_score = ?, credibility_level = ?,
            credibility_reasons_json = ?, credibility_risks_json = ?, ai_likelihood_score = ?,
            ai_likelihood_level = ?, ai_reasons_json = ?, ai_limitations_json = ?,
            status = ?, error_message = NULL, updated_at = ?
        WHERE id = ?
        """,
        (
            article.get("title"),
            article.get("source"),
            article.get("author"),
            article.get("language"),
            article.get("published_at"),
            article.get("fetched_at"),
            article.get("raw_html_path"),
            article.get("extracted_text_path"),
            summary,
            json_dumps(main_threads),
            credibility.get("score"),
            credibility.get("level"),
            json_dumps(credibility.get("reasons", [])),
            json_dumps(credibility.get("risks", [])),
            ai_likelihood.get("score"),
            ai_likelihood.get("level"),
            json_dumps(ai_likelihood.get("reasons", [])),
            json_dumps(ai_likelihood.get("limitations", [])),
            status,
            utc_now_iso(),
            article_id,
        ),
    )
    conn.commit()


def list_articles_by_status(
    conn: sqlite3.Connection,
    status: str,
    *,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM articles WHERE status = ? ORDER BY created_at ASC"
    params: list[Any] = [status]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return list(conn.execute(sql, params).fetchall())


def update_articles_status(conn: sqlite3.Connection, article_ids: Iterable[int], status: str) -> None:
    ids = list(article_ids)
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    conn.execute(
        f"UPDATE articles SET status = ?, updated_at = ? WHERE id IN ({placeholders})",
        [status, utc_now_iso(), *ids],
    )
    conn.commit()


def record_delivery(
    conn: sqlite3.Connection,
    *,
    batch_date: str,
    article_ids: list[int],
    target_chat_id: str,
    target_thread_id: str | None,
    message_count: int,
    delivery_method: str,
    delivery_status: str,
    external_message_ids: list[str] | None = None,
    error_message: str | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO deliveries (
            batch_date, article_ids_json, target_chat_id, target_thread_id,
            message_count, delivery_method, delivery_status,
            external_message_ids_json, error_message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            batch_date,
            json_dumps(article_ids),
            target_chat_id,
            target_thread_id,
            message_count,
            delivery_method,
            delivery_status,
            json_dumps(external_message_ids or []),
            error_message,
            utc_now_iso(),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def list_deliveries(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM deliveries ORDER BY id ASC").fetchall())


def article_row_to_payload(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    source = dict(row)
    return {
        "id": source.get("id"),
        "url": source.get("url"),
        "title": source.get("title") or "未命名文章",
        "source": source.get("source") or "未知来源",
        "author": source.get("author"),
        "published_at": source.get("published_at"),
        "language": source.get("language") or "unknown",
        "summary": source.get("summary") or "",
        "main_threads": load_json_if_present(source.get("main_threads_json")) or [],
        "credibility": {
            "score": int(source.get("credibility_score") or 0),
            "level": source.get("credibility_level") or "未知",
            "reasons": load_json_if_present(source.get("credibility_reasons_json")) or [],
            "risks": load_json_if_present(source.get("credibility_risks_json")) or [],
            "disclaimer": CREDIBILITY_DISCLAIMER,
        },
        "ai_likelihood": {
            "score": int(source.get("ai_likelihood_score") or 0),
            "level": source.get("ai_likelihood_level") or "无法判断",
            "reasons": load_json_if_present(source.get("ai_reasons_json")) or [],
            "limitations": load_json_if_present(source.get("ai_limitations_json")) or [],
            "disclaimer": AI_DISCLAIMER,
        },
        "status": source.get("status"),
    }
