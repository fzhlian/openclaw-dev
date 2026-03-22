from __future__ import annotations

from app.db import connect_db, get_settings, init_db, set_settings
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
    assert "【文章研判】" not in result["message"]
    assert result["message"].startswith("消息入库测试")


def test_ingest_message_direct_send_by_default(tmp_path):
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
        return {"ok": True, "result": {"message_id": 99}}

    result = ingest_message(
        "请处理这篇 https://example.com/direct",
        conn=conn,
        fetcher=lambda _: HTML,
        env_file=env_file,
        telegram_sender=fake_telegram_sender,
    )
    row = conn.execute("SELECT status FROM articles LIMIT 1").fetchone()
    assert result["status"] == "sent"
    assert row["status"] == "sent"
    assert len(sent_texts) == 1
    assert "已完成抓取和分析，正在推送总结" not in sent_texts[0]
    assert "【文章研判】" not in sent_texts[0]
    assert sent_texts[0].startswith("消息入库测试")
    assert "已推送 1" in result["message"]


def test_ingest_message_queue_hint_still_queues(tmp_path):
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

    result = ingest_message(
        "晚上统一发给我 https://example.com/queue-me",
        conn=conn,
        fetcher=lambda _: HTML,
        env_file=env_file,
    )
    row = conn.execute("SELECT status FROM articles LIMIT 1").fetchone()
    assert result["status"] == "queued"
    assert row["status"] == "queued"
    assert "入队 1" in result["message"]


def test_ingest_message_delay_hint_schedules_single_url(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    scheduled: list[tuple[int, int]] = []

    result = ingest_message(
        "现在开始，5分钟后再把整理后的发给我 https://example.com/delay-one",
        conn=conn,
        fetcher=lambda _: HTML,
        delay_scheduler=lambda article_id, delay_seconds, env_file=None: scheduled.append((article_id, delay_seconds)),
    )

    row = conn.execute("SELECT id, status FROM articles LIMIT 1").fetchone()
    assert result["status"] == "scheduled"
    assert row["status"] == "queued"
    assert scheduled == [(row["id"], 300)]
    assert "5 分钟后" in result["message"]


def test_ingest_message_delay_hint_can_schedule_latest_article_without_url(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    scheduled: list[tuple[int, int]] = []

    ingest_message(
        "帮我收录这篇 https://example.com/delay-follow-up",
        conn=conn,
        fetcher=lambda _: HTML,
    )

    row = conn.execute("SELECT id FROM articles LIMIT 1").fetchone()
    result = ingest_message(
        "现在开始，5分钟后再把整理后的发给我",
        conn=conn,
        delay_scheduler=lambda article_id, delay_seconds, env_file=None: scheduled.append((article_id, delay_seconds)),
    )

    assert result["status"] == "scheduled"
    assert scheduled == [(row["id"], 300)]
    assert "5 分钟后" in result["message"]


def test_ingest_message_delay_hint_accepts_more_natural_followup_variants(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    scheduled: list[tuple[int, int]] = []

    ingest_message(
        "帮我收录这篇 https://example.com/delay-natural",
        conn=conn,
        fetcher=lambda _: HTML,
    )

    row = conn.execute("SELECT id FROM articles LIMIT 1").fetchone()
    variants = [
        ("10分钟后再推送", 600),
        ("十分钟后再推送", 600),
        ("延迟十分钟推送", 600),
        ("延迟10分钟推送", 600),
        ("过10分钟再发给我", 600),
        ("先整理，10分钟后发我", 600),
    ]
    for text, seconds in variants:
        result = ingest_message(
            text,
            conn=conn,
            delay_scheduler=lambda article_id, delay_seconds, env_file=None: scheduled.append((article_id, delay_seconds)),
        )
        assert result["status"] == "scheduled"
        assert scheduled[-1] == (row["id"], seconds)


def test_ingest_message_can_update_daily_schedule(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"ARTICLE_DIGEST_DB={tmp_path / 'article_digest.db'}\n", encoding="utf-8")
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    installed: list[str] = []

    result = ingest_message(
        "开启定时推送，时间为22:30",
        conn=conn,
        env_file=env_file,
        schedule_installer=lambda project_root, *, cron_expr, env_file: installed.append(cron_expr),
    )

    settings = get_settings(conn)
    assert result["status"] == "schedule_updated"
    assert settings["digest_schedule"] == "30 22 * * *"
    assert installed == ["30 22 * * *"]
    assert "22:30" in result["message"]


def test_ingest_message_can_update_daily_schedule_from_natural_text(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"ARTICLE_DIGEST_DB={tmp_path / 'article_digest.db'}\n", encoding="utf-8")
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)
    installed: list[str] = []

    result = ingest_message(
        "每天12:00推送给我",
        conn=conn,
        env_file=env_file,
        schedule_installer=lambda project_root, *, cron_expr, env_file: installed.append(cron_expr),
    )

    settings = get_settings(conn)
    assert result["status"] == "schedule_updated"
    assert settings["digest_schedule"] == "0 12 * * *"
    assert installed == ["0 12 * * *"]
    assert "12:00" in result["message"]


def test_ingest_message_daily_schedule_switches_following_links_to_queue(tmp_path):
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

    ingest_message(
        "每天9:00推送",
        conn=conn,
        env_file=env_file,
        schedule_installer=lambda project_root, *, cron_expr, env_file: None,
    )

    sent_texts: list[str] = []

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_texts.append(text)
        return {"ok": True, "result": {"message_id": 99}}

    result = ingest_message(
        "https://example.com/scheduled-queue",
        conn=conn,
        fetcher=lambda _: HTML,
        env_file=env_file,
        telegram_sender=fake_telegram_sender,
    )

    settings = get_settings(conn)
    row = conn.execute("SELECT status FROM articles LIMIT 1").fetchone()
    assert settings["digest_delivery_mode"] == "scheduled"
    assert result["status"] == "queued"
    assert row["status"] == "queued"
    assert sent_texts == []


def test_ingest_message_respects_existing_custom_schedule_without_mode_flag(tmp_path):
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
    set_settings(conn, {"digest_schedule": "0 9 * * *"})

    sent_texts: list[str] = []

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_texts.append(text)
        return {"ok": True, "result": {"message_id": 99}}

    result = ingest_message(
        "https://example.com/scheduled-legacy-queue",
        conn=conn,
        fetcher=lambda _: HTML,
        env_file=env_file,
        telegram_sender=fake_telegram_sender,
    )

    row = conn.execute("SELECT status FROM articles LIMIT 1").fetchone()
    assert result["status"] == "queued"
    assert row["status"] == "queued"
    assert sent_texts == []


def test_ingest_message_can_push_ready_articles_immediately(tmp_path):
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
    ingest_message(
        "晚上统一发给我 https://example.com/push-now",
        conn=conn,
        env_file=env_file,
        fetcher=lambda _: HTML,
    )
    sent_texts: list[str] = []

    def fake_telegram_sender(token, chat_id, text, thread_id=None):
        sent_texts.append(text)
        return {"ok": True, "result": {"message_id": len(sent_texts)}}

    result = ingest_message(
        "提前推送",
        conn=conn,
        env_file=env_file,
        telegram_sender=fake_telegram_sender,
    )
    row = conn.execute("SELECT status FROM articles LIMIT 1").fetchone()

    assert result["status"] == "sent"
    assert row["status"] == "sent"
    assert sent_texts
    assert "已提前推送 1 篇已整理文章到 Telegram。" in result["message"]


def test_ingest_message_can_favorite_latest_article(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    ingest_message(
        "帮我收录这篇 https://example.com/favorite-latest",
        conn=conn,
        fetcher=lambda _: HTML,
    )
    result = ingest_message("收藏这篇", conn=conn)
    row = conn.execute("SELECT is_favorite FROM articles LIMIT 1").fetchone()

    assert result["status"] == "favorited"
    assert row["is_favorite"] == 1
    assert "已收藏" in result["message"]


def test_ingest_message_can_favorite_latest_article_with_bare_command(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    ingest_message(
        "帮我收录这篇 https://example.com/favorite-bare",
        conn=conn,
        fetcher=lambda _: HTML,
    )
    result = ingest_message("收藏", conn=conn)
    row = conn.execute("SELECT is_favorite FROM articles LIMIT 1").fetchone()

    assert result["status"] == "favorited"
    assert row["is_favorite"] == 1
    assert "已收藏" in result["message"]


def test_ingest_message_favorite_ignores_latest_failed_stub(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    ingest_message(
        "帮我收录这篇 https://example.com/favorite-ready",
        conn=conn,
        fetcher=lambda _: HTML,
    )
    ingest_message(
        "帮我收录这篇 https://example.com/favorite-failed",
        conn=conn,
        fetcher=lambda _: "<html><head><title>坏页面</title></head><body>太短</body></html>",
    )

    result = ingest_message("收藏", conn=conn)
    rows = conn.execute("SELECT id, title, status, is_favorite FROM articles ORDER BY id ASC").fetchall()

    assert result["status"] == "favorited"
    assert rows[0]["title"] == "消息入库测试"
    assert rows[0]["is_favorite"] == 1
    assert rows[1]["status"] == "extract_failed"
    assert rows[1]["is_favorite"] == 0


def test_ingest_message_can_list_and_review_favorites(tmp_path):
    conn = connect_db(tmp_path / "article_digest.db")
    init_db(conn)

    ingest_message(
        "收藏这篇 https://example.com/favorite-review-one",
        conn=conn,
        fetcher=lambda _: HTML.replace("消息入库测试", "第一篇收藏"),
    )
    first_article_id = conn.execute("SELECT id FROM articles LIMIT 1").fetchone()["id"]
    ingest_message(
        "收藏这篇 https://example.com/favorite-review-two",
        conn=conn,
        fetcher=lambda _: HTML.replace("消息入库测试", "第二篇收藏"),
    )

    favorites = ingest_message("查看收藏", conn=conn)
    detail = ingest_message("回看收藏 1", conn=conn)
    detail_by_id = ingest_message(f"回看收藏 id {first_article_id}", conn=conn)
    detail_by_brief = ingest_message("回看2", conn=conn)
    detail_by_number = ingest_message("2", conn=conn)

    assert favorites["status"] == "favorites_list"
    assert "共收藏 2 篇：" in favorites["message"]
    assert "1）第二篇收藏" in favorites["message"]
    assert "2）第一篇收藏" in favorites["message"]
    assert "原文链接：" in favorites["message"]
    assert "直接回复数字、发送“回看2”" in favorites["message"]
    assert detail["status"] == "favorite_detail"
    assert "【文章研判】" not in detail["message"]
    assert "第二篇收藏" in detail["message"]
    assert "AI 参与度：" in detail["message"]
    assert detail["message"].rstrip().endswith("https://example.com/favorite-review-two")
    assert detail_by_id["status"] == "favorite_detail"
    assert "第一篇收藏" in detail_by_id["message"]
    assert detail_by_brief["status"] == "favorite_detail"
    assert "第一篇收藏" in detail_by_brief["message"]
    assert detail_by_number["status"] == "favorite_detail"
    assert "第一篇收藏" in detail_by_number["message"]
