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
  "is_favorite": false,
  "favorited_at": "ISO8601|null",
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
- 3-6 条主要内容
- 可信度评分、依据、风险、免责声明
- AI 痕迹评分、依据、限制、免责声明

约束：

- 核心摘要必须是基于全文的 1-2 句总结，不能直接复用首段。
- `main_threads` 虽然沿用这个字段名，但内容应是更具体的“主要内容”，而不是“主线一/主线二”式空泛标签。
- 如果文章已收藏，输出中应能反映收藏状态。

Digest 文案必须支持自动分段，每段不超过 Telegram 安全阈值。
