from __future__ import annotations

from app.db import connect_db, init_db, list_deliveries
from app.pipeline import ingest_url, send_digest


HTML = """
<html><head><title>Delivery 测试</title></head><body>
<p>第一段正文用于发送记录测试，长度足够。</p>
<p>第二段补充上下文和来源信息。</p>
<p>第三段继续扩充文章长度。</p>
</body></html>
"""


def test_delivery_record_is_written(tmp_path):
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
    ingest_url("https://example.com/delivery", conn=conn, fetcher=lambda _: HTML, env_file=env_file, 仅入队=True)

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        return {"ok": True, "result": {"message_id": 77}}

    result = send_digest(env_file=env_file, conn=conn, telegram_sender=fake_telegram_sender)
    deliveries = list_deliveries(conn)
    assert result["status"] == "sent"
    assert len(deliveries) == 1
    assert deliveries[0]["delivery_status"] == "sent"
    assert deliveries[0]["message_count"] >= 1
