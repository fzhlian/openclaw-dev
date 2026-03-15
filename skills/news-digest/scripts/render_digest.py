#!/usr/bin/env python3
"""将过滤后的 news-digest 结果渲染为最终 Markdown 输出。"""

from __future__ import annotations

import argparse
import sys

from news_digest_normalize import (
    DEFAULT_LIMIT,
    DEFAULT_LANGUAGE,
    MAX_LIMIT,
    DEFAULT_TIME_RANGE,
    FLAT_OUTPUT_MODE,
    GROUPED_OUTPUT_MODE,
    dedupe_casefolded_items,
    extract_results_payload,
    join_display_items,
    load_json_file,
    normalize_frequency,
    normalize_host_value,
    normalize_limit_value,
    normalize_language,
    normalize_output_mode,
    normalize_site_items,
    normalize_site_value,
    normalize_time_range,
    split_list_items,
    validate_frequency_value,
    validate_language_value,
    validate_limit_value,
    validate_output_mode_value,
)
DEFAULT_TIME_LABEL = "时间未标注"
DEFAULT_LIMITATIONS = "来源受限、时间缺失或覆盖不足时，结论仅基于当前检索结果。"
DEFAULT_NEXT_STEP = "如需更高覆盖，可放宽时间范围、补充来源或显式开启扩词。"
TOPIC_KEYS = ("topic", "queryTopic", "keyword", "query")
SUMMARY_KEYS = ("snippetZh", "summaryZh", "snippet", "summary")


def split_csv(value: str) -> list[str]:
    return split_list_items([value])


def dedupe_keywords(items: list[str]) -> list[str]:
    return dedupe_casefolded_items(items)


def pick_source_label(item: dict) -> str:
    for key in ("matchedDomain", "sourceDomain"):
        value = str(item.get(key, "")).strip()
        if not value:
            continue
        try:
            return normalize_site_value(value)
        except ValueError:
            continue
    return normalize_host_value(str(item.get("url", "")).strip())


def normalize_topics_display(value: str) -> str:
    items = dedupe_keywords(split_csv(value))
    return join_display_items(items)


def normalize_sites_display(value: str) -> str:
    items = split_csv(value)
    return join_display_items(normalize_site_items(items))


def load_payload(path: str) -> dict:
    data = load_json_file(path)
    return extract_results_payload(data)["payload"]


def render_overview(results: list[dict], max_items: int) -> list[str]:
    items: list[str] = []
    for item in results[:max_items]:
        title = str(item.get("title", "")).strip()
        source = pick_source_label(item)
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
    url = str(item.get("url", "")).strip()
    source = pick_source_label(item) or "来源未标注"
    published_at = str(item.get("publishedAt", "")).strip() or DEFAULT_TIME_LABEL
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
    frequency = normalize_frequency(args.frequency)
    output_mode = normalize_output_mode(
        args.output_mode,
        default_on_blank=FLAT_OUTPUT_MODE,
    )
    time_range = normalize_time_range(args.time_range) or DEFAULT_TIME_RANGE
    keywords = normalize_topics_display(args.keywords)
    sites = normalize_sites_display(args.sites)
    limit = normalize_limit_value(args.limit, default_limit=DEFAULT_LIMIT)
    language = normalize_language(args.language)
    return [
        "## 检索参数",
        f"- 关键词：{keywords or '（未提供）'}",
        f"- 网站：{sites or '（未提供）'}",
        f"- 时间范围：{time_range}",
        f"- 频率：{frequency or '（未提供）'}",
        f"- 结果数：{limit}",
        f"- 输出模式：{output_mode}",
        f"- 输出语言：{language}",
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
    output_mode = normalize_output_mode(
        args.output_mode,
        default_on_blank=FLAT_OUTPUT_MODE,
    )
    effective_limit = normalize_limit_value(args.limit, default_limit=DEFAULT_LIMIT)
    results = results[:effective_limit]

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
    try:
        validate_limit_value(args.limit, max_limit=MAX_LIMIT, allow_none=True)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.overview_limit < 1:
        print("--overview-limit 必须 >= 1", file=sys.stderr)
        return 1
    normalized_frequency = normalize_frequency(args.frequency)
    normalized_output_mode = normalize_output_mode(
        args.output_mode,
        default_on_blank=FLAT_OUTPUT_MODE,
    )
    normalized_language = normalize_language(args.language)
    try:
        validate_frequency_value(normalized_frequency)
        validate_output_mode_value(normalized_output_mode)
        validate_language_value(normalized_language)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        payload = load_payload(args.input)
        args.output_mode = normalized_output_mode
        args.frequency = normalized_frequency
        args.language = normalized_language
        print(build_markdown(payload, args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
