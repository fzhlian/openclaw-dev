from __future__ import annotations

import sqlite3
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from app.analysis import assess_ai_likelihood, assess_credibility, summarize_threads
from app.config import AppConfig, load_config
from app.db import (
    article_row_to_payload,
    connect_db,
    create_article_stub,
    get_article_by_hash,
    get_settings,
    init_db,
    list_articles_by_status,
    mark_article_status,
    record_delivery,
    set_settings,
    update_article_success,
    update_articles_status,
)
from app.digest import build_digest_messages, format_single_article
from app.extraction import ExtractionError, extract_article
from app.schema import validate_article_payload
from app.sending import deliver_messages
from app.telegram_fallback import send_via_telegram_bot
from app.utils import extract_urls, local_today, normalize_url, url_hash, utc_now_iso


def _ensure_conn(config: AppConfig, conn: sqlite3.Connection | None) -> sqlite3.Connection:
    if conn is not None:
        init_db(conn)
        return conn
    new_conn = connect_db(config.db_path)
    init_db(new_conn)
    return new_conn


def _sync_runtime_settings(config: AppConfig, conn: sqlite3.Connection) -> AppConfig:
    stored = get_settings(conn)
    has = config.provided_keys
    resolved_digest_schedule = config.digest_schedule if "DIGEST_SCHEDULE" in has else stored.get("digest_schedule", config.digest_schedule)
    resolved_digest_tz = config.digest_tz if "DIGEST_TZ" in has else stored.get("digest_tz", config.digest_tz)
    resolved_send_mode = config.send_mode if "SEND_MODE" in has else stored.get("send_mode", config.send_mode)
    resolved_max_items = (
        config.max_digest_items if "MAX_DIGEST_ITEMS" in has else int(stored.get("max_digest_items", str(config.max_digest_items)))
    )
    resolved_max_chars = (
        config.max_message_chars if "MAX_MESSAGE_CHARS" in has else int(stored.get("max_message_chars", str(config.max_message_chars)))
    )
    resolved_telegram_chat_id = (
        config.telegram_chat_id
        if "TELEGRAM_CHAT_ID" in has
        else config.telegram_chat_id or stored.get("telegram_chat_id")
    )
    resolved_telegram_thread_id = (
        config.telegram_thread_id
        if "TELEGRAM_THREAD_ID" in has
        else config.telegram_thread_id or stored.get("telegram_thread_id")
    )
    resolved_openclaw_target = (
        config.openclaw_target
        if "OPENCLAW_MESSAGE_TARGET" in has or "TELEGRAM_CHAT_ID" in has
        else config.openclaw_target or stored.get("openclaw_target")
    )
    resolved_openclaw_channel = (
        config.openclaw_channel
        if "OPENCLAW_MESSAGE_CHANNEL" in has
        else config.openclaw_channel or stored.get("openclaw_channel")
    )
    persisted = {
        "digest_schedule": resolved_digest_schedule,
        "digest_tz": resolved_digest_tz,
        "send_mode": resolved_send_mode,
        "max_digest_items": str(resolved_max_items),
        "max_message_chars": str(resolved_max_chars),
    }
    if resolved_telegram_chat_id:
        persisted["telegram_chat_id"] = resolved_telegram_chat_id
    if resolved_telegram_thread_id:
        persisted["telegram_thread_id"] = resolved_telegram_thread_id
    if resolved_openclaw_target:
        persisted["openclaw_target"] = resolved_openclaw_target
    if resolved_openclaw_channel:
        persisted["openclaw_channel"] = resolved_openclaw_channel
    set_settings(conn, persisted)
    return replace(
        config,
        telegram_chat_id=resolved_telegram_chat_id,
        telegram_thread_id=resolved_telegram_thread_id,
        digest_schedule=resolved_digest_schedule,
        digest_tz=resolved_digest_tz,
        send_mode=resolved_send_mode,
        max_digest_items=resolved_max_items,
        max_message_chars=resolved_max_chars,
        openclaw_target=resolved_openclaw_target,
        openclaw_channel=resolved_openclaw_channel,
    )


def ingest_url(
    url: str,
    *,
    immediate: bool = False,
    env_file: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
    fetcher: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    config = load_config(env_file)
    database = _ensure_conn(config, conn)
    config = _sync_runtime_settings(config, database)
    normalized = normalize_url(url)
    article_hash = url_hash(normalized)
    existing = get_article_by_hash(database, article_hash)
    if existing:
        payload = article_row_to_payload(existing)
        validate_article_payload(payload)
        return {"status": "duplicate", "url": normalized, "article": payload}
    article_id = create_article_stub(database, url=normalized, url_hash=article_hash, fetched_at=utc_now_iso(), status="extracting")
    try:
        article = extract_article(
            normalized,
            raw_html_dir=config.raw_html_dir,
            extracted_text_dir=config.extracted_text_dir,
            fetcher=fetcher,
        )
    except ExtractionError as exc:
        mark_article_status(database, article_id, "extract_failed", error_message=str(exc))
        return {"status": "extract_failed", "url": normalized, "error_message": str(exc)}
    try:
        credibility = assess_credibility(article)
        ai_likelihood = assess_ai_likelihood(article)
        threads = summarize_threads(article)
    except Exception as exc:
        mark_article_status(database, article_id, "analysis_failed", error_message=str(exc))
        return {"status": "analysis_failed", "url": normalized, "error_message": str(exc)}
    update_article_success(
        database,
        article_id,
        article=article.to_dict(),
        summary=threads["summary"],
        main_threads=threads["main_threads"],
        credibility=credibility.to_dict(),
        ai_likelihood=ai_likelihood.to_dict(),
        status="queued",
    )
    row = database.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    payload = article_row_to_payload(row)
    payload["url"] = normalized
    validate_article_payload(payload)
    if immediate:
        payload["message"] = format_single_article(payload)
        return payload
    return {"status": "queued", "message": "已加入待发送列表", "article": payload}


def ingest_message(
    message_text: str,
    *,
    env_file: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
    fetcher: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    urls = extract_urls(message_text)
    if not urls:
        return {"status": "no_url", "message": "未识别到可处理的链接"}
    wants_immediate = any(keyword in message_text for keyword in ("立即分析", "现在分析", "马上分析", "immediate", "analyze now"))
    results = [ingest_url(url, immediate=wants_immediate and len(urls) == 1, env_file=env_file, conn=conn, fetcher=fetcher) for url in urls]
    if wants_immediate and len(urls) == 1:
        return results[0]
    queued_count = sum(1 for item in results if item.get("status") == "queued")
    duplicate_count = sum(1 for item in results if item.get("status") == "duplicate")
    failed_count = sum(1 for item in results if item.get("status") not in {"queued", "duplicate"})
    return {
        "status": "queued" if queued_count else "partial_failed",
        "message": f"已处理 {len(results)} 个链接：入队 {queued_count}，重复 {duplicate_count}，失败 {failed_count}",
        "results": results,
    }


def send_digest(
    *,
    env_file: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
    runner: Callable[..., Any] | None = None,
    telegram_sender: Callable[..., dict[str, Any]] | None = None,
    batch_date: str | None = None,
) -> dict[str, Any]:
    config = load_config(env_file)
    database = _ensure_conn(config, conn)
    config = _sync_runtime_settings(config, database)
    queued_rows = list_articles_by_status(database, "queued", limit=config.max_digest_items)
    if not queued_rows:
        return {"status": "empty", "message_count": 0, "article_ids": []}
    article_ids = [int(row["id"]) for row in queued_rows]
    payloads = [article_row_to_payload(row) for row in queued_rows]
    mark_date = batch_date or local_today(config.digest_tz)
    messages = build_digest_messages(payloads, batch_date=mark_date, max_chars=config.max_message_chars)
    update_articles_status(database, article_ids, "sending")
    try:
        delivery = deliver_messages(
            messages,
            config=config,
            runner=runner or subprocess.run,
            telegram_sender=telegram_sender or send_via_telegram_bot,
        )
    except Exception as exc:
        update_articles_status(database, article_ids, "send_failed")
        record_delivery(
            database,
            batch_date=mark_date,
            article_ids=article_ids,
            target_chat_id=config.telegram_chat_id or config.openclaw_target or "unknown",
            target_thread_id=config.telegram_thread_id,
            message_count=len(messages),
            delivery_method="failed",
            delivery_status="failed",
            error_message=str(exc),
        )
        return {"status": "failed", "error_message": str(exc), "article_ids": article_ids}
    update_articles_status(database, article_ids, "sent")
    record_delivery(
        database,
        batch_date=mark_date,
        article_ids=article_ids,
        target_chat_id=config.telegram_chat_id or config.openclaw_target or "unknown",
        target_thread_id=config.telegram_thread_id,
        message_count=len(messages),
        delivery_method=delivery["delivery_method"],
        delivery_status="sent",
        external_message_ids=delivery["external_message_ids"],
    )
    return {
        "status": "sent",
        "article_ids": article_ids,
        "message_count": len(messages),
        "delivery_method": delivery["delivery_method"],
        "messages": messages,
    }
