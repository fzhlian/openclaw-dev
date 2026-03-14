#!/usr/bin/env python3
"""根据关键词和站点生成检索查询列表。"""

from __future__ import annotations

import argparse
import sys
from urllib.parse import urlparse


def split_items(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for part in value.split(","):
            item = part.strip()
            if item:
                items.append(item)
    return items


def normalize_site(site: str) -> str:
    candidate = site.strip()
    if "://" in candidate:
        parsed = urlparse(candidate)
        candidate = parsed.netloc or parsed.path
    candidate = candidate.split("/")[0].strip().lower()
    if not candidate:
        raise ValueError(f"无效站点: {site}")
    return candidate


def build_queries(keywords: list[str], sites: list[str]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for site in sites:
        domain = normalize_site(site)
        for keyword in keywords:
            query = f"site:{domain} {keyword.strip()}"
            if query not in seen:
                seen.add(query)
                queries.append(query)
    return queries


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    keywords = split_items(args.keyword)
    sites = split_items(args.site)

    if not keywords:
        print("缺少关键词，请至少提供一个 --keyword。", file=sys.stderr)
        return 1
    if not sites:
        print("缺少站点，请至少提供一个 --site。", file=sys.stderr)
        return 1

    try:
        queries = build_queries(keywords, sites)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for query in queries:
        print(query)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
