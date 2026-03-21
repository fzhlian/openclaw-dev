from __future__ import annotations

from typing import Iterable

from app.utils import truncate


DISCLAIMER_TEXT = "说明：可信度与 AI 痕迹均为启发式分析，不构成最终裁决。"


def format_single_article(record: dict[str, object]) -> str:
    credibility = record["credibility"]  # type: ignore[index]
    ai_likelihood = record["ai_likelihood"]  # type: ignore[index]
    threads = record.get("main_threads", [])
    author = record.get("author") or "未知"
    published_at = record.get("published_at") or "未知"
    thread_lines = "\n".join(
        f"{index + 1}. {item}" for index, item in enumerate(list(threads)[:6])
    )
    credibility_reasons = "\n".join(f"- {item}" for item in credibility["reasons"])  # type: ignore[index]
    credibility_risks = "\n".join(f"- {item}" for item in credibility["risks"])  # type: ignore[index]
    ai_reasons = "\n".join(f"- {item}" for item in ai_likelihood["reasons"])  # type: ignore[index]
    ai_limits = "\n".join(f"- {item}" for item in ai_likelihood["limitations"])  # type: ignore[index]
    return (
        f"【文章研判】{record['title']}\n\n"
        f"来源：{record['source']}\n"
        f"作者：{author}\n"
        f"发布时间：{published_at}\n"
        f"链接：{record['url']}\n\n"
        "一、核心摘要\n"
        f"{record['summary']}\n\n"
        "二、主要脉络\n"
        f"{thread_lines}\n\n"
        "三、可信度评估\n"
        f"评分：{credibility['score']}/100（{credibility['level']}）\n"
        f"依据：\n{credibility_reasons}\n"
        f"风险：\n{credibility_risks}\n\n"
        "四、AI 参与痕迹估算\n"
        f"评分：{ai_likelihood['score']}/100（{ai_likelihood['level']}）\n"
        f"依据：\n{ai_reasons}\n"
        f"限制：\n{ai_limits}\n\n"
        f"{DISCLAIMER_TEXT}"
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
        f"- 主线：{truncate(main_thread, 100)}\n"
        f"- 链接：{record['url']}\n"
    )


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
    footer = f"\n{DISCLAIMER_TEXT}"
    messages: list[str] = []
    current = header
    for index, record in enumerate(items, start=1):
        block = format_digest_item(record, index)
        if len(current) + len(block) + len(footer) <= max_chars:
            current += ("\n" if not current.endswith("\n") else "") + block
            continue
        if current.strip() != header.strip():
            messages.append((current + footer).strip())
            current = f"【今日文章 Digest｜{batch_date}｜续】\n\n"
        if len(current) + len(block) + len(footer) <= max_chars:
            current += block
            continue
        oversized_parts = split_long_block(block, max_chars - len(footer) - 10)
        for part in oversized_parts:
            if len(current) + len(part) + len(footer) > max_chars and current.strip():
                messages.append((current + footer).strip())
                current = f"【今日文章 Digest｜{batch_date}｜续】\n\n"
            current += part + "\n"
    if current.strip():
        messages.append((current + footer).strip())
    return messages

