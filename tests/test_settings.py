from __future__ import annotations

from app.db import connect_db, get_settings, init_db, set_settings
from app.pipeline import ingest_url, send_digest


HTML = """
<html><head><title>Settings 测试</title></head><body>
<p>这是一篇用于检查 settings 落库的测试文章，内容足够长。</p>
<p>第二段补充更多上下文信息。</p>
<p>第三段补充更多细节。</p>
</body></html>
"""


def test_runtime_settings_are_persisted(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"ARTICLE_DIGEST_DB={tmp_path / 'article_digest.db'}",
                "TELEGRAM_CHAT_ID=chat-42",
                "OPENCLAW_MESSAGE_TARGET=chat-42",
                "DIGEST_TZ=Asia/Taipei",
                "MAX_DIGEST_ITEMS=7",
            ]
        ),
        encoding="utf-8",
    )
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    ingest_url("https://example.com/settings", env_file=env_file, conn=conn, fetcher=lambda _: HTML)
    settings = get_settings(conn)
    assert settings["telegram_chat_id"] == "chat-42"
    assert settings["openclaw_target"] == "chat-42"
    assert settings["digest_tz"] == "Asia/Taipei"
    assert settings["max_digest_items"] == "7"


def test_settings_fallback_applies_when_env_missing(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"ARTICLE_DIGEST_DB={tmp_path / 'article_digest.db'}\nSEND_MODE=telegram\nTELEGRAM_BOT_TOKEN=test-token\n", encoding="utf-8")
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    set_settings(
        conn,
        {
            "telegram_chat_id": "stored-chat",
            "openclaw_target": "stored-chat",
            "max_digest_items": "3",
        },
    )
    ingest_url("https://example.com/settings-fallback", env_file=env_file, conn=conn, fetcher=lambda _: HTML)
    sent_messages = []

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_messages.append((token, chat_id, text, thread_id))
        return {"ok": True, "result": {"message_id": 88}}

    result = send_digest(env_file=env_file, conn=conn, telegram_sender=fake_telegram_sender)
    assert result["status"] == "sent"
    assert sent_messages[0][1] == "stored-chat"
