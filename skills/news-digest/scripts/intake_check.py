#!/usr/bin/env python3
"""根据用户输入生成 news-digest 采集缺项追问与参数确认块。"""

from __future__ import annotations

import argparse
import json
from typing import Any

from news_digest_normalize import (
    DEFAULT_LIMIT,
    DEFAULT_LANGUAGE,
    DEFAULT_TIME_RANGE,
    FLAT_OUTPUT_MODE,
    GROUPED_OUTPUT_MODE,
    MAX_LIMIT,
    dedupe_casefolded_items,
    join_display_items,
    normalize_frequency,
    normalize_limit_value,
    normalize_language,
    normalize_site_items,
    normalize_output_mode,
    normalize_site_value,
    normalize_time_range,
    split_list_items,
    validate_frequency_value,
    validate_language_value,
    validate_limit_value,
    validate_output_mode_value,
)
SITE_ALIASES = {
    "bbc": "bbc.com",
    "bbc news": "bbc.com",
    "rfi": "rfi.fr",
    "dw": "dw.com",
    "deutsche welle": "dw.com",
    "nyt": "nytimes.com",
    "new york times": "nytimes.com",
    "纽约时报": "nytimes.com",
    "紐約時報": "nytimes.com",
    "华尔街见闻": "wallstreetcn.com",
    "華爾街見聞": "wallstreetcn.com",
}


def split_csv(values: list[str]) -> list[str]:
    return split_list_items(values)


def dedupe_keywords(items: list[str]) -> list[str]:
    return dedupe_casefolded_items(items)


def normalize_site(site: str) -> str:
    return normalize_site_value(site, aliases=SITE_ALIASES)


def ask_list(params: dict[str, Any]) -> list[str]:
    asks: list[str] = []
    if not params["topics"]:
        asks.append("你最想追踪哪几个主题？可先给 3-8 个关键词。")
    if not params["sites"]:
        asks.append("你希望限定哪些站点/媒体？如果不限定，我可先给高相关来源建议。")
    if not params["frequency"]:
        asks.append("这是一次性检索，还是要做日报/周报模板？")
    return asks


def normalize_params(args: argparse.Namespace) -> dict[str, Any]:
    topics = dedupe_keywords(split_csv(args.topic))
    sites = normalize_site_items(split_csv(args.site), aliases=SITE_ALIASES)
    return {
        "topics": topics,
        "sites": sites,
        "time_range": normalize_time_range(args.time_range),
        "frequency": normalize_frequency(args.frequency),
        "limit": normalize_limit_value(args.limit),
        "output_mode": normalize_output_mode(
            args.output_mode,
            default_on_blank="",
        ),
        "language": normalize_language(args.language),
        "defaults_applied": {
            "time_range": not bool(args.time_range.strip()),
            "output_mode": not bool(args.output_mode.strip()),
        },
    }


def to_confirm_block(params: dict[str, Any]) -> dict[str, str | int]:
    time_range = params["time_range"] or DEFAULT_TIME_RANGE
    output_mode = params["output_mode"] or FLAT_OUTPUT_MODE
    return {
        "关键词": join_display_items(params["topics"]) if params["topics"] else "（待确认）",
        "网站": join_display_items(params["sites"]) if params["sites"] else "（待确认）",
        "时间范围": time_range,
        "频率": params["frequency"] or "（待确认）",
        "结果数": params["limit"],
        "输出模式": output_mode,
        "输出语言": params["language"],
    }


def render_text(params: dict[str, Any], asks: list[str], confirm: dict[str, str | int]) -> str:
    lines: list[str] = []

    if asks:
        lines.append("## 缺项追问清单")
        for i, ask in enumerate(asks, start=1):
            lines.append(f"{i}. {ask}")
    else:
        lines.append("## 缺项追问清单")
        lines.append("- 无（可直接进入参数确认）")

    lines.append("")
    lines.append("## 参数确认")
    for k, v in confirm.items():
        lines.append(f"- {k}：{v}")

    defaults = []
    if params["defaults_applied"]["time_range"]:
        defaults.append(f"时间范围默认使用：{DEFAULT_TIME_RANGE}")
    if params["defaults_applied"]["output_mode"]:
        defaults.append(f"输出模式默认使用：{FLAT_OUTPUT_MODE}")

    if defaults:
        lines.append("")
        lines.append("## 默认值提示")
        for item in defaults:
            lines.append(f"- {item}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 news-digest 需求采集缺项清单与参数确认块")
    parser.add_argument("--topic", action="append", default=[], help="追踪主题，支持重复传入或逗号分隔")
    parser.add_argument("--site", action="append", default=[], help="来源站点，支持重复传入或逗号分隔")
    parser.add_argument("--time-range", default="", help="时间范围，如 最近 24 小时 / 7 天 / 30 天")
    parser.add_argument(
        "--frequency",
        default="",
        help="更新频率，仅支持 一次性 / 每日 / 每周（支持自然表达归一化）",
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="结果条数，默认 5")
    parser.add_argument(
        "--output-mode",
        default="",
        help=f"输出模式，仅支持 {FLAT_OUTPUT_MODE} / {GROUPED_OUTPUT_MODE}",
    )
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="输出语言，当前仅支持中文")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_limit_value(args.limit, max_limit=MAX_LIMIT)
    except ValueError as exc:
        raise SystemExit(str(exc))
    try:
        split_sites = split_csv(args.site)
        for site in split_sites:
            normalize_site(site)
    except ValueError as exc:
        raise SystemExit(str(exc))
    normalized_frequency = normalize_frequency(args.frequency)
    normalized_output_mode = normalize_output_mode(
        args.output_mode,
        default_on_blank="",
    )
    try:
        validate_frequency_value(normalized_frequency)
        validate_output_mode_value(normalized_output_mode)
        validate_language_value(normalize_language(args.language))
    except ValueError as exc:
        raise SystemExit(str(exc))

    params = normalize_params(args)
    asks = ask_list(params)
    confirm = to_confirm_block(params)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "missingQuestions": asks,
                    "confirm": confirm,
                    "defaultsApplied": params["defaults_applied"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_text(params, asks, confirm))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
