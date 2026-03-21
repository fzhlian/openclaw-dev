from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CREDIBILITY_DISCLAIMER = "该结果为基于来源、证据与交叉印证的启发式评估，不构成最终事实裁定。"
AI_DISCLAIMER = "该结果仅为启发式分析，不能单独证明或否定文本由 AI 生成。"


@dataclass(slots=True)
class CredibilityResult:
    score: int
    level: str
    reasons: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    disclaimer: str = CREDIBILITY_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "reasons": self.reasons,
            "risks": self.risks,
            "disclaimer": self.disclaimer,
        }


@dataclass(slots=True)
class AILikelihoodResult:
    score: int
    level: str
    reasons: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    disclaimer: str = AI_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "reasons": self.reasons,
            "limitations": self.limitations,
            "disclaimer": self.disclaimer,
        }


@dataclass(slots=True)
class ExtractedArticle:
    url: str
    title: str
    source: str
    author: str | None
    published_at: str | None
    language: str
    text: str
    word_count: int
    fetched_at: str
    raw_html_path: str | None = None
    extracted_text_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "author": self.author,
            "published_at": self.published_at,
            "language": self.language,
            "text": self.text,
            "word_count": self.word_count,
            "fetched_at": self.fetched_at,
            "raw_html_path": self.raw_html_path,
            "extracted_text_path": self.extracted_text_path,
        }


def build_article_payload(
    *,
    article: ExtractedArticle | dict[str, Any],
    summary: str,
    main_threads: list[str],
    credibility: CredibilityResult | dict[str, Any],
    ai_likelihood: AILikelihoodResult | dict[str, Any],
    status: str,
) -> dict[str, Any]:
    article_data = article.to_dict() if isinstance(article, ExtractedArticle) else dict(article)
    credibility_data = credibility.to_dict() if isinstance(credibility, CredibilityResult) else dict(credibility)
    ai_data = ai_likelihood.to_dict() if isinstance(ai_likelihood, AILikelihoodResult) else dict(ai_likelihood)
    return {
        "url": article_data["url"],
        "title": article_data.get("title") or "未命名文章",
        "source": article_data.get("source") or "未知来源",
        "author": article_data.get("author"),
        "published_at": article_data.get("published_at"),
        "language": article_data.get("language") or "unknown",
        "summary": summary,
        "main_threads": list(main_threads),
        "credibility": credibility_data,
        "ai_likelihood": ai_data,
        "status": status,
    }

