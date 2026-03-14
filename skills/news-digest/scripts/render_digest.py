#!/usr/bin/env python3
"""将过滤后的 news-digest 结果渲染为最终 Markdown 输出。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_TIME_LABEL = "时间未标注"
DEFAULT_LIMITATIONS = "来源受限、时间缺失或覆盖不足时，结论仅基于当前检索结果。"
DEFAULT_NEXT_STEP = "如需更高覆盖，可放宽时间范围、补充来源或显式开启扩词。"


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
        if title:
            items.append(f"- {title}")
    return items or ["- 未形成足够结果，暂不输出趋势摘要"]


def render_articles(results: list[dict]) -> list[str]:
    lines: list[str] = ["## 文章清单"]
    if not results:
        lines.append("- 暂无可输出结果")
        return lines

    for index, item in enumerate(results, start=1):
        title = str(item.get("title", "未命名条目")).strip() or "未命名条目"
        snippet = str(item.get("snippet", "")).strip() or "（无摘要）"
        source = (
            str(item.get("matchedDomain", "")).strip()
            or str(item.get("sourceDomain", "")).strip()
            or "来源未标注"
        )
        published_at = str(item.get("publishedAt", "")).strip() or DEFAULT_TIME_LABEL
        url = str(item.get("url", "")).strip() or "（无链接）"

        lines.append(f"{index}. **{title}**")
        lines.append(f"   - 摘要：{snippet}")
        lines.append(f"   - 来源：{source} ｜ 时间：{published_at}")
        lines.append(f"   - 链接：{url}")
        lines.append("")

    if lines[-1] == "":
        lines.pop()
    return lines


def render_parameters(args: argparse.Namespace) -> list[str]:
    return [
        "## 检索参数",
        f"- 关键词：{args.keywords or '（未提供）'}",
        f"- 网站：{args.sites or '（未提供）'}",
        f"- 时间范围：{args.time_range or '（未提供）'}",
        f"- 结果数：{args.limit if args.limit is not None else '（未提供）'}",
    ]


def render_limitations(args: argparse.Namespace) -> list[str]:
    return [
        "## 局限与建议",
        f"- 局限：{args.limitations}",
        f"- 建议下一步：{args.next_step}",
    ]


def build_markdown(payload: dict, args: argparse.Namespace) -> str:
    results = payload.get("results", [])
    lines: list[str] = ["## 摘要总览"]
    lines.extend(render_overview(results, max_items=args.overview_limit))
    lines.append("")
    lines.extend(render_articles(results))
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
    parser.add_argument("--limit", type=int, help="结果数，展示在参数区")
    parser.add_argument("--overview-limit", type=int, default=3, help="摘要总览条数，默认 3")
    parser.add_argument("--limitations", default=DEFAULT_LIMITATIONS, help="局限说明")
    parser.add_argument("--next-step", default=DEFAULT_NEXT_STEP, help="下一步建议")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.overview_limit < 1:
        print("--overview-limit 必须 >= 1", file=sys.stderr)
        return 1

    try:
        payload = load_payload(args.input)
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(build_markdown(payload, args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
