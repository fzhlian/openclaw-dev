from __future__ import annotations

from app.analysis import assess_ai_likelihood
from app.models import ExtractedArticle


def test_ai_result_always_has_disclaimer():
    article = ExtractedArticle(
        url="https://example.com/ai",
        title="AI 检测样本",
        source="Example",
        author=None,
        published_at=None,
        language="zh",
        text="值得注意的是，这段文本用于检查免责声明。总的来说，可以看出它有一些模板化表达。" * 5,
        word_count=200,
        fetched_at="2026-03-21T00:00:00Z",
    )
    result = assess_ai_likelihood(article).to_dict()
    assert result["disclaimer"]
    assert "启发式" in result["disclaimer"]

