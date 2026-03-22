from __future__ import annotations

from app.digest import format_single_article


def test_single_article_template_uses_主要内容标题():
    rendered = format_single_article(
        {
            "title": "模板测试",
            "source": "测试源",
            "author": None,
            "published_at": None,
            "is_favorite": False,
            "url": "https://example.com/render",
            "summary": "这是一段摘要。",
            "main_threads": ["第一点内容。", "第二点内容。"],
            "credibility": {
                "score": 70,
                "level": "中等可信",
                "reasons": ["依据一"],
                "risks": ["风险一"],
            },
            "ai_likelihood": {
                "score": 30,
                "level": "轻度 AI 痕迹",
                "reasons": ["依据一"],
                "limitations": ["限制一"],
            },
        }
    )

    assert "二、主要内容" in rendered
    assert "内容脉络" not in rendered
    assert "说明：可信度与 AI 痕迹均为启发式分析" not in rendered
    assert "原文链接：\nhttps://example.com/render" in rendered
    assert rendered.rstrip().endswith("https://example.com/render")
