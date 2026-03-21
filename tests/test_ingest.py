from __future__ import annotations

from app.db import connect_db, init_db, list_articles_by_status
from app.pipeline import ingest_url


HTML = """
<html lang="zh">
  <head>
    <title>测试文章</title>
    <meta property="og:site_name" content="测试站点" />
    <meta name="author" content="测试作者" />
    <meta property="article:published_time" content="2026-03-21T10:00:00Z" />
  </head>
  <body>
    <article>
      <p>这是一篇包含充分细节的测试文章。它给出了时间、数字 123 和引用“测试对象”的说法，用于验证正文抽取。</p>
      <p>第二段继续提供补充背景、来源和事件过程，使得摘要、主线和可信度评分都有稳定输入。</p>
      <p>第三段加入更多上下文，避免因为正文过短而被判定为抽取失败。</p>
    </article>
  </body>
</html>
"""


def test_ingest_success(tmp_path):
    db_path = tmp_path / "article_digest.db"
    conn = connect_db(db_path)
    init_db(conn)
    result = ingest_url(
        "https://example.com/articles/1?utm_source=test",
        conn=conn,
        fetcher=lambda _: HTML,
    )
    queued = list_articles_by_status(conn, "queued")
    assert result["status"] == "queued"
    assert queued
    assert queued[0]["title"] == "测试文章"

