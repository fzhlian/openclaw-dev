from __future__ import annotations

from app.db import connect_db, create_article_stub, init_db, update_article_success
from app.pipeline import ingest_url
from app.utils import url_hash, utc_now_iso


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


def test_bad_wechat_payload_can_refresh_same_hash(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    url = "https://mp.weixin.qq.com/s/retry"
    article_id = create_article_stub(conn, url=url, url_hash=url_hash(url), fetched_at=utc_now_iso(), status="extracting")
    update_article_success(
        conn,
        article_id,
        article={
            "title": "轻触查看原文",
            "source": "微信公众平台",
            "author": None,
            "language": "unknown",
            "published_at": None,
            "fetched_at": utc_now_iso(),
            "raw_html_path": None,
            "extracted_text_path": None,
        },
        summary="微信扫一扫可打开此内容，使用完整服务",
        main_threads=["向上滑动看下一个"],
        credibility={"score": 0, "level": "未知", "reasons": [], "risks": []},
        ai_likelihood={"score": 0, "level": "无法判断", "reasons": [], "limitations": []},
        status="queued",
    )
    valid_html = """
    <html lang="zh-CN">
      <body>
        <h1 id="activity-name">微信重抓成功</h1>
        <a id="js_name">示例公众号</a>
        <div id="js_content">
          <p>第一段足够长的正文内容，用来验证历史坏记录会被自动重抓，而不是继续走 duplicate 分支。</p>
          <p>第二段补充信息，确保抽取后的结果会更新数据库里的旧记录。</p>
        </div>
        <script>
          var ct = "1774063100";
          var nickname = htmlDecode("示例公众号");
        </script>
      </body>
    </html>
    """

    result = ingest_url(url, conn=conn, fetcher=lambda _: valid_html)
    row = conn.execute("SELECT status, title, source FROM articles LIMIT 1").fetchone()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    assert result["status"] == "queued"
    assert row["status"] == "queued"
    assert row["title"] == "微信重抓成功"
    assert row["source"] == "示例公众号"
    assert count == 1
