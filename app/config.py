from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from app.utils import ensure_dir, load_env, resolve_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(slots=True)
class AppConfig:
    root_dir: Path
    workspace_dir: Path
    provided_keys: frozenset[str]
    db_path: Path
    data_dir: Path
    raw_html_dir: Path
    extracted_text_dir: Path
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    telegram_thread_id: str | None
    digest_schedule: str
    digest_tz: str
    send_mode: str
    max_digest_items: int
    max_message_chars: int
    openclaw_bin: str
    openclaw_channel: str | None
    openclaw_account: str | None
    openclaw_agent: str | None
    openclaw_target: str | None
    openclaw_extra_args: list[str]


def load_config(env_path: str | Path | None = None) -> AppConfig:
    root_dir = PROJECT_ROOT
    values = load_env(root_dir, Path(env_path) if env_path else None)
    tracked_keys = {
        "OPENCLAW_WORKSPACE",
        "ARTICLE_DIGEST_DB",
        "ARTICLE_DIGEST_RAW_HTML_DIR",
        "ARTICLE_DIGEST_TEXT_DIR",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TELEGRAM_THREAD_ID",
        "DIGEST_SCHEDULE",
        "DIGEST_TZ",
        "SEND_MODE",
        "MAX_DIGEST_ITEMS",
        "MAX_MESSAGE_CHARS",
        "OPENCLAW_MESSAGE_BIN",
        "OPENCLAW_MESSAGE_CHANNEL",
        "OPENCLAW_MESSAGE_ACCOUNT",
        "OPENCLAW_AGENT",
        "OPENCLAW_MESSAGE_TARGET",
        "OPENCLAW_MESSAGE_EXTRA_ARGS",
    }
    workspace_dir = resolve_path(root_dir, values.get("OPENCLAW_WORKSPACE", str(root_dir)))
    db_path = resolve_path(root_dir, values.get("ARTICLE_DIGEST_DB", "./data/article_digest.db"))
    data_dir = db_path.parent
    raw_html_dir = resolve_path(root_dir, values.get("ARTICLE_DIGEST_RAW_HTML_DIR", "./data/raw_html"))
    extracted_text_dir = resolve_path(root_dir, values.get("ARTICLE_DIGEST_TEXT_DIR", "./data/extracted_text"))
    ensure_dir(data_dir)
    ensure_dir(raw_html_dir)
    ensure_dir(extracted_text_dir)
    return AppConfig(
        root_dir=root_dir,
        workspace_dir=workspace_dir,
        provided_keys=frozenset(key for key in tracked_keys if key in values),
        db_path=db_path,
        data_dir=data_dir,
        raw_html_dir=raw_html_dir,
        extracted_text_dir=extracted_text_dir,
        telegram_bot_token=values.get("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=values.get("TELEGRAM_CHAT_ID") or None,
        telegram_thread_id=values.get("TELEGRAM_THREAD_ID") or None,
        digest_schedule=values.get("DIGEST_SCHEDULE", "30 22 * * *"),
        digest_tz=values.get("DIGEST_TZ", "Asia/Taipei"),
        send_mode=values.get("SEND_MODE", "auto").lower(),
        max_digest_items=int(values.get("MAX_DIGEST_ITEMS", "10")),
        max_message_chars=int(values.get("MAX_MESSAGE_CHARS", "3500")),
        openclaw_bin=values.get("OPENCLAW_MESSAGE_BIN", "openclaw"),
        openclaw_channel=values.get("OPENCLAW_MESSAGE_CHANNEL", "telegram"),
        openclaw_account=values.get("OPENCLAW_MESSAGE_ACCOUNT") or None,
        openclaw_agent=values.get("OPENCLAW_AGENT") or None,
        openclaw_target=values.get("OPENCLAW_MESSAGE_TARGET") or values.get("TELEGRAM_CHAT_ID") or None,
        openclaw_extra_args=shlex.split(values.get("OPENCLAW_MESSAGE_EXTRA_ARGS", "")),
    )
