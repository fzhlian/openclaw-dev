#!/usr/bin/env python3
"""将过滤后的 news-digest 结果渲染为最终 Markdown 输出。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_TIME_LABEL = "时间未标注"
DEFAULT_LIMITATIONS = "来源受限、时间缺失或覆盖不足时，结论仅基于当前检索结果。"
DEFAULT_NEXT_STEP = "如需更高覆盖，可放宽时间范围、补充来源或显式开启扩词。"
GROUPED_OUTPUT_MODE = "按主题分组+逐条"
FLAT_OUTPUT_MODE = "摘要总览 + 逐条清单"
DEFAULT_LANGUAGE = "中文"
SUPPORTED_LANGUAGE = "中文"
SUPPORTED_OUTPUT_MODES = (FLAT_OUTPUT_MODE, GROUPED_OUTPUT_MODE)
FLAT_OUTPUT_MODE_ALIASES = {"摘要总览+逐条清单", "摘要总览+逐条", "总览+逐条"}
GROUPED_OUTPUT_MODE_ALIASES = {"按主题分组+逐条", "按主题分组+逐条清单", "分组+逐条"}
FREQUENCY_ALIASES = {
    "一次性": "一次性",
    "一次": "一次性",
    "执行一次": "一次性",
    "跑一遍": "一次性",
    "先发一版": "一次性",
    "先跑一版": "一次性",
    "每日": "每日",
    "每天": "每日",
    "日报": "每日",
    "每周": "每周",
    "每星期": "每周",
    "周报": "每周",
}
SUPPORTED_FREQUENCIES = ("一次性", "每日", "每周")
TIME_RANGE_ALIASES = {
    "24h": "最近 24 小时",
    "1d": "最近 1 天",
    "7d": "最近 7 天",
    "14d": "最近 14 天",
    "30d": "最近 30 天",
}
TOPIC_KEYS = ("topic", "queryTopic", "keyword", "query")
SUMMARY_KEYS = ("snippetZh", "summaryZh", "snippet", "summary")


def normalize_output_mode(value: str) -> str:
    text = value.strip()
    if not text:
        return FLAT_OUTPUT_MODE
    compact = "".join(text.split())
    if compact in FLAT_OUTPUT_MODE_ALIASES:
        return FLAT_OUTPUT_MODE
    if compact in GROUPED_OUTPUT_MODE_ALIASES:
        return GROUPED_OUTPUT_MODE
    return text


def normalize_time_range(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    compact = "".join(text.split()).lower()
    return TIME_RANGE_ALIASES.get(compact, text)


def split_csv(value: str) -> list[str]:
    items: list[str] = []
    for part in value.split(","):
        item = part.strip()
        if item:
            items.append(item)
    return list(dict.fromkeys(items))


def normalize_site(value: str) -> str:
    candidate = value.strip()
    if "://" in candidate:
        parsed = urlparse(candidate)
        candidate = parsed.netloc or parsed.path
    candidate = candidate.split("/")[0].strip().lower()
    if candidate.startswith("www."):
        candidate = candidate[4:]
    if not candidate:
        raise ValueError(f"无效站点: {value}")
    if "." not in candidate:
        raise ValueError(f"站点需使用域名，如 bbc.com；收到: {value}")
    return candidate


def normalize_topics_display(value: str) -> str:
    items = split_csv(value)
    return "、".join(items)


def normalize_sites_display(value: str) -> str:
    items = split_csv(value)
    return "、".join(normalize_site(item) for item in items)


def load_payload(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data
    if isinstance(data, list):
        return {"results": data}
    raise ValueError("输入 JSON 必须是结果数组，或包含 results 数组")


def render_overview(results: list[dict], max_items: int) -> list[str]:
    items: list[str] = []
    for item in results[:max_items]:
        title = str(item.get("title", "")).strip()
        source = str(item.get("matchedDomain", "")).strip() or str(item.get("sourceDomain", "")).strip()
        snippet = ""
        for key in SUMMARY_KEYS:
            value = str(item.get(key, "")).strip()
            if value:
                snippet = value
                break
        summary = snippet[:80].rstrip("，、；： ") if snippet else "暂无摘要信息"

        if title:
            if source:
                items.append(f"- {title}（来源：{source}）：{summary}")
            else:
                items.append(f"- {title}：{summary}")
    return items or ["- 未形成足够结果，暂不输出趋势摘要"]


def validate_results(results: list[dict]) -> None:
    for index, item in enumerate(results, start=1):
        if not str(item.get("url", "")).strip():
            raise ValueError(f"第 {index} 条结果缺少 url，不能渲染最终摘要")
        if not str(item.get("title", "")).strip():
            raise ValueError(f"第 {index} 条结果缺少 title，不能渲染最终摘要")


def pick_topic(item: dict) -> str:
    for key in TOPIC_KEYS:
        value = str(item.get(key, "")).strip()
        if value:
            return value
    return ""


def render_article_item(item: dict, index: int) -> list[str]:
    title = str(item.get("title", "未命名条目")).strip() or "未命名条目"
    snippet = ""
    for key in SUMMARY_KEYS:
        value = str(item.get(key, "")).strip()
        if value:
            snippet = value
            break
    snippet = snippet or "（无摘要）"
    source = (
        str(item.get("matchedDomain", "")).strip()
        or str(item.get("sourceDomain", "")).strip()
        or "来源未标注"
    )
    published_at = str(item.get("publishedAt", "")).strip() or DEFAULT_TIME_LABEL
    url = str(item.get("url", "")).strip()
    return [
        f"{index}. **{title}**",
        f"   - 摘要：{snippet}",
        f"   - 来源：{source} ｜ 时间：{published_at}",
        f"   - 链接：{url}",
    ]



def render_articles(results: list[dict], output_mode: str) -> list[str]:
    lines: list[str] = ["## 文章清单"]
    if not results:
        lines.append("- 暂无可输出结果")
        return lines

    validate_results(results)

    if output_mode == GROUPED_OUTPUT_MODE:
        missing_topics = [str(index) for index, item in enumerate(results, start=1) if not pick_topic(item)]
        if missing_topics:
            raise ValueError(
                "按主题分组+逐条 模式要求每条结果包含 topic / queryTopic / keyword / query 字段"
            )
        groups: dict[str, list[dict]] = {}
        order: list[str] = []
        for item in results:
            topic = pick_topic(item)
            if topic not in groups:
                groups[topic] = []
                order.append(topic)
            groups[topic].append(item)

        for topic in order:
            lines.append(f"### {topic}")
            for index, item in enumerate(groups[topic], start=1):
                lines.extend(render_article_item(item, index))
                lines.append("")
            if lines[-1] == "":
                lines.pop()
            lines.append("")

        if lines[-1] == "":
            lines.pop()
        return lines

    for index, item in enumerate(results, start=1):
        lines.extend(render_article_item(item, index))
        lines.append("")

    if lines[-1] == "":
        lines.pop()
    return lines


def render_parameters(args: argparse.Namespace) -> list[str]:
    frequency = FREQUENCY_ALIASES.get(args.frequency.strip(), args.frequency.strip())
    output_mode = normalize_output_mode(args.output_mode)
    time_range = normalize_time_range(args.time_range)
    keywords = normalize_topics_display(args.keywords)
    sites = normalize_sites_display(args.sites)
    return [
        "## 检索参数",
        f"- 关键词：{keywords or '（未提供）'}",
        f"- 网站：{sites or '（未提供）'}",
        f"- 时间范围：{time_range or '（未提供）'}",
        f"- 频率：{frequency or '（未提供）'}",
        f"- 结果数：{args.limit if args.limit is not None else '（未提供）'}",
        f"- 输出模式：{output_mode}",
        f"- 输出语言：{args.language or DEFAULT_LANGUAGE}",
    ]


def render_limitations(args: argparse.Namespace) -> list[str]:
    return [
        "## 局限与建议",
        f"- 局限：{args.limitations}",
        f"- 建议下一步：{args.next_step}",
    ]


def render_discovered_results(payload: dict) -> list[str]:
    entries = payload.get("discoveredResults") or payload.get("findings") or []
    lines = ["## 已发现结果"]
    if not isinstance(entries, list) or not entries:
        lines.append("- 暂未拿到满足约束的可输出结果")
        return lines

    for entry in entries:
        if isinstance(entry, str):
            text = entry.strip()
            if text:
                lines.append(f"- {text}")
            continue

        if not isinstance(entry, dict):
            continue

        label = (
            str(entry.get("topic", "")).strip()
            or str(entry.get("title", "")).strip()
            or str(entry.get("site", "")).strip()
        )
        detail = (
            str(entry.get("summary", "")).strip()
            or str(entry.get("note", "")).strip()
            or str(entry.get("detail", "")).strip()
        )

        if label and detail:
            lines.append(f"- {label}：{detail}")
        elif label:
            lines.append(f"- {label}")
        elif detail:
            lines.append(f"- {detail}")

    if len(lines) == 1:
        lines.append("- 暂未拿到满足约束的可输出结果")
    return lines


def build_markdown(payload: dict, args: argparse.Namespace) -> str:
    results = payload.get("results", [])
    force_degraded = bool(payload.get("forceDegraded"))
    output_mode = normalize_output_mode(args.output_mode)

    if force_degraded or not results:
        lines: list[str] = []
        lines.extend(render_parameters(args))
        lines.append("")
        lines.extend(render_discovered_results(payload))
        lines.append("")
        lines.extend(render_limitations(args))
        return "\n".join(lines).strip() + "\n"

    lines = ["## 摘要总览"]
    lines.extend(render_overview(results, max_items=args.overview_limit))
    lines.append("")
    lines.extend(render_articles(results, output_mode=output_mode))
    lines.append("")
    lines.extend(render_parameters(args))
    lines.append("")
    lines.extend(render_limitations(args))
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将过滤后的 news-digest 结果渲染为 Markdown")
    parser.add_argument("--input", required=True, help="输入 JSON；支持数组或 {results:[...]} 结构")
    parser.add_argument("--keywords", default="", help="检索关键词，展示在参数区")
    parser.add_argument("--sites", default="", help="目标站点，展示在参数区")
    parser.add_argument("--time-range", default="", help="时间范围，展示在参数区")
    parser.add_argument(
        "--frequency",
        default="",
        help="更新频率，仅支持 一次性 / 每日 / 每周（支持自然表达归一化）",
    )
    parser.add_argument("--limit", type=int, help="结果数，展示在参数区")
    parser.add_argument(
        "--output-mode",
        default=FLAT_OUTPUT_MODE,
        help=f"输出模式，仅支持 {FLAT_OUTPUT_MODE} / {GROUPED_OUTPUT_MODE}",
    )
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="输出语言，当前仅支持中文")
    parser.add_argument("--overview-limit", type=int, default=3, help="摘要总览条数，默认 3")
    parser.add_argument("--limitations", default=DEFAULT_LIMITATIONS, help="局限与建议中的局限说明")
    parser.add_argument("--next-step", default=DEFAULT_NEXT_STEP, help="下一步建议")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.overview_limit < 1:
        print("--overview-limit 必须 >= 1", file=sys.stderr)
        return 1
    normalized_frequency = FREQUENCY_ALIASES.get(args.frequency.strip(), args.frequency.strip())
    if normalized_frequency and normalized_frequency not in SUPPORTED_FREQUENCIES:
        print("--frequency 当前仅支持 一次性 / 每日 / 每周", file=sys.stderr)
        return 1
    normalized_output_mode = normalize_output_mode(args.output_mode)
    if normalized_output_mode not in SUPPORTED_OUTPUT_MODES:
        print(
            f"--output-mode 当前仅支持 {FLAT_OUTPUT_MODE} / {GROUPED_OUTPUT_MODE}",
            file=sys.stderr,
        )
        return 1
    if (args.language.strip() or DEFAULT_LANGUAGE) != SUPPORTED_LANGUAGE:
        print(f"--language 当前仅支持 {SUPPORTED_LANGUAGE}", file=sys.stderr)
        return 1

    try:
        payload = load_payload(args.input)
        args.output_mode = normalized_output_mode
        print(build_markdown(payload, args))
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
