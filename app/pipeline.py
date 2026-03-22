from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from app.analysis import assess_ai_likelihood, assess_credibility, summarize_threads
from app.config import AppConfig, load_config
from app.db import (
    article_row_to_payload,
    connect_db,
    create_article_stub,
    get_article_by_id,
    get_article_by_hash,
    get_latest_article,
    get_latest_ready_article,
    get_settings,
    init_db,
    list_articles_by_status,
    list_favorite_articles,
    mark_article_status,
    record_delivery,
    READY_ARTICLE_STATUSES,
    reset_article_for_retry,
    set_article_favorite,
    set_settings,
    update_article_success,
    update_articles_status,
)
from app.digest import (
    build_digest_messages,
    format_favorite_detail,
    format_favorites_list,
    format_processing_failure,
    format_single_article,
)
from app.extraction import ExtractionError, extract_article
from app.schema import validate_article_payload
from app.scheduler import install_systemd_timer, resolve_env_path
from app.sending import deliver_messages
from app.telegram_fallback import send_via_telegram_bot
from app.translation import localize_article_for_display, normalize_error_message_to_chinese
from app.utils import domain_from_url, extract_urls, local_today, normalize_url, url_hash, utc_now_iso


WECHAT_RETRY_MARKERS = (
    "轻触查看原文",
    "向上滑动看下一个",
    "微信扫一扫可打开此内容",
    "使用完整服务",
    "轻点两下取消赞",
    "轻点两下取消在看",
)
仅入队关键词 = (
    "晚上统一发给我",
    "统一发给我",
    "加入队列",
    "待发送",
    "稍后发送",
    "定时发送",
    "晚点发",
    "晚点统一发",
)
立即查看关键词 = ("立即分析", "现在分析", "马上分析", "analyze now", "immediate")
延迟发送触发词 = (
    "发给我",
    "发送给我",
    "推送给我",
    "再发",
    "再发送",
    "再推送",
    "发我",
    "发送",
    "推送",
    "整理后的",
    "整理结果",
)
立即推送关键词 = ("提前推送", "立刻推送", "立即推送", "马上推送", "推送文章", "整理好的文章给我", "把整理好的文章给我")
定时推送关键词 = ("开启定时推送", "定时发送", "定时推送", "每天")
收藏关键词 = ("收藏这篇", "收藏刚才这篇", "收藏最近一篇", "加入收藏", "收藏文章", "收藏 ")
取消收藏关键词 = ("取消收藏", "移出收藏", "删除收藏")
查看收藏关键词 = ("查看收藏", "回看收藏", "我的收藏", "收藏列表", "收藏夹")
可收藏状态 = {"queued", "sending", "sent", "send_failed", "duplicate"}
定时入队模式值 = "scheduled"
即时发送模式值 = "immediate"
默认摘要定时cron = "30 22 * * *"


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


def _should_retry_existing_payload(url: str, payload: dict[str, Any]) -> bool:
    if domain_from_url(url) != "mp.weixin.qq.com":
        return False
    haystacks = [payload.get("title") or "", payload.get("summary") or "", *payload.get("main_threads", [])]
    combined = "\n".join(part for part in haystacks if part).strip()
    if not combined:
        return False
    return any(marker in combined for marker in WECHAT_RETRY_MARKERS)


def _当前发送模式(database: sqlite3.Connection) -> str:
    settings = get_settings(database)
    mode = settings.get("digest_delivery_mode", "").strip().lower()
    if mode:
        return mode
    stored_schedule = settings.get("digest_schedule", "").strip()
    if stored_schedule and stored_schedule != 默认摘要定时cron:
        return 定时入队模式值
    return 即时发送模式值


def _已配置发送能力(config: AppConfig) -> bool:
    if config.openclaw_target:
        return True
    return bool(config.telegram_bot_token and config.telegram_chat_id)


def _发送处理异常通知(
    *,
    article_id: int,
    url: str,
    stage: str,
    error_message: str,
    config: AppConfig,
    database: sqlite3.Connection,
    runner: Callable[..., Any] | None = None,
    telegram_sender: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    通知消息 = format_processing_failure(url=url, stage=stage, error_message=error_message)
    批次日期 = local_today(config.digest_tz)
    try:
        发送结果 = deliver_messages(
            [通知消息],
            config=config,
            runner=runner or subprocess.run,
            telegram_sender=telegram_sender or send_via_telegram_bot,
        )
    except Exception as exc:
        record_delivery(
            database,
            batch_date=批次日期,
            article_ids=[article_id],
            target_chat_id=config.telegram_chat_id or config.openclaw_target or "unknown",
            target_thread_id=config.telegram_thread_id,
            message_count=1,
            delivery_method="failed",
            delivery_status="failed",
            error_message=str(exc),
        )
        return {
            "status_notice_sent": False,
            "status_notice_error": str(exc),
            "status_notice_message": 通知消息,
        }

    record_delivery(
        database,
        batch_date=批次日期,
        article_ids=[article_id],
        target_chat_id=config.telegram_chat_id or config.openclaw_target or "unknown",
        target_thread_id=config.telegram_thread_id,
        message_count=1,
        delivery_method=发送结果["delivery_method"],
        delivery_status="sent",
        external_message_ids=发送结果["external_message_ids"],
    )
    return {
        "status_notice_sent": True,
        "status_notice_message": 通知消息,
        "status_notice_delivery_method": 发送结果["delivery_method"],
        "status_notice_external_message_ids": 发送结果["external_message_ids"],
    }


def _发送单篇文章(
    *,
    article_id: int,
    payload: dict[str, Any],
    config: AppConfig,
    database: sqlite3.Connection,
    runner: Callable[..., Any] | None = None,
    telegram_sender: Callable[..., dict[str, Any]] | None = None,
    mark_before_send: bool = True,
    mark_sent_on_success: bool = True,
    mark_failed_on_error: bool = True,
) -> dict[str, Any]:
    单篇消息 = format_single_article(payload)
    if mark_before_send:
        mark_article_status(database, article_id, "sending", error_message=None)
    批次日期 = local_today(config.digest_tz)
    try:
        发送结果 = deliver_messages(
            [单篇消息],
            config=config,
            runner=runner or subprocess.run,
            telegram_sender=telegram_sender or send_via_telegram_bot,
        )
    except Exception as exc:
        if mark_failed_on_error:
            mark_article_status(database, article_id, "send_failed", error_message=str(exc))
        record_delivery(
            database,
            batch_date=批次日期,
            article_ids=[article_id],
            target_chat_id=config.telegram_chat_id or config.openclaw_target or "unknown",
            target_thread_id=config.telegram_thread_id,
            message_count=1,
            delivery_method="failed",
            delivery_status="failed",
            error_message=str(exc),
        )
        return {
            "status": "send_failed",
            "message": f"已完成抓取和分析，但推送到 Telegram 失败：{normalize_error_message_to_chinese(str(exc))}",
            "error_message": str(exc),
            "article": payload,
            "article_message": 单篇消息,
        }
    if mark_sent_on_success:
        mark_article_status(database, article_id, "sent", error_message=None)
    record_delivery(
        database,
        batch_date=批次日期,
        article_ids=[article_id],
        target_chat_id=config.telegram_chat_id or config.openclaw_target or "unknown",
        target_thread_id=config.telegram_thread_id,
        message_count=1,
        delivery_method=发送结果["delivery_method"],
        delivery_status="sent",
        external_message_ids=发送结果["external_message_ids"],
    )
    payload["status"] = "sent"
    return {
        "status": "sent",
        "message": "已完成抓取、分析并推送到 Telegram。",
        "article": payload,
        "article_message": 单篇消息,
        "delivery_method": 发送结果["delivery_method"],
        "external_message_ids": 发送结果["external_message_ids"],
    }


def _提取文章编号(message_text: str) -> int | None:
    match = re.search(r"(?:文章|编号|id)?\s*[:=：]?\s*(\d{1,9})(?!\d)", message_text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _是显式文章编号引用(message_text: str) -> bool:
    return bool(re.search(r"(?:文章|编号|id)\s*[:=：]?\s*\d{1,9}(?!\d)", message_text, re.IGNORECASE))


def _标准化短命令(message_text: str) -> str:
    return re.sub(r"[。！!？?\s]+$", "", message_text.strip())


def _是收藏列表命令(message_text: str, urls: list[str]) -> bool:
    if urls:
        return False
    if not any(keyword in message_text for keyword in 查看收藏关键词):
        return False
    return _提取文章编号(message_text) is None


def _是简易收藏详情命令(message_text: str, urls: list[str]) -> bool:
    if urls:
        return False
    normalized = _标准化短命令(message_text)
    return bool(
        re.fullmatch(r"\d{1,9}", normalized)
        or re.fullmatch(r"(?:回看|看)\s*[:=：]?\s*\d{1,9}", normalized)
    )


def _是收藏详情命令(message_text: str, urls: list[str]) -> bool:
    if _是简易收藏详情命令(message_text, urls):
        return True
    if "回看收藏" in message_text:
        return bool(urls or _提取文章编号(message_text) is not None)
    if "查看收藏" in message_text and (_提取文章编号(message_text) is not None or bool(urls)):
        return True
    return False


def _是取消收藏命令(message_text: str) -> bool:
    return any(keyword in message_text for keyword in 取消收藏关键词)


def _是收藏命令(message_text: str) -> bool:
    if _是取消收藏命令(message_text):
        return False
    if _标准化短命令(message_text) == "收藏":
        return True
    return any(keyword in message_text for keyword in 收藏关键词)


def _提取延迟发送秒数(message_text: str) -> int | None:
    normalized = _标准化短命令(message_text)
    if not normalized or not any(token in normalized for token in 延迟发送触发词):
        return None

    def _解析中文数字(token: str) -> int | None:
        token = token.strip()
        if not token:
            return None
        if token.isdigit():
            return int(token)
        mapping = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if token == "十":
            return 10
        if "十" in token:
            left, _, right = token.partition("十")
            tens = mapping.get(left, 1) if left else 1
            ones = mapping.get(right, 0) if right else 0
            return tens * 10 + ones
        if "百" in token:
            left, _, right = token.partition("百")
            hundreds = mapping.get(left, 1) if left else 1
            if not right:
                return hundreds * 100
            tail = _解析中文数字(right)
            return None if tail is None else hundreds * 100 + tail
        value = 0
        for char in token:
            if char not in mapping:
                return None
            value = value * 10 + mapping[char]
        return value

    def _匹配时长(unit: str) -> int | None:
        for pattern in (
            rf"(?<!\d)(\d{{1,3}}|[零一二两三四五六七八九十百]{{1,6}})\s*{unit}后",
            rf"过\s*(\d{{1,3}}|[零一二两三四五六七八九十百]{{1,6}})\s*{unit}",
            rf"延迟\s*(\d{{1,3}}|[零一二两三四五六七八九十百]{{1,6}})\s*{unit}",
            rf"延后\s*(\d{{1,3}}|[零一二两三四五六七八九十百]{{1,6}})\s*{unit}",
        ):
            match = re.search(pattern, normalized)
            if not match:
                continue
            value = _解析中文数字(match.group(1))
            if value is not None and value > 0:
                return value
        return None

    minute_value = _匹配时长("分钟")
    if minute_value is not None:
        return minute_value * 60

    hour_value = _匹配时长("小时")
    if hour_value is not None:
        return hour_value * 3600

    return None


def _是立即推送命令(message_text: str, urls: list[str]) -> bool:
    if urls:
        return False
    normalized = _标准化短命令(message_text)
    return any(keyword in normalized for keyword in 立即推送关键词)


def _提取定时推送时间(message_text: str) -> tuple[int, int] | None:
    normalized = _标准化短命令(message_text)
    if not normalized:
        return None
    if not any(keyword in normalized for keyword in 定时推送关键词):
        return None

    match = re.search(r"(?<!\d)([01]?\d|2[0-3])\s*[:：点时]\s*([0-5]?\d)?(?!\d)", normalized)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        return hour, minute

    if "开启定时推送" in normalized:
        return 22, 30

    return None


def _格式化每日时间(hour: int, minute: int) -> str:
    return f"每天 {hour:02d}:{minute:02d}"


def _构建每日cron(hour: int, minute: int) -> str:
    return f"{minute} {hour} * * *"


def _格式化延迟时长(delay_seconds: int) -> str:
    if delay_seconds % 3600 == 0:
        hours = delay_seconds // 3600
        return f"{hours} 小时后"
    minutes = max(1, delay_seconds // 60)
    return f"{minutes} 分钟后"


def _文章可发送(row: sqlite3.Row | None) -> bool:
    if row is None:
        return False
    status = str(row["status"] or "")
    summary = str(row["summary"] or "").strip()
    return status in READY_ARTICLE_STATUSES and bool(summary)


def _默认延迟发送调度(
    article_id: int,
    delay_seconds: int,
    *,
    env_file: str | Path | None = None,
) -> None:
    script = Path(__file__).resolve().parents[1] / "skills" / "article-digest" / "scripts" / "delayed_send.py"
    args = [
        sys.executable or "python3",
        str(script),
        "--article-id",
        str(article_id),
        "--delay-seconds",
        str(delay_seconds),
    ]
    if env_file:
        args.extend(["--env-file", str(env_file)])
    subprocess.Popen(
        args,
        cwd=str(Path(__file__).resolve().parents[1]),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _安排延迟发送(
    article_id: int,
    delay_seconds: int,
    *,
    env_file: str | Path | None = None,
    delay_scheduler: Callable[..., Any] | None = None,
) -> None:
    scheduler = delay_scheduler or _默认延迟发送调度
    scheduler(article_id, delay_seconds, env_file=env_file)


def _查找目标文章(
    database: sqlite3.Connection,
    message_text: str,
    urls: list[str],
    *,
    仅限收藏: bool = False,
) -> sqlite3.Row | None:
    for url in urls:
        try:
            normalized = normalize_url(url)
        except ValueError:
            continue
        row = get_article_by_hash(database, url_hash(normalized))
        if row is None:
            continue
        if 仅限收藏 and not bool(row["is_favorite"]):
            continue
        return row

    article_id = _提取文章编号(message_text)
    if article_id is not None:
        if 仅限收藏 and not _是显式文章编号引用(message_text):
            favorite_rows = list_favorite_articles(database)
            if 1 <= article_id <= len(favorite_rows):
                return favorite_rows[article_id - 1]
        row = get_article_by_id(database, article_id)
        if row is None:
            return None
        if 仅限收藏 and not bool(row["is_favorite"]):
            return None
        return row

    latest = get_latest_ready_article(database, only_favorite=仅限收藏)
    if latest is None and not 仅限收藏:
        latest = get_latest_article(database, only_favorite=False)
    if latest is None:
        return None
    if 仅限收藏 and not bool(latest["is_favorite"]):
        return None
    return latest


def _文章可收藏(row: sqlite3.Row | None) -> bool:
    if row is None:
        return False
    status = str(row["status"] or "")
    summary = str(row["summary"] or "").strip()
    return status in 可收藏状态 and bool(summary)


def _收藏文章(
    database: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    is_favorite: bool,
) -> dict[str, Any]:
    if is_favorite and not _文章可收藏(row):
        return {
            "status": "favorite_not_ready",
            "message": "这篇文章还没有整理完成，暂时不能收藏；请等正文分析完成后再试。",
        }
    article_id = int(row["id"])
    was_favorite = bool(row["is_favorite"])
    set_article_favorite(database, article_id, is_favorite=is_favorite)
    updated_row = get_article_by_id(database, article_id)
    assert updated_row is not None
    payload = article_row_to_payload(updated_row)
    validate_article_payload(payload)
    if is_favorite:
        if was_favorite:
            message = f"这篇文章已经在收藏夹里：{payload['title']}"
        else:
            message = f"已收藏：{payload['title']}"
        status = "favorited"
    else:
        if was_favorite:
            message = f"已取消收藏：{payload['title']}"
        else:
            message = f"这篇文章原本就不在收藏夹里：{payload['title']}"
        status = "unfavorited"
    return {"status": status, "message": message, "article": payload}


def _收藏结果中的文章(
    database: sqlite3.Connection,
    results: list[dict[str, Any]],
) -> tuple[int, int]:
    新增收藏数 = 0
    已收藏数 = 0
    for item in results:
        article = item.get("article")
        article_id = None
        if isinstance(article, dict) and article.get("id") is not None:
            article_id = int(article["id"])
        elif item.get("url"):
            try:
                normalized = normalize_url(str(item["url"]))
            except ValueError:
                normalized = ""
            if normalized:
                row = get_article_by_hash(database, url_hash(normalized))
                if row is not None:
                    article_id = int(row["id"])
        if article_id is None:
            continue
        row = get_article_by_id(database, article_id)
        if row is None:
            continue
        if not _文章可收藏(row):
            continue
        was_favorite = bool(row["is_favorite"])
        set_article_favorite(database, article_id, is_favorite=True)
        updated_row = get_article_by_id(database, article_id)
        if updated_row is None:
            continue
        updated_payload = article_row_to_payload(updated_row)
        validate_article_payload(updated_payload)
        if isinstance(article, dict):
            article.update(updated_payload)
        if was_favorite:
            已收藏数 += 1
        else:
            新增收藏数 += 1
    return 新增收藏数, 已收藏数


def _构建收藏列表响应(database: sqlite3.Connection) -> dict[str, Any]:
    rows = list_favorite_articles(database)
    payloads = [article_row_to_payload(row) for row in rows]
    for payload in payloads:
        validate_article_payload(payload)
    return {
        "status": "favorites_list",
        "message": format_favorites_list(payloads),
        "articles": payloads,
    }


def _构建收藏详情响应(database: sqlite3.Connection, row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        return {"status": "favorite_not_found", "message": "没有找到对应的收藏文章。"}
    payload = article_row_to_payload(row)
    validate_article_payload(payload)
    return {
        "status": "favorite_detail",
        "message": format_favorite_detail(payload),
        "article": payload,
    }


def _查找延迟发送目标文章(
    database: sqlite3.Connection,
    message_text: str,
) -> sqlite3.Row | None:
    article_id = _提取文章编号(message_text) if _是显式文章编号引用(message_text) else None
    if article_id is not None:
        row = get_article_by_id(database, article_id)
        if row is not None:
            return row

    latest = get_latest_ready_article(database, only_favorite=False)
    if latest is not None:
        return latest
    return get_latest_article(database, only_favorite=False)


def _更新定时推送配置(
    *,
    hour: int,
    minute: int,
    config: AppConfig,
    database: sqlite3.Connection,
    env_file: str | Path | None = None,
    schedule_installer: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    cron_expr = _构建每日cron(hour, minute)
    set_settings(
        database,
        {
            "digest_schedule": cron_expr,
            "digest_delivery_mode": 定时入队模式值,
        },
    )
    installer = schedule_installer or install_systemd_timer
    env_path = str(resolve_env_path(config.root_dir, str(env_file or ".env")))
    try:
        installer(
            config.root_dir,
            cron_expr=cron_expr,
            env_file=env_path,
        )
    except Exception as exc:
        return {
            "status": "schedule_partial",
            "message": (
                f"已保存定时推送时间为{_格式化每日时间(hour, minute)}，"
                f"但系统定时器更新失败：{normalize_error_message_to_chinese(str(exc))}"
            ),
            "cron_expr": cron_expr,
        }
    return {
        "status": "schedule_updated",
        "message": f"已开启定时推送：{_格式化每日时间(hour, minute)}。",
        "cron_expr": cron_expr,
    }


def send_article_by_id(
    article_id: int,
    *,
    env_file: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
    runner: Callable[..., Any] | None = None,
    telegram_sender: Callable[..., dict[str, Any]] | None = None,
    wait_ready_seconds: int = 0,
) -> dict[str, Any]:
    config = load_config(env_file)
    database = _ensure_conn(config, conn)
    config = _sync_runtime_settings(config, database)
    deadline = time.monotonic() + max(0, wait_ready_seconds)

    while True:
        row = get_article_by_id(database, article_id)
        if row is None:
            return {"status": "article_not_found", "message": "没有找到要发送的文章。"}
        if _文章可发送(row):
            break
        status = str(row["status"] or "")
        if status in {"extract_failed", "analysis_failed"}:
            return {"status": status, "message": "这篇文章整理失败，当前不能再次发送。"}
        if time.monotonic() >= deadline:
            return {"status": "article_not_ready", "message": "这篇文章还没有整理完成，请稍后再试。"}
        time.sleep(min(5, max(1, int(deadline - time.monotonic()))))

    payload = article_row_to_payload(row)
    validate_article_payload(payload)
    status = str(row["status"] or "")
    should_update_status = status in {"queued", "send_failed"}
    result = _发送单篇文章(
        article_id=article_id,
        payload=payload,
        config=config,
        database=database,
        runner=runner,
        telegram_sender=telegram_sender,
        mark_before_send=should_update_status,
        mark_sent_on_success=should_update_status,
        mark_failed_on_error=should_update_status,
    )
    if not should_update_status and result.get("status") == "sent":
        result["message"] = "已按延迟要求重新推送到 Telegram。"
    return result


def ingest_url(
    url: str,
    *,
    immediate: bool = False,
    仅入队: bool = False,
    env_file: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
    fetcher: Callable[[str], str] | None = None,
    runner: Callable[..., Any] | None = None,
    telegram_sender: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = load_config(env_file)
    database = _ensure_conn(config, conn)
    config = _sync_runtime_settings(config, database)
    normalized = normalize_url(url)
    article_hash = url_hash(normalized)
    existing = get_article_by_hash(database, article_hash)
    if existing:
        existing_status = str(existing["status"] or "")
        existing_payload = article_row_to_payload(existing)
        if _should_retry_existing_payload(normalized, existing_payload):
            article_id = int(existing["id"])
            reset_article_for_retry(database, article_id, fetched_at=utc_now_iso(), status="extracting")
        elif existing_status == "send_failed":
            mark_article_status(database, int(existing["id"]), "queued", error_message=None)
            payload = article_row_to_payload(get_article_by_hash(database, article_hash))
            validate_article_payload(payload)
            return {"status": "queued", "message": "已重新加入待发送列表", "article": payload}
        elif existing_status in {"extract_failed", "analysis_failed"}:
            article_id = int(existing["id"])
            reset_article_for_retry(database, article_id, fetched_at=utc_now_iso(), status="extracting")
        else:
            validate_article_payload(existing_payload)
            return {"status": "duplicate", "url": normalized, "article": existing_payload}
    else:
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
        result = {
            "status": "extract_failed",
            "url": normalized,
            "error_message": str(exc),
            "message": f"正文抓取失败：{normalize_error_message_to_chinese(str(exc))}",
        }
        if not 仅入队 and _已配置发送能力(config):
            result.update(
                _发送处理异常通知(
                    article_id=article_id,
                    url=normalized,
                    stage="extract_failed",
                    error_message=str(exc),
                    config=config,
                    database=database,
                    runner=runner,
                    telegram_sender=telegram_sender,
                )
            )
        return result
    try:
        credibility = assess_credibility(article)
        ai_likelihood = assess_ai_likelihood(article)
        threads = summarize_threads(article)
        article, localized_summary, localized_threads = localize_article_for_display(
            article,
            summary=threads["summary"],
            main_threads=threads["main_threads"],
        )
    except Exception as exc:
        mark_article_status(database, article_id, "analysis_failed", error_message=str(exc))
        result = {
            "status": "analysis_failed",
            "url": normalized,
            "error_message": str(exc),
            "message": f"正文分析失败：{normalize_error_message_to_chinese(str(exc))}",
        }
        if not 仅入队 and _已配置发送能力(config):
            result.update(
                _发送处理异常通知(
                    article_id=article_id,
                    url=normalized,
                    stage="analysis_failed",
                    error_message=str(exc),
                    config=config,
                    database=database,
                    runner=runner,
                    telegram_sender=telegram_sender,
                )
            )
        return result
    update_article_success(
        database,
        article_id,
        article=article.to_dict(),
        summary=localized_summary,
        main_threads=localized_threads,
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
        if 仅入队 or not _已配置发送能力(config):
            return payload
        发送结果 = _发送单篇文章(
            article_id=article_id,
            payload=payload,
            config=config,
            database=database,
            runner=runner,
            telegram_sender=telegram_sender,
        )
        发送结果["inline_message"] = payload["message"]
        return 发送结果
    if not 仅入队 and _已配置发送能力(config):
        return _发送单篇文章(
            article_id=article_id,
            payload=payload,
            config=config,
            database=database,
            runner=runner,
            telegram_sender=telegram_sender,
        )
    return {"status": "queued", "message": "已加入待发送列表", "article": payload}


def ingest_message(
    message_text: str,
    *,
    env_file: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
    fetcher: Callable[[str], str] | None = None,
    runner: Callable[..., Any] | None = None,
    telegram_sender: Callable[..., dict[str, Any]] | None = None,
    delay_scheduler: Callable[..., Any] | None = None,
    schedule_installer: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    config = load_config(env_file)
    database = _ensure_conn(config, conn)
    config = _sync_runtime_settings(config, database)
    urls = extract_urls(message_text)
    delay_seconds = _提取延迟发送秒数(message_text)
    scheduled_time = _提取定时推送时间(message_text)
    delivery_mode = _当前发送模式(database)
    if _是收藏列表命令(message_text, urls):
        return _构建收藏列表响应(database)
    if _是收藏详情命令(message_text, urls):
        return _构建收藏详情响应(
            database,
            _查找目标文章(database, message_text, urls, 仅限收藏=True),
        )
    if _是取消收藏命令(message_text):
        row = _查找目标文章(database, message_text, urls)
        if row is None:
            return {"status": "favorite_not_found", "message": "当前没有找到可取消收藏的文章。"}
        return _收藏文章(database, row, is_favorite=False)
    if _是收藏命令(message_text) and not urls:
        row = _查找目标文章(database, message_text, urls)
        if row is None:
            return {"status": "favorite_not_found", "message": "当前没有找到可收藏的文章，请先收录文章或附上链接。"}
        return _收藏文章(database, row, is_favorite=True)
    if not urls and scheduled_time is not None:
        hour, minute = scheduled_time
        return _更新定时推送配置(
            hour=hour,
            minute=minute,
            config=config,
            database=database,
            env_file=env_file,
            schedule_installer=schedule_installer,
        )
    if _是立即推送命令(message_text, urls):
        result = send_digest(
            env_file=env_file,
            conn=database,
            runner=runner,
            telegram_sender=telegram_sender,
        )
        if result.get("status") == "empty":
            return {"status": "empty", "message": "当前没有已整理待推送的文章。"}
        if result.get("status") == "sent":
            count = len(result.get("article_ids", []))
            return {
                "status": "sent",
                "message": f"已提前推送 {count} 篇已整理文章到 Telegram。",
                **result,
            }
        return result
    if not urls and delay_seconds is not None:
        row = _查找延迟发送目标文章(database, message_text)
        if row is None:
            return {"status": "article_not_found", "message": "当前没有找到可延迟发送的文章。"}
        if str(row["status"] or "") in {"extract_failed", "analysis_failed"}:
            return {"status": "article_not_ready", "message": "这篇文章整理失败，当前不能安排延迟发送。"}
        _安排延迟发送(
            int(row["id"]),
            delay_seconds,
            env_file=env_file,
            delay_scheduler=delay_scheduler,
        )
        return {
            "status": "scheduled",
            "message": f"已开始处理，{_格式化延迟时长(delay_seconds)}再把整理后的发给你。",
            "article": article_row_to_payload(row),
        }
    if not urls:
        return {"status": "no_url", "message": "未识别到可处理的链接"}
    wants_immediate = any(keyword in message_text for keyword in 立即查看关键词)
    wants_queue = (
        any(keyword in message_text for keyword in 仅入队关键词)
        or delay_seconds is not None
        or (delivery_mode == 定时入队模式值 and not wants_immediate)
    )
    wants_favorite = _是收藏命令(message_text)
    results = [
        ingest_url(
            url,
            immediate=False,
            仅入队=wants_queue,
            env_file=env_file,
            conn=database,
            fetcher=fetcher,
            runner=runner,
            telegram_sender=telegram_sender,
        )
        for url in urls
    ]
    if delay_seconds is not None:
        scheduled_count = 0
        for item in results:
            article = item.get("article")
            article_id = int(article["id"]) if isinstance(article, dict) and article.get("id") is not None else None
            if article_id is None:
                continue
            if item.get("status") in {"extract_failed", "analysis_failed"}:
                continue
            _安排延迟发送(
                article_id,
                delay_seconds,
                env_file=env_file,
                delay_scheduler=delay_scheduler,
            )
            scheduled_count += 1
        failed_count = sum(1 for item in results if item.get("status") in {"extract_failed", "analysis_failed", "send_failed"})
        return {
            "status": "scheduled" if scheduled_count else "partial_failed",
            "message": (
                f"已开始处理 {len(results)} 个链接，预计 {_格式化延迟时长(delay_seconds)}发送整理结果："
                f"已安排 {scheduled_count}，失败 {failed_count}"
            ),
            "results": results,
        }
    新增收藏数 = 0
    已收藏数 = 0
    if wants_favorite:
        新增收藏数, 已收藏数 = _收藏结果中的文章(database, results)
    if wants_immediate and len(urls) == 1:
        item = results[0]
        if wants_favorite:
            收藏提示 = (
                "已加入收藏夹。"
                if 新增收藏数
                else "这篇文章已经在收藏夹里。"
                if 已收藏数
                else "当前未能完成收藏。"
            )
            if item.get("message"):
                item["message"] = f"{item['message']}\n\n{收藏提示}"
            else:
                item["message"] = 收藏提示
        if item.get("status") in {"sent", "send_failed"}:
            return item
        article = item.get("article")
        if isinstance(article, dict):
            item["message"] = format_single_article(article)
            if wants_favorite:
                item["message"] = f"{item['message']}\n\n收藏状态：已加入收藏夹。"
        return item
    已推送数 = sum(1 for item in results if item.get("status") == "sent")
    queued_count = sum(1 for item in results if item.get("status") == "queued")
    duplicate_count = sum(1 for item in results if item.get("status") == "duplicate")
    failed_count = sum(1 for item in results if item.get("status") in {"extract_failed", "analysis_failed", "send_failed"})
    if failed_count:
        overall_status = "partial_failed" if (已推送数 or queued_count or duplicate_count) else "send_failed"
    elif 已推送数:
        overall_status = "sent"
    elif queued_count:
        overall_status = "queued"
    elif duplicate_count:
        overall_status = "duplicate"
    else:
        overall_status = "partial_failed"
    收藏附注 = ""
    if wants_favorite:
        收藏附注 = f"，新增收藏 {新增收藏数}，已在收藏夹 {已收藏数}"
    return {
        "status": overall_status,
        "message": f"已处理 {len(results)} 个链接：已推送 {已推送数}，入队 {queued_count}，重复 {duplicate_count}，失败 {failed_count}{收藏附注}",
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
