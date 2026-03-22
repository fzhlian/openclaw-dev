from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models import ExtractedArticle
from app.utils import clean_text, sentence_split


TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
TRANSLATE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TRANSLATE_MAX_CHARS = 1400
HTTP_ERROR_RE = re.compile(r"HTTP Error (\d{3})(?::\s*([^\n]+))?", re.IGNORECASE)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-zÀ-ÿ]")
URLISH_RE = re.compile(r"(?:https?://|www\.|[A-Za-z0-9-]+\.[A-Za-z]{2,})", re.IGNORECASE)


def is_mostly_chinese(text: str) -> bool:
    normalized = clean_text(text)
    if not normalized:
        return True
    cjk_count = len(CJK_RE.findall(normalized))
    latin_count = len(LATIN_RE.findall(normalized))
    if cjk_count == 0:
        return False
    if latin_count == 0:
        return True
    return cjk_count >= latin_count


def should_translate_to_chinese(text: str, *, language: str = "unknown", allow_urlish: bool = False) -> bool:
    normalized = clean_text(text)
    if not normalized:
        return False
    if str(language or "").lower().startswith("zh") and is_mostly_chinese(normalized):
        return False
    if not allow_urlish and URLISH_RE.search(normalized):
        return False
    if is_mostly_chinese(normalized):
        return False
    return bool(LATIN_RE.search(normalized))


def _translate_chunk(text: str, *, timeout: int = 15) -> str:
    query = urlencode(
        {
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": text,
        }
    )
    request = Request(f"{TRANSLATE_ENDPOINT}?{query}", headers=TRANSLATE_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    translated = "".join(str(item[0]) for item in payload[0] if item and item[0])
    return clean_text(translated)


def _split_translation_chunks(text: str) -> list[str]:
    normalized = clean_text(text)
    if len(normalized) <= TRANSLATE_MAX_CHARS:
        return [normalized]
    sentences = sentence_split(normalized) or [normalized]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= TRANSLATE_MAX_CHARS:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(sentence) <= TRANSLATE_MAX_CHARS:
            current = sentence
            continue
        start = 0
        while start < len(sentence):
            end = min(start + TRANSLATE_MAX_CHARS, len(sentence))
            chunks.append(sentence[start:end])
            start = end
        current = ""
    if current:
        chunks.append(current)
    return chunks


def translate_text_to_chinese(text: str, *, timeout: int = 15) -> str:
    normalized = clean_text(text)
    if not normalized:
        return ""
    translated_parts = [_translate_chunk(chunk, timeout=timeout) for chunk in _split_translation_chunks(normalized)]
    return clean_text(" ".join(part for part in translated_parts if part))


def _fallback_threads_from_text(text: str, *, max_items: int = 3) -> list[str]:
    paragraphs = [clean_text(chunk) for chunk in re.split(r"\n{2,}", clean_text(text)) if clean_text(chunk)]
    candidates = [chunk for chunk in paragraphs if len(chunk) >= 40]
    if not candidates:
        candidates = [chunk for chunk in sentence_split(text) if len(chunk) >= 30]
    return candidates[:max_items]


def localize_article_for_display(
    article: ExtractedArticle,
    *,
    summary: str,
    main_threads: list[str],
    translator: Callable[[str], str] | None = None,
) -> tuple[ExtractedArticle, str, list[str]]:
    translator = translator or translate_text_to_chinese

    def localize(text: str, *, language: str = "unknown", allow_urlish: bool = False) -> str:
        normalized = clean_text(text)
        if not should_translate_to_chinese(normalized, language=language, allow_urlish=allow_urlish):
            return normalized
        try:
            translated = translator(normalized)
        except Exception:
            return normalized
        return clean_text(translated) or normalized

    localized_title = localize(article.title, language=article.language)
    localized_source = localize(article.source, language=article.language)
    localized_author = localize(article.author or "", language=article.language, allow_urlish=True) if article.author else None
    localized_summary = localize(summary, language=article.language)
    source_threads = main_threads or _fallback_threads_from_text(article.text)
    localized_threads = [localize(item, language=article.language) for item in source_threads]
    changed = (
        localized_title != article.title
        or localized_source != article.source
        or localized_author != article.author
        or localized_summary != summary
        or localized_threads != main_threads
    )
    localized_article = replace(
        article,
        title=localized_title or article.title,
        source=localized_source or article.source,
        author=localized_author or article.author,
        language="zh" if changed else article.language,
    )
    return localized_article, localized_summary or summary, localized_threads or main_threads


def normalize_error_message_to_chinese(message: str) -> str:
    normalized = clean_text(message)
    if not normalized:
        return "未知错误"
    segments = [clean_text(part) for part in re.split(r"[；;]+\s*", normalized) if clean_text(part)]
    if not segments:
        return "未知错误"
    normalized_segments: list[str] = []
    for segment in segments:
        translated = _normalize_error_segment(segment)
        if translated and translated not in normalized_segments:
            normalized_segments.append(translated)
    return "；".join(normalized_segments) or "未知错误"


def _normalize_error_segment(message: str) -> str:
    normalized = clean_text(message)
    if not normalized:
        return ""
    http_match = HTTP_ERROR_RE.search(normalized)
    if http_match:
        status = int(http_match.group(1))
        if status == 403:
            return "HTTP 403：目标站点拒绝访问"
        if status == 404:
            return "HTTP 404：页面不存在"
        if status == 451:
            return "HTTP 451：目标站点因法律限制不可访问"
        if status == 429:
            return "HTTP 429：请求过于频繁"
        if 500 <= status < 600:
            return f"HTTP {status}：目标站点暂时不可用"
        return f"HTTP {status}：请求失败"
    if is_mostly_chinese(normalized):
        return normalized
    lowered = normalized.lower()
    mappings = [
        ("redirect error that would lead to an infinite loop", "页面重定向异常，跳转进入死循环"),
        ("network timeout", "网络请求超时"),
        ("read operation timed out", "网络请求超时"),
        ("timed out", "网络请求超时"),
        ("access denied", "目标站点拒绝访问"),
        ("forbidden", "目标站点拒绝访问"),
        ("connection reset", "网络连接被重置"),
        ("connection refused", "目标站点拒绝连接"),
    ]
    for needle, replacement in mappings:
        if needle in lowered:
            return replacement
    return normalized
