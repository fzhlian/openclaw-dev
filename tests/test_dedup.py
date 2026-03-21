from __future__ import annotations

from app.db import connect_db, init_db
from app.pipeline import ingest_url


HTML = """
<html><head><title>重复文章</title></head><body>
<p>第一段有足够长的内容用于测试去重逻辑。这篇文章会被连续入库两次。</p>
<p>第二段继续补充上下文，确保抽取能成功。</p>
<p>第三段补充更多信息。</p>
</body></html>
"""


def test_duplicate_url_not_inserted_twice(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    first = ingest_url("https://example.com/repeat", conn=conn, fetcher=lambda _: HTML)
    second = ingest_url("https://example.com/repeat#section", conn=conn, fetcher=lambda _: HTML)
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    assert first["status"] == "queued"
    assert second["status"] == "duplicate"
    assert count == 1


def test_extract_failed_url_can_retry_same_hash(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    def failing_fetcher(_: str) -> str:
        raise RuntimeError("temporary gate")

    first = ingest_url("https://example.com/retry", conn=conn, fetcher=failing_fetcher)
    second = ingest_url("https://example.com/retry", conn=conn, fetcher=lambda _: HTML)
    row = conn.execute("SELECT status, title FROM articles LIMIT 1").fetchone()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    assert first["status"] == "extract_failed"
    assert second["status"] == "queued"
    assert row["status"] == "queued"
    assert row["title"] == "重复文章"
    assert count == 1
