from __future__ import annotations

from app.db import connect_db, init_db
from app.pipeline import ingest_url, send_digest


HTML = """
<html><head><title>Batch 测试</title></head><body>
<p>第一段用于批量发送测试，长度足够。</p>
<p>第二段用于保证抽取和摘要逻辑顺利执行。</p>
<p>第三段增加文章长度和上下文。</p>
</body></html>
"""


def test_only_queued_articles_are_sent_and_marked_sent(tmp_path):
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
    ingest_url("https://example.com/a", conn=conn, fetcher=lambda _: HTML, env_file=env_file, 仅入队=True)
    ingest_url("https://example.com/b", conn=conn, fetcher=lambda _: HTML, env_file=env_file, 仅入队=True)
    latest_id = conn.execute("SELECT id FROM articles ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.execute("UPDATE articles SET status = 'sent' WHERE id = ?", (latest_id,))
    conn.commit()

    sent_messages = []

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_messages.append(text)
        return {"ok": True, "result": {"message_id": len(sent_messages)}}

    result = send_digest(env_file=env_file, conn=conn, telegram_sender=fake_telegram_sender)
    rows = conn.execute("SELECT url, status FROM articles ORDER BY url").fetchall()
    assert result["status"] == "sent"
    assert len(result["article_ids"]) == 1
    assert any("文章 Digest" in message for message in sent_messages)
    assert rows[0]["status"] == "sent"
    assert rows[1]["status"] == "sent"
