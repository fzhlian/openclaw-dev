from __future__ import annotations


class SchemaValidationError(ValueError):
    pass


def validate_article_payload(payload: dict[str, object]) -> None:
    required_top_level = {
        "url",
        "title",
        "source",
        "author",
        "published_at",
        "language",
        "is_favorite",
        "favorited_at",
        "summary",
        "main_threads",
        "credibility",
        "ai_likelihood",
        "status",
    }
    missing = required_top_level - set(payload)
    if missing:
        raise SchemaValidationError(f"缺少顶层字段: {sorted(missing)}")
    credibility = payload["credibility"]
    ai_likelihood = payload["ai_likelihood"]
    if not isinstance(credibility, dict):
        raise SchemaValidationError("credibility 必须是对象")
    if not isinstance(ai_likelihood, dict):
        raise SchemaValidationError("ai_likelihood 必须是对象")
    for section_name, section, keys in (
        ("credibility", credibility, {"score", "level", "reasons", "risks", "disclaimer"}),
        ("ai_likelihood", ai_likelihood, {"score", "level", "reasons", "limitations", "disclaimer"}),
    ):
        missing_keys = keys - set(section)
        if missing_keys:
            raise SchemaValidationError(f"{section_name} 缺少字段: {sorted(missing_keys)}")
        disclaimer = section.get("disclaimer")
        if not isinstance(disclaimer, str) or "启发式" not in disclaimer:
            raise SchemaValidationError(f"{section_name} 必须包含启发式免责声明")
    main_threads = payload["main_threads"]
    if not isinstance(main_threads, list) or not all(isinstance(item, str) for item in main_threads):
        raise SchemaValidationError("main_threads 必须是字符串数组")
    if not isinstance(payload["is_favorite"], bool):
        raise SchemaValidationError("is_favorite 必须是布尔值")
    favorited_at = payload["favorited_at"]
    if favorited_at is not None and not isinstance(favorited_at, str):
        raise SchemaValidationError("favorited_at 必须是字符串或 null")
