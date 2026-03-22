from __future__ import annotations

import app.translation as translation
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


def test_ingest_success_direct_send_when_transport_available(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"ARTICLE_DIGEST_DB={tmp_path / 'article_digest.db'}",
                "SEND_MODE=telegram",
                "TELEGRAM_BOT_TOKEN=test-token",
                "TELEGRAM_CHAT_ID=chat-1",
            ]
        ),
        encoding="utf-8",
    )
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    sent_texts: list[str] = []

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_texts.append(text)
        return {"ok": True, "result": {"message_id": 88}}

    result = ingest_url(
        "https://example.com/articles/direct",
        conn=conn,
        fetcher=lambda _: HTML,
        env_file=env_file,
        telegram_sender=fake_telegram_sender,
    )
    sent = conn.execute("SELECT status, title FROM articles LIMIT 1").fetchone()
    assert result["status"] == "sent"
    assert result["delivery_method"] == "telegram_bot_fallback"
    assert sent["status"] == "sent"
    assert sent["title"] == "测试文章"
    assert len(sent_texts) == 1
    assert "已完成抓取和分析，正在推送总结" not in sent_texts[0]
    assert "【文章研判】测试文章" not in sent_texts[0]
    assert sent_texts[0].startswith("测试文章")


def test_ingest_translates_non_chinese_output_to_chinese(tmp_path, monkeypatch):
    english_html = """
    <html lang="en">
      <head>
        <title>Energy route under pressure</title>
        <meta property="og:site_name" content="Example News" />
        <meta property="article:published_time" content="2026-03-21T10:00:00Z" />
      </head>
      <body>
        <article>
          <p>The article explains how a critical sea route is becoming more fragile because of geopolitical tension and rising insurance costs.</p>
          <p>It also argues that shipping companies now need to assess security, fuel costs and diplomatic risk together instead of treating them separately.</p>
          <p>A final section describes how energy buyers and exporters are preparing contingency plans for further disruption.</p>
        </article>
      </body>
    </html>
    """

    monkeypatch.setattr(translation, "translate_text_to_chinese", lambda text, timeout=15: f"中译：{text}")

    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    result = ingest_url(
        "https://example.com/articles/english",
        conn=conn,
        fetcher=lambda _: english_html,
    )

    assert result["status"] == "queued"
    assert result["article"]["title"].startswith("中译：")
    assert result["article"]["summary"].startswith("中译：")
    assert result["article"]["main_threads"]
    assert all(item.startswith("中译：") for item in result["article"]["main_threads"])
