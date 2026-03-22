from __future__ import annotations

from app.digest import format_single_article


def test_single_article_format_shows_only_scores_for_credibility_and_ai():
    message = format_single_article(
        {
            "title": "测试文章",
            "source": "测试来源",
            "author": "作者",
            "published_at": "2026-03-21T12:00:00+08:00",
            "is_favorite": False,
            "summary": "这是一段摘要。",
            "main_threads": ["主线一", "主线二"],
            "credibility": {"score": 72, "level": "中等可信", "reasons": ["a"], "risks": ["b"]},
            "ai_likelihood": {"score": 18, "level": "低 AI 痕迹", "reasons": ["c"], "limitations": ["d"]},
            "url": "https://example.com/a",
        }
    )

    assert "评分：72/100（中等可信）" in message
    assert "评分：18/100（低 AI 痕迹）" in message
    assert "依据：" not in message
    assert "风险：" not in message
    assert "限制：" not in message
