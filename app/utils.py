from __future__ import annotations

import hashlib
import json
import os
import re
from html import unescape as stdlib_unescape
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo


URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
BLANK_LINES_RE = re.compile(r"\n{3,}")


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def local_today(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).date().isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def normalize_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise ValueError("URL 不能为空")
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"无法识别 URL: {url}")
    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith("utm_") or key_lower in {"fbclid", "gclid", "igshid"}:
            continue
        query_items.append((key, value))
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path or "/",
        params="",
        query=urlencode(sorted(query_items)),
        fragment="",
    )
    return urlunparse(normalized)


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def extract_urls(text: str) -> list[str]:
    return URL_PATTERN.findall(text or "")


def domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def slugify(value: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    if not cleaned:
        cleaned = "article"
    return cleaned[:max_length].strip("-") or "article"


def strip_html(value: str) -> str:
    text = COMMENT_RE.sub("", value)
    text = SCRIPT_STYLE_RE.sub(" ", text)
    text = re.sub(r"</(p|div|br|li|article|section|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = TAG_RE.sub(" ", text)
    text = html_unescape(text)
    text = WHITESPACE_RE.sub(" ", text)
    text = re.sub(r"\n +", "\n", text)
    text = BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def html_unescape(value: str) -> str:
    return stdlib_unescape(value).replace("\xa0", " ")


def clean_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def word_count(text: str) -> int:
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_tokens = len(re.findall(r"[A-Za-z0-9_]+", text))
    if cjk_chars:
        return cjk_chars + latin_tokens
    return latin_tokens


def sentence_split(text: str) -> list[str]:
    normalized = clean_text(text)
    if not normalized:
        return []
    normalized = normalized.replace("\n", " ")
    parts = SENTENCE_SPLIT_PATTERN.split(normalized)
    sentences = [part.strip() for part in parts if part and part.strip()]
    if not sentences:
        return []

    merged: list[str] = []
    for sentence in sentences:
        if merged and sentence.startswith(("”", "’", '"', "」", "』", "》", "】")):
            merged[-1] = f"{merged[-1]}{sentence}"
            continue
        merged.append(sentence)
    return merged


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load_json_if_present(value: str | None) -> object:
    if not value:
        return None
    return json.loads(value)


def first_non_empty(values: Iterable[str | None], fallback: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return fallback


def resolve_path(root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (root / candidate).resolve()


def coalesce_env(environ: dict[str, str], file_values: dict[str, str]) -> dict[str, str]:
    merged = dict(file_values)
    merged.update({key: value for key, value in environ.items() if value is not None})
    return merged


def load_env(root: Path, env_path: Path | None = None) -> dict[str, str]:
    target = env_path or root / ".env"
    return coalesce_env(os.environ, parse_env_file(target))
