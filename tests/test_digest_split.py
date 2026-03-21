from __future__ import annotations

from app.digest import build_digest_messages


def test_digest_split_respects_message_limit():
    records = []
    for index in range(1, 8):
        records.append(
            {
                "url": f"https://example.com/{index}",
                "title": f"文章 {index}",
                "source": "测试源",
                "author": None,
                "published_at": None,
                "language": "zh",
                "summary": "摘要",
                "main_threads": [f"主线 {index} " + ("细节" * 80)],
                "credibility": {"score": 70, "level": "中等可信", "reasons": ["依据"], "risks": ["风险"], "disclaimer": "d"},
                "ai_likelihood": {"score": 30, "level": "轻度 AI 痕迹", "reasons": ["依据"], "limitations": ["限制"], "disclaimer": "d"},
                "status": "queued",
            }
        )
    messages = build_digest_messages(records, batch_date="2026-03-21", max_chars=500)
    assert len(messages) > 1
    assert all(len(message) <= 500 for message in messages)

