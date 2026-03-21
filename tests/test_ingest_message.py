from __future__ import annotations

from app.db import connect_db, init_db
from app.pipeline import ingest_message


HTML = """
<html><head><title>消息入库测试</title></head><body>
<p>第一段正文用于测试从一条消息中提取多个 URL，并且内容足够长。</p>
<p>第二段继续补充背景，确保不会因为提取过短失败。</p>
<p>第三段增加上下文和细节。</p>
</body></html>
"""


def test_ingest_message_extracts_multiple_urls(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    result = ingest_message(
        "帮我收录这两篇 https://example.com/a 和 https://example.com/b",
        conn=conn,
        fetcher=lambda _: HTML,
    )
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    assert result["status"] == "queued"
    assert count == 2
    assert "入队 2" in result["message"]


def test_ingest_message_immediate_single_url(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    result = ingest_message(
        "现在分析这篇 https://example.com/instant",
        conn=conn,
        fetcher=lambda _: HTML,
    )
    assert result["status"] == "queued"
    assert "message" in result
    assert "【文章研判】" in result["message"]

