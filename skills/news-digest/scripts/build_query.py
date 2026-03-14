#!/usr/bin/env python3
"""根据关键词和站点生成检索查询列表。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ENGLISH_DOMAINS = {
    "bbc.com",
    "nytimes.com",
    "dw.com",
    "rfi.fr",
    "reuters.com",
    "apnews.com",
}

# 中文关键词 -> 英文主词 + 相关扩展词
CN_TO_EN_EXPANSIONS: dict[str, list[str]] = {
    "贪官": ["corruption", "graft", "anti-corruption", "official misconduct"],
    "伊朗": ["Iran", "Iranian"],
    "任命": ["appointment", "nomination", "cabinet reshuffle"],
    "战争": ["war", "conflict", "military strike"],
    "ai": ["AI", "artificial intelligence", "machine learning"],
}

# 中文关键词 -> 中文相关扩展词
CN_EXPANSIONS: dict[str, list[str]] = {
    "贪官": ["腐败", "反腐", "官员违纪"],
    "伊朗": ["伊朗局势", "德黑兰"],
    "任命": ["人事任命", "提名", "改组"],
    "战争": ["冲突", "战事", "军事打击"],
    "ai": ["人工智能", "机器学习", "大模型"],
}


def split_items(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for part in value.split(","):
            item = part.strip()
            if item:
                items.append(item)
    return items


def load_list_file(path: str) -> list[str]:
    file = Path(path)
    if not file.exists():
        raise ValueError(f"文件不存在: {path}")
    items: list[str] = []
    for line in file.read_text(encoding="utf-8").splitlines():
        row = line.strip()
        if not row or row.startswith("#"):
            continue
        items.extend(split_items([row]))
    return items


def normalize_site(site: str) -> str:
    candidate = site.strip()
    if "://" in candidate:
        parsed = urlparse(candidate)
        candidate = parsed.netloc or parsed.path
    candidate = candidate.split("/")[0].strip().lower()
    if candidate.startswith("www."):
        candidate = candidate[4:]
    if not candidate:
        raise ValueError(f"无效站点: {site}")
    return candidate


def is_english_site(domain: str) -> bool:
    return any(domain == base or domain.endswith(f".{base}") for base in ENGLISH_DOMAINS)


def keyword_seed(keyword: str) -> str:
    return keyword.strip().lower()


def expand_keyword(keyword: str, english_mode: bool) -> list[str]:
    seed = keyword_seed(keyword)

    if english_mode and seed in CN_TO_EN_EXPANSIONS:
        return CN_TO_EN_EXPANSIONS[seed]
    if not english_mode and seed in CN_EXPANSIONS:
        return [keyword.strip(), *CN_EXPANSIONS[seed]]

    # 英文模式下保留原词并做少量通用扩展
    if english_mode:
        if seed == "ai":
            return ["AI", "artificial intelligence", "machine learning"]
        return [keyword.strip()]

    return [keyword.strip()]


def expand_keywords(keywords: list[str], english_mode: bool) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        for item in expand_keyword(keyword, english_mode):
            term = item.strip()
            if not term:
                continue
            marker = term.lower()
            if marker not in seen:
                seen.add(marker)
                results.append(term)
    return results


def build_queries(
    keywords: list[str],
    sites: list[str],
    excludes: list[str],
    auto_expand: bool,
    auto_english: bool,
) -> tuple[list[str], dict[str, list[str]]]:
    queries: list[str] = []
    seen: set[str] = set()
    suffix = " ".join(f'-"{item}"' for item in excludes)
    keyword_plan: dict[str, list[str]] = {}

    for site in sites:
        domain = normalize_site(site)
        english_mode = auto_english and is_english_site(domain)
        words = expand_keywords(keywords, english_mode) if auto_expand else keywords
        keyword_plan[domain] = words

        for keyword in words:
            core = f"site:{domain} {keyword.strip()}".strip()
            query = f"{core} {suffix}".strip() if suffix else core
            if query not in seen:
                seen.add(query)
                queries.append(query)

    return queries, keyword_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="输入关键词和站点，输出检索查询列表。"
    )
    parser.add_argument(
        "-k",
        "--keyword",
        action="append",
        default=[],
        help="关键词，可重复传入，也支持逗号分隔",
    )
    parser.add_argument(
        "-s",
        "--site",
        action="append",
        default=[],
        help="站点域名，可重复传入，也支持逗号分隔",
    )
    parser.add_argument(
        "--keyword-file",
        help="关键词文件（每行一个，支持逗号分隔，# 开头视为注释）",
    )
    parser.add_argument(
        "--site-file",
        help="站点文件（每行一个，支持逗号分隔，# 开头视为注释）",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        action="append",
        default=[],
        help='排除词，可重复传入，也支持逗号分隔（输出为 -"词"）',
    )
    parser.add_argument(
        "--expand",
        action="store_true",
        help="显式开启关键词扩展",
    )
    parser.add_argument(
        "--auto-english",
        action="store_true",
        help="对已知英文站点显式开启关键词英文化",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式，默认 text",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    keywords = split_items(args.keyword)
    sites = split_items(args.site)
    excludes = split_items(args.exclude)

    try:
        if args.keyword_file:
            keywords.extend(load_list_file(args.keyword_file))
        if args.site_file:
            sites.extend(load_list_file(args.site_file))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    keywords = list(dict.fromkeys(item.strip() for item in keywords if item.strip()))
    sites = list(dict.fromkeys(item.strip() for item in sites if item.strip()))

    if not keywords:
        print("缺少关键词，请至少提供一个 --keyword 或 --keyword-file。", file=sys.stderr)
        return 1
    if not sites:
        print("缺少站点，请至少提供一个 --site 或 --site-file。", file=sys.stderr)
        return 1

    try:
        queries, keyword_plan = build_queries(
            keywords=keywords,
            sites=sites,
            excludes=excludes,
            auto_expand=args.expand,
            auto_english=args.auto_english,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.format == "json":
        print(
            json.dumps(
                {
                    "queries": queries,
                    "keywordPlan": keyword_plan,
                    "autoExpand": args.expand,
                    "autoEnglish": args.auto_english,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for query in queries:
            print(query)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
