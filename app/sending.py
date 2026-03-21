from __future__ import annotations

import subprocess
from typing import Any, Callable

from app.config import AppConfig
from app.telegram_fallback import send_via_telegram_bot


class DeliveryError(RuntimeError):
    pass


def build_openclaw_command(config: AppConfig, text: str) -> list[str]:
    if not config.openclaw_target:
        raise DeliveryError("缺少 OPENCLAW_MESSAGE_TARGET 或 TELEGRAM_CHAT_ID")
    command = [config.openclaw_bin, "message", "send"]
    if config.openclaw_channel:
        command += ["--channel", config.openclaw_channel]
    if config.openclaw_account:
        command += ["--account", config.openclaw_account]
    command += ["--target", config.openclaw_target, "--message", text]
    if config.telegram_thread_id and config.openclaw_channel == "telegram":
        command += ["--thread-id", config.telegram_thread_id]
    command += config.openclaw_extra_args
    return command


def send_via_openclaw(
    text: str,
    *,
    config: AppConfig,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    command = build_openclaw_command(config, text)
    result = runner(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {"command": command, "stdout": getattr(result, "stdout", ""), "stderr": getattr(result, "stderr", "")}


def deliver_messages(
    messages: list[str],
    *,
    config: AppConfig,
    runner: Callable[..., Any] = subprocess.run,
    telegram_sender: Callable[..., dict[str, Any]] = send_via_telegram_bot,
) -> dict[str, Any]:
    if not messages:
        return {"delivery_method": "none", "external_message_ids": []}
    external_message_ids: list[str] = []
    used_fallback = False
    primary_attempted = False
    for message in messages:
        delivered = False
        if config.send_mode in {"auto", "openclaw"}:
            primary_attempted = True
            try:
                send_via_openclaw(message, config=config, runner=runner)
                delivered = True
            except Exception:
                if config.send_mode == "openclaw":
                    raise
        if not delivered:
            if config.send_mode == "openclaw":
                raise DeliveryError("OpenClaw 主动消息发送失败")
            if not config.telegram_bot_token or not config.telegram_chat_id:
                raise DeliveryError("缺少 Telegram Bot fallback 所需的 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID")
            response = telegram_sender(
                config.telegram_bot_token,
                config.telegram_chat_id,
                message,
                thread_id=config.telegram_thread_id,
            )
            message_id = response.get("result", {}).get("message_id")
            if message_id is not None:
                external_message_ids.append(str(message_id))
            used_fallback = True
    if used_fallback and primary_attempted:
        method = "openclaw_message+telegram_bot_fallback"
    elif used_fallback:
        method = "telegram_bot_fallback"
    else:
        method = "openclaw_message"
    return {"delivery_method": method, "external_message_ids": external_message_ids}

