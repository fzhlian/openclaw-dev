#!/usr/bin/env python3
"""根据关键词和站点生成检索查询列表。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


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


def build_queries(keywords: list[str], sites: list[str], excludes: list[str]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    suffix = " ".join(f'-"{item}"' for item in excludes)

    for site in sites:
        domain = normalize_site(site)
        for keyword in keywords:
            core = f"site:{domain} {keyword.strip()}".strip()
            query = f"{core} {suffix}".strip() if suffix else core
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
        queries = build_queries(keywords, sites, excludes)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps({"queries": queries}, ensure_ascii=False, indent=2))
    else:
        for query in queries:
            print(query)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
