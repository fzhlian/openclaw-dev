from __future__ import annotations

from typing import Iterable

from app.translation import normalize_error_message_to_chinese
from app.utils import truncate


def format_single_article(record: dict[str, object]) -> str:
    credibility = record["credibility"]  # type: ignore[index]
    ai_likelihood = record["ai_likelihood"]  # type: ignore[index]
    threads = record.get("main_threads", [])
    author = record.get("author") or "未知"
    published_at = record.get("published_at") or "未知"
    favorite_text = "已收藏" if record.get("is_favorite") else "未收藏"
    thread_lines = "\n".join(
        f"{index + 1}. {item}" for index, item in enumerate(list(threads)[:6])
    )
    return (
        f"{record['title']}\n\n"
        f"来源：{record['source']}\n"
        f"作者：{author}\n"
        f"发布时间：{published_at}\n"
        f"收藏状态：{favorite_text}\n"
        "\n"
        "一、核心摘要\n"
        f"{record['summary']}\n\n"
        "二、主要内容\n"
        f"{thread_lines}\n\n"
        "三、可信度评估\n"
        f"评分：{credibility['score']}/100（{credibility['level']}）\n"
        "\n"
        "四、AI 参与痕迹估算\n"
        f"评分：{ai_likelihood['score']}/100（{ai_likelihood['level']}）\n"
        "\n"
        "原文链接：\n"
        f"{record['url']}"
    )


def format_favorite_detail(record: dict[str, object]) -> str:
    credibility = record["credibility"]  # type: ignore[index]
    ai_likelihood = record["ai_likelihood"]  # type: ignore[index]
    threads = [str(item).strip() for item in list(record.get("main_threads", [])) if str(item).strip()]
    thread_lines = "\n".join(
        f"{index + 1}. {item}" for index, item in enumerate(threads[:6])
    ) or "1. 暂无整理结果。"
    published_at = record.get("published_at") or "未知"
    return (
        f"{record['title']}\n\n"
        f"来源：{record['source']}\n"
        f"发布时间：{published_at}\n"
        "\n"
        "核心摘要\n"
        f"{record['summary']}\n\n"
        "主要内容\n"
        f"{thread_lines}\n\n"
        f"可信度：{credibility['score']}/100（{credibility['level']}）\n"
        f"AI 参与度：{ai_likelihood['score']}/100（{ai_likelihood['level']}）\n\n"
        "原文链接：\n"
        f"{record['url']}"
    )


def format_processing_failure(
    *,
    url: str,
    stage: str,
    error_message: str,
    title: str | None = None,
) -> str:
    stage_label = {
        "extract_failed": "正文抓取失败",
        "analysis_failed": "正文分析失败",
        "send_failed": "消息推送失败",
    }.get(stage, "处理失败")
    header = f"【文章处理异常】{title}" if title else "【文章处理异常】"
    return (
        f"{header}\n\n"
        f"阶段：{stage_label}\n"
        f"链接：{url}\n"
        f"原因：{truncate(normalize_error_message_to_chinese(error_message or '未知错误'), 220)}"
    )

def format_digest_item(record: dict[str, object], index: int) -> str:
    credibility = record["credibility"]  # type: ignore[index]
    ai_likelihood = record["ai_likelihood"]  # type: ignore[index]
    main_thread = ""
    threads = list(record.get("main_threads", []))
    if threads:
        main_thread = threads[0]
    return (
        f"{index}）{record['title']}\n"
        f"- 来源：{record['source']}\n"
        f"- 可信度：{credibility['level']}（{credibility['score']}）\n"
        f"- AI 痕迹：{ai_likelihood['level']}（{ai_likelihood['score']}）\n"
        f"- 主要内容：{truncate(main_thread, 100)}\n"
        f"- 链接：{record['url']}\n"
    )


def format_favorites_list(records: Iterable[dict[str, object]]) -> str:
    items = list(records)
    if not items:
        return "当前还没有收藏文章。"
    lines = [f"共收藏 {len(items)} 篇："]
    for index, record in enumerate(items, start=1):
        favorited_at = record.get("favorited_at") or "未知时间"
        lines.append(
            "\n".join(
                [
                    f"{index}）{record['title']}",
                    f"来源：{record['source']}",
                    f"收藏时间：{favorited_at}",
                    f"当前状态：{record['status']}",
                    "原文链接：",
                    f"{record['url']}",
                ]
            )
        )
    lines.append("\n提示：直接回复数字、发送“回看2”，或发送“回看收藏 2”都可以。")
    return "\n\n".join(lines)


def split_long_block(block: str, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]
    lines = block.splitlines()
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}".strip() if current else line
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(line) <= max_chars:
            current = line
        else:
            start = 0
            while start < len(line):
                end = min(start + max_chars, len(line))
                chunks.append(line[start:end])
                start = end
            current = ""
    if current:
        chunks.append(current)
    return chunks


def build_digest_messages(
    records: Iterable[dict[str, object]],
    *,
    batch_date: str,
    max_chars: int,
) -> list[str]:
    items = list(records)
    if not items:
        return []
    header = f"【今日文章 Digest｜{batch_date}】\n\n共收录 {len(items)} 篇，以下为重点摘要：\n"
    messages: list[str] = []
    current = header
    for index, record in enumerate(items, start=1):
        block = format_digest_item(record, index)
        if len(current) + len(block) <= max_chars:
            current += ("\n" if not current.endswith("\n") else "") + block
            continue
        if current.strip() != header.strip():
            messages.append(current.strip())
            current = f"【今日文章 Digest｜{batch_date}｜续】\n\n"
        if len(current) + len(block) <= max_chars:
            current += block
            continue
        oversized_parts = split_long_block(block, max_chars - 10)
        for part in oversized_parts:
            if len(current) + len(part) > max_chars and current.strip():
                messages.append(current.strip())
                current = f"【今日文章 Digest｜{batch_date}｜续】\n\n"
            current += part + "\n"
    if current.strip():
        messages.append(current.strip())
    return messages
