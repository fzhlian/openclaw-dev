#!/usr/bin/env python3
"""Shared normalization helpers for news-digest scripts."""

from __future__ import annotations

import re
import json
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_LANGUAGE = "中文"
SUPPORTED_LANGUAGE = "中文"
DEFAULT_LIMIT = 5
MAX_LIMIT = 20
DEFAULT_TIME_RANGE = "最近 7 天"
FLAT_OUTPUT_MODE = "摘要总览 + 逐条清单"
GROUPED_OUTPUT_MODE = "按主题分组+逐条"
SUPPORTED_OUTPUT_MODES = (FLAT_OUTPUT_MODE, GROUPED_OUTPUT_MODE)

EDGE_WRAPPER_PUNCTUATION = "\"'“”‘’()（）[]【】<>《》"
PARAM_EDGE_PUNCTUATION = ".,，。;；:：!！?？" + EDGE_WRAPPER_PUNCTUATION
KEYWORD_EDGE_PUNCTUATION = ".,，。;；:：!！?？" + EDGE_WRAPPER_PUNCTUATION
SITE_EDGE_PUNCTUATION = ".,，。;；:：!！?？" + EDGE_WRAPPER_PUNCTUATION

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
    "每天一次": "每日",
    "一天一次": "每日",
    "每天1次": "每日",
    "一天1次": "每日",
    "日报": "每日",
    "每周": "每周",
    "每周一次": "每周",
    "每星期": "每周",
    "每星期一次": "每周",
    "一周一次": "每周",
    "每周1次": "每周",
    "每星期1次": "每周",
    "一周1次": "每周",
    "周报": "每周",
}
SUPPORTED_FREQUENCIES = ("一次性", "每日", "每周")

TIME_RANGE_ALIASES = {
    "24h": "最近 24 小时",
    "1d": "最近 1 天",
    "7d": "最近 7 天",
    "14d": "最近 14 天",
    "30d": "最近 30 天",
    "24小时": "最近 24 小时",
    "1天": "最近 1 天",
    "一天": "最近 1 天",
    "今天": "最近 1 天",
    "今日": "最近 1 天",
    "昨天": "最近 1 天",
    "昨日": "最近 1 天",
    "本周": "最近 7 天",
    "本星期": "最近 7 天",
    "本礼拜": "最近 7 天",
    "本月": "最近 30 天",
    "这周": "最近 7 天",
    "这星期": "最近 7 天",
    "这礼拜": "最近 7 天",
    "这一周": "最近 7 天",
    "这个月": "最近 30 天",
    "这月": "最近 30 天",
    "这一月": "最近 30 天",
    "上周": "最近 7 天",
    "上星期": "最近 7 天",
    "上礼拜": "最近 7 天",
    "上一周": "最近 7 天",
    "上一星期": "最近 7 天",
    "上个月": "最近 30 天",
    "上月": "最近 30 天",
    "上一月": "最近 30 天",
    "上一个月": "最近 30 天",
    "7天": "最近 7 天",
    "14天": "最近 14 天",
    "30天": "最近 30 天",
    "1月": "最近 30 天",
    "一月": "最近 30 天",
    "1周": "最近 7 天",
    "2周": "最近 14 天",
    "1个月": "最近 30 天",
    "一周": "最近 7 天",
    "两周": "最近 14 天",
    "一个月": "最近 30 天",
    "最近24小时": "最近 24 小时",
    "最近1天": "最近 1 天",
    "最近7天": "最近 7 天",
    "最近14天": "最近 14 天",
    "最近30天": "最近 30 天",
    "最近1月": "最近 30 天",
    "最近一月": "最近 30 天",
    "最近1周": "最近 7 天",
    "最近2周": "最近 14 天",
    "最近1个月": "最近 30 天",
    "近24小时": "最近 24 小时",
    "近1天": "最近 1 天",
    "近7天": "最近 7 天",
    "近14天": "最近 14 天",
    "近30天": "最近 30 天",
    "近1月": "最近 30 天",
    "近一月": "最近 30 天",
    "近1周": "最近 7 天",
    "近2周": "最近 14 天",
    "近1个月": "最近 30 天",
    "近一周": "最近 7 天",
    "近两周": "最近 14 天",
    "近一个月": "最近 30 天",
    "过去24小时": "最近 24 小时",
    "过去1天": "最近 1 天",
    "过去7天": "最近 7 天",
    "过去14天": "最近 14 天",
    "过去30天": "最近 30 天",
    "过去1月": "最近 30 天",
    "过去一月": "最近 30 天",
    "过去1周": "最近 7 天",
    "过去2周": "最近 14 天",
    "过去1个月": "最近 30 天",
    "最近一天": "最近 1 天",
    "过去一天": "最近 1 天",
    "最近一周": "最近 7 天",
    "过去一周": "最近 7 天",
    "最近两周": "最近 14 天",
    "过去两周": "最近 14 天",
    "最近一个月": "最近 30 天",
    "过去一个月": "最近 30 天",
}


def normalize_output_mode(
    value: str,
    *,
    flat_output_mode: str,
    grouped_output_mode: str,
    default_on_blank: str,
) -> str:
    text = value.strip().strip(PARAM_EDGE_PUNCTUATION)
    if not text:
        return default_on_blank
    compact = "".join(text.split()).replace("＋", "+")
    if compact in FLAT_OUTPUT_MODE_ALIASES:
        return flat_output_mode
    if compact in GROUPED_OUTPUT_MODE_ALIASES:
        return grouped_output_mode
    return text


def normalize_time_range(value: str) -> str:
    text = value.strip().strip(PARAM_EDGE_PUNCTUATION)
    if not text:
        return ""
    compact = "".join(text.split()).lower()
    return TIME_RANGE_ALIASES.get(compact, text)


def normalize_frequency(value: str) -> str:
    text = value.strip().strip(PARAM_EDGE_PUNCTUATION)
    if not text:
        return ""
    compact = "".join(text.split())
    return FREQUENCY_ALIASES.get(compact, FREQUENCY_ALIASES.get(text, text))


def normalize_language(value: str, *, default_language: str = DEFAULT_LANGUAGE) -> str:
    return value.strip().strip(PARAM_EDGE_PUNCTUATION) or default_language


def split_list_items(values: list[str], *, dedupe: bool = True) -> list[str]:
    items: list[str] = []
    for value in values:
        normalized = (
            value.replace("，", ",")
            .replace("、", ",")
            .replace("；", ",")
            .replace(";", ",")
            .replace("|", ",")
            .replace("／", ",")
        )
        normalized = re.sub(r"\s+/\s*|\s*/\s+", ",", normalized)
        for part in normalized.split(","):
            item = part.strip()
            if item:
                items.append(item)
    return list(dict.fromkeys(items)) if dedupe else items


def dedupe_casefolded_items(
    items: list[str],
    *,
    strip_chars: str = KEYWORD_EDGE_PUNCTUATION,
) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip().strip(strip_chars)
        if not normalized:
            continue
        marker = normalized.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(normalized)
    return deduped


def normalize_host_value(value: str) -> str:
    raw = str(value).strip().strip(SITE_EDGE_PUNCTUATION)
    parsed = urlparse(raw if "://" in raw else f"//{raw}", scheme="https")
    candidate = (parsed.hostname or "").strip().strip(SITE_EDGE_PUNCTUATION).lower()
    if candidate.startswith("www."):
        candidate = candidate[4:]
    return candidate


def normalize_site_value(
    value: str,
    *,
    aliases: Mapping[str, str] | None = None,
) -> str:
    candidate = normalize_host_value(value)
    if not candidate:
        raise ValueError(f"无效站点: {value}")
    if aliases:
        alias = aliases.get(candidate)
        if alias:
            return alias
    if "." not in candidate:
        raise ValueError(f"站点需使用域名，如 bbc.com；收到: {value}")
    return candidate


def read_text_file(
    path: str,
    *,
    missing_prefix: str = "文件不存在",
    read_error_prefix: str = "读取文件失败",
) -> str:
    file = Path(path)
    if not file.exists():
        raise ValueError(f"{missing_prefix}: {path}")
    try:
        return file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{read_error_prefix}: {path}") from exc


def load_json_file(
    path: str,
    *,
    read_error_prefix: str = "读取输入 JSON 失败",
    parse_error_prefix: str = "解析输入 JSON 失败",
):
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{read_error_prefix}: {path}") from exc
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{parse_error_prefix}: {path}") from exc


def normalize_limit_value(value: int | None, *, default_limit: int = DEFAULT_LIMIT) -> int:
    return default_limit if value is None else value


def validate_limit_value(
    value: int | None,
    *,
    max_limit: int = MAX_LIMIT,
    allow_none: bool = False,
) -> None:
    if value is None:
        if allow_none:
            return
        raise ValueError("--limit 缺失")
    if value < 1:
        raise ValueError("--limit 必须 >= 1")
    if value > max_limit:
        raise ValueError(f"--limit 必须 <= {max_limit}")


def validate_frequency_value(value: str) -> None:
    if value and value not in SUPPORTED_FREQUENCIES:
        raise ValueError("--frequency 当前仅支持 一次性 / 每日 / 每周")


def validate_language_value(value: str) -> None:
    if value != SUPPORTED_LANGUAGE:
        raise ValueError(f"--language 当前仅支持 {SUPPORTED_LANGUAGE}")


def validate_output_mode_value(value: str) -> None:
    if value and value not in SUPPORTED_OUTPUT_MODES:
        raise ValueError(
            f"--output-mode 当前仅支持 {FLAT_OUTPUT_MODE} / {GROUPED_OUTPUT_MODE}"
        )
