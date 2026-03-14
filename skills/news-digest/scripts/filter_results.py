#!/usr/bin/env python3
"""按目标站点过滤并去重 news-digest 候选结果。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

SNIPPET_KEYS = ("snippet", "description", "summary", "content")
PUBLISHED_AT_KEYS = ("publishedAt", "published_at", "date", "time")
SOURCE_DOMAIN_KEYS = ("sourceDomain", "domain", "site", "source")


def normalize_site(site: str) -> str:
    candidate = site.strip().lower()
    if "://" in candidate:
        parsed = urlparse(candidate)
        candidate = parsed.netloc or parsed.path
    candidate = candidate.split("/")[0].strip()
    if candidate.startswith("www."):
        candidate = candidate[4:]
    if not candidate:
        raise ValueError(f"无效站点: {site}")
    if "." not in candidate:
        raise ValueError(f"站点需使用域名，如 bbc.com；收到: {site}")
    return candidate


def normalize_host(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.netloc or parsed.path).split("/")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")


TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_name",
    "utm_cid",
    "utm_reader",
    "utm_referrer",
    "utm_brand",
    "utm_pubreferrer",
    "gclid",
    "fbclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "cmpid",
}


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    host = normalize_host(url)
    path = re.sub(r"/+", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
    ]
    query = urlencode(query_pairs, doseq=True)
    suffix = f"?{query}" if query else ""
    return f"{scheme}://{host}{path}{suffix}"


def normalize_title(title: str) -> str:
    text = title.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff ]+", "", text)
    return text.strip()


def split_items(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for part in value.replace("，", ",").replace("、", ",").split(","):
            item = part.strip()
            if item:
                items.append(item)
    return list(dict.fromkeys(items))


def load_results(path: str) -> list[dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"读取输入 JSON 失败: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"解析输入 JSON 失败: {path}") from exc
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"]
    raise ValueError("输入 JSON 必须是结果数组，或包含 results 数组")


def first_nonempty(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def normalize_result_item(item: dict) -> dict:
    normalized = dict(item)
    snippet = first_nonempty(item, SNIPPET_KEYS)
    published_at = first_nonempty(item, PUBLISHED_AT_KEYS)
    source_domain = first_nonempty(item, SOURCE_DOMAIN_KEYS)
    url = str(item.get("url", "")).strip()

    if snippet and not normalized.get("snippet"):
        normalized["snippet"] = snippet
    if published_at and not normalized.get("publishedAt"):
        normalized["publishedAt"] = published_at
    if not normalized.get("sourceDomain"):
        normalized["sourceDomain"] = source_domain or normalize_host(url)

    return normalized


def filter_results(results: list[dict], sites: list[str], auto_normalize: bool = False) -> dict[str, object]:
    domains = list(dict.fromkeys(normalize_site(site) for site in sites))
    seen_urls: set[str] = set()
    seen_titles_by_domain: dict[str, set[str]] = {}
    kept: list[dict] = []
    dropped: list[dict] = []

    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            dropped.append({"index": index, "reason": "invalid_item", "item": item})
            continue

        current = normalize_result_item(item) if auto_normalize else dict(item)

        url = str(current.get("url", "")).strip()
        title = str(current.get("title", "")).strip()
        if not url:
            dropped.append({"index": index, "reason": "missing_url", "item": current})
            continue
        if not title:
            dropped.append({"index": index, "reason": "missing_title", "item": current})
            continue

        host = normalize_host(url)
        if not host:
            dropped.append({"index": index, "reason": "invalid_host", "item": current})
            continue

        matched_domain = next((domain for domain in domains if host_matches(host, domain)), None)
        if not matched_domain:
            dropped.append({"index": index, "reason": "domain_mismatch", "host": host, "item": current})
            continue

        normalized_url = normalize_url(url)
        normalized_title = normalize_title(title)

        if normalized_url in seen_urls:
            dropped.append({"index": index, "reason": "duplicate_url", "normalizedUrl": normalized_url, "item": current})
            continue

        seen_titles = seen_titles_by_domain.setdefault(matched_domain, set())
        if normalized_title and normalized_title in seen_titles:
            dropped.append(
                {
                    "index": index,
                    "reason": "duplicate_title",
                    "matchedDomain": matched_domain,
                    "normalizedTitle": normalized_title,
                    "item": current,
                }
            )
            continue

        seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)

        enriched = dict(current)
        enriched["matchedDomain"] = matched_domain
        enriched["normalizedUrl"] = normalized_url
        enriched["normalizedTitle"] = normalized_title
        kept.append(enriched)

    return {
        "sites": domains,
        "summary": {
            "input": len(results),
            "kept": len(kept),
            "dropped": len(dropped),
        },
        "results": kept,
        "dropped": dropped,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按目标域名过滤并去重 news-digest 候选结果")
    parser.add_argument("--input", required=True, help="输入 JSON 文件路径；支持数组或 {results:[...]} 结构")
    parser.add_argument("--site", action="append", default=[], help="目标站点，可重复传入，也支持逗号分隔")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--keep-dropped", action="store_true", help="输出中保留被丢弃条目")
    parser.add_argument("--normalize", action="store_true", help="将 description/summary/content 等别名字段归一化为标准结果字段")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sites = split_items(args.site)
    if not sites:
        print("缺少站点，请至少提供一个 --site。", file=sys.stderr)
        return 1

    try:
        results = load_results(args.input)
        payload = filter_results(results, sites, auto_normalize=args.normalize)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.keep_dropped:
        payload = dict(payload)
        payload.pop("dropped", None)

    if args.format == "text":
        print(f"输入: {payload['summary']['input']}")
        print(f"保留: {payload['summary']['kept']}")
        print(f"丢弃: {payload['summary']['dropped']}")
        for item in payload["results"]:
            print(f"- [{item['matchedDomain']}] {item['title']} -> {item['normalizedUrl']}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
