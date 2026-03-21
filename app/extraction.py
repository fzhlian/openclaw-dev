from __future__ import annotations

import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.models import ExtractedArticle
from app.utils import (
    clean_text,
    domain_from_url,
    first_non_empty,
    normalize_url,
    slugify,
    strip_html,
    truncate,
    url_hash,
    utc_now_iso,
    word_count,
)


META_PATTERN_TEMPLATE = r'<meta[^>]+(?:name|property)=["\']{name}["\'][^>]+content=["\']([^"\']+)["\']'
TITLE_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="og:title"),
    META_PATTERN_TEMPLATE.format(name="twitter:title"),
    r"<title[^>]*>(.*?)</title>",
    r"<h1[^>]*>(.*?)</h1>",
]
AUTHOR_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="author"),
    META_PATTERN_TEMPLATE.format(name="article:author"),
    r'class=["\'][^"\']*author[^"\']*["\'][^>]*>(.*?)</',
]
PUBLISHED_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="article:published_time"),
    META_PATTERN_TEMPLATE.format(name="pubdate"),
    META_PATTERN_TEMPLATE.format(name="publishdate"),
    META_PATTERN_TEMPLATE.format(name="date"),
    r"<time[^>]+datetime=[\"']([^\"']+)[\"']",
]
SOURCE_PATTERNS = [
    META_PATTERN_TEMPLATE.format(name="og:site_name"),
    META_PATTERN_TEMPLATE.format(name="application-name"),
]
LANG_PATTERN = r"<html[^>]+lang=[\"']([^\"']+)[\"']"


class ExtractionError(RuntimeError):
    pass


def fetch_html(url: str, timeout: int = 20) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _search_first(patterns: list[str], html: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(strip_html(match.group(1)))
    return None


def _extract_main_text(html: str) -> str:
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
    cleaned_paragraphs = [clean_text(strip_html(chunk)) for chunk in paragraphs]
    cleaned_paragraphs = [chunk for chunk in cleaned_paragraphs if len(chunk) >= 40]
    if cleaned_paragraphs:
        return "\n\n".join(cleaned_paragraphs)
    article_match = re.search(r"<article[^>]*>(.*?)</article>", html, flags=re.IGNORECASE | re.DOTALL)
    if article_match:
        return clean_text(strip_html(article_match.group(1)))
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.IGNORECASE | re.DOTALL)
    if body_match:
        return clean_text(strip_html(body_match.group(1)))
    return clean_text(strip_html(html))


def extract_article(
    url: str,
    *,
    raw_html_dir: Path | None = None,
    extracted_text_dir: Path | None = None,
    fetcher: Callable[[str], str] | None = None,
) -> ExtractedArticle:
    normalized = normalize_url(url)
    try:
        html = (fetcher or fetch_html)(normalized)
    except Exception as exc:
        raise ExtractionError(str(exc)) from exc
    if not html or not html.strip():
        raise ExtractionError("页面返回空内容")
    text = _extract_main_text(html)
    if not text:
        raise ExtractionError("无法从页面中提取正文")
    fetched_at = utc_now_iso()
    article_hash = url_hash(normalized)
    title = first_non_empty((_search_first(TITLE_PATTERNS, html),), "未命名文章")
    source = first_non_empty((_search_first(SOURCE_PATTERNS, html), domain_from_url(normalized)), "未知来源")
    author = _search_first(AUTHOR_PATTERNS, html)
    published_at = _search_first(PUBLISHED_PATTERNS, html)
    language_match = re.search(LANG_PATTERN, html, flags=re.IGNORECASE)
    language = (language_match.group(1) if language_match else "unknown").split("-", 1)[0].lower()
    raw_html_path = None
    extracted_text_path = None
    if raw_html_dir is not None:
        file_name = f"{slugify(title)}-{article_hash[:12]}.html"
        target = raw_html_dir / file_name
        target.write_text(html, encoding="utf-8")
        raw_html_path = str(target)
    if extracted_text_dir is not None:
        file_name = f"{slugify(title)}-{article_hash[:12]}.txt"
        target = extracted_text_dir / file_name
        target.write_text(text, encoding="utf-8")
        extracted_text_path = str(target)
    extracted = ExtractedArticle(
        url=normalized,
        title=truncate(title, 180),
        source=source,
        author=truncate(author, 120) if author else None,
        published_at=published_at,
        language=language or "unknown",
        text=text,
        word_count=word_count(text),
        fetched_at=fetched_at,
        raw_html_path=raw_html_path,
        extracted_text_path=extracted_text_path,
    )
    if extracted.word_count < 20:
        raise ExtractionError("提取到的正文过短，疑似抓取失败")
    return extracted
