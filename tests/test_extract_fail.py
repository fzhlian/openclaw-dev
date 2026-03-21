from __future__ import annotations

from app.db import connect_db, init_db
from app.pipeline import ingest_url


def test_extract_failure_marks_status(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    def failing_fetcher(_: str) -> str:
        raise RuntimeError("network timeout")

    result = ingest_url("https://example.com/fail", conn=conn, fetcher=failing_fetcher)
    row = conn.execute("SELECT status, error_message FROM articles LIMIT 1").fetchone()
    assert result["status"] == "extract_failed"
    assert row["status"] == "extract_failed"
    assert "timeout" in row["error_message"]


def test_access_gate_page_marks_extract_failed(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    gate_html = """
    <html>
      <head><title>环境异常</title></head>
      <body>
        <p>环境异常</p>
        <p>当前环境异常，完成验证后即可继续访问。</p>
        <p>去验证</p>
      </body>
    </html>
    """

    result = ingest_url("https://mp.weixin.qq.com/s/example", conn=conn, fetcher=lambda _: gate_html)
    row = conn.execute("SELECT status, error_message FROM articles LIMIT 1").fetchone()
    assert result["status"] == "extract_failed"
    assert row["status"] == "extract_failed"
    assert "访问验证" in row["error_message"]
