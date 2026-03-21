# Output Format

统一 JSON Schema：

```json
{
  "url": "string",
  "title": "string",
  "source": "string",
  "author": "string|null",
  "published_at": "ISO8601|null",
  "language": "string",
  "summary": "string",
  "main_threads": ["string"],
  "credibility": {
    "score": 0,
    "level": "string",
    "reasons": ["string"],
    "risks": ["string"],
    "disclaimer": "string"
  },
  "ai_likelihood": {
    "score": 0,
    "level": "string",
    "reasons": ["string"],
    "limitations": ["string"],
    "disclaimer": "string"
  },
  "status": "queued|sent|failed"
}
```

单篇回复必须带：

- 核心摘要
- 3-6 条主要脉络
- 可信度评分、依据、风险、免责声明
- AI 痕迹评分、依据、限制、免责声明

Digest 文案必须支持自动分段，每段不超过 Telegram 安全阈值。

