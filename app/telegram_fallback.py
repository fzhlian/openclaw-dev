from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen


class TelegramFallbackError(RuntimeError):
    pass


def send_via_telegram_bot(
    token: str,
    chat_id: str,
    text: str,
    *,
    thread_id: str | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if thread_id:
        payload["message_thread_id"] = int(thread_id) if str(thread_id).isdigit() else thread_id
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise TelegramFallbackError(body.get("description", "Telegram Bot API 返回失败"))
    return body

