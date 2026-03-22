from __future__ import annotations

import subprocess

from app.db import connect_db, init_db
from app.pipeline import ingest_url, send_digest


HTML = """
<html><head><title>Fallback 测试</title></head><body>
<p>第一段提供足够长度的正文内容，以便入库和后续发送。</p>
<p>第二段给出更多上下文和事件细节，避免提取失败。</p>
<p>第三段继续扩充文章长度。</p>
</body></html>
"""


def test_send_fallback_to_telegram(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"ARTICLE_DIGEST_DB={tmp_path / 'article_digest.db'}",
                "SEND_MODE=auto",
                "TELEGRAM_BOT_TOKEN=test-token",
                "TELEGRAM_CHAT_ID=123456",
                "OPENCLAW_MESSAGE_TARGET=123456",
            ]
        ),
        encoding="utf-8",
    )
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    ingest_url("https://example.com/fallback", conn=conn, fetcher=lambda _: HTML, env_file=env_file, 仅入队=True)

    def failing_runner(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=kwargs.get("args") or args[0])

    sent_payloads = []

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_payloads.append((token, chat_id, text, thread_id))
        return {"ok": True, "result": {"message_id": 1001}}

    result = send_digest(env_file=env_file, conn=conn, runner=failing_runner, telegram_sender=fake_telegram_sender)
    assert result["status"] == "sent"
    assert result["delivery_method"] == "openclaw_message+telegram_bot_fallback"
    assert sent_payloads
