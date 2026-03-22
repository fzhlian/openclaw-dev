from __future__ import annotations

from app.pipeline import ingest_url
from app.db import connect_db, init_db


HTML = """
<html><head><title>Schema 文章</title><meta property="og:site_name" content="Schema Site" /></head>
<body>
<p>这是一篇用于校验 schema 的文章，包含足够长的内容、时间 2026-03-21 和一些具体信息。</p>
<p>第二段继续提供支撑内容，确保各字段都能生成。</p>
<p>第三段提供补充说明和引用“某专家”的说法。</p>
</body></html>
"""


def test_output_matches_schema_shape(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    result = ingest_url("https://example.com/schema", conn=conn, fetcher=lambda _: HTML)
    article = result["article"]
    assert {
        "url",
        "title",
        "source",
        "author",
        "published_at",
        "language",
        "is_favorite",
        "favorited_at",
        "summary",
        "main_threads",
        "credibility",
        "ai_likelihood",
        "status",
    } <= set(article)
    assert {"score", "level", "reasons", "risks", "disclaimer"} <= set(article["credibility"])
    assert {"score", "level", "reasons", "limitations", "disclaimer"} <= set(article["ai_likelihood"])
    assert isinstance(article["main_threads"], list)
    assert article["is_favorite"] is False
