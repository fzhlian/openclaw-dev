# result-schema

用于约定 `news-digest` 在“外部检索结果 -> 过滤结果 -> 最终摘要”之间的最小数据接口，避免不同检索来源输出结构不一致。

## 最小结果对象

进入过滤阶段前，先尽量整理为以下字段：

```json
{
  "title": "文章标题",
  "url": "https://example.com/post",
  "snippet": "搜索摘要或抓取后的核心片段",
  "publishedAt": "2026-03-14",
  "sourceDomain": "example.com"
}
```

其中：

- `title`：必填；用于最终输出与标题去重
- `url`：必填；用于域名校验、链接输出与 URL 去重
- `snippet`：建议提供；作为摘要阶段的基础材料
- `publishedAt`：可缺失；缺失时不要编造，最终输出标注“时间未标注”
- `sourceDomain`：建议提供；缺失时可由 URL 提取主域名

## 归一化要求

在调用 `scripts/filter_results.py` 前，先做以下整理：

1. 丢弃明显缺少 `title` 或 `url` 的条目，或接受其被过滤脚本丢弃
2. 将不同搜索源中的摘要字段（如 `description`、`summary`、`content`）统一映射到 `snippet`
3. 将不同时间字段（如 `published_at`、`date`、`time`）统一映射到 `publishedAt`
4. 将来源字段（如 `domain`、`site`、`source`）统一映射到 `sourceDomain`
5. 若没有 `sourceDomain`，从 `url` 解析主域名

## 过滤后结果

`filter_results.py` 当前会补充以下字段：

- `matchedDomain`
- `normalizedUrl`
- `normalizedTitle`

摘要阶段应优先使用过滤后的结果对象，不要回退到原始搜索结果混合总结。

## 进入摘要前的最低要求

进入摘要前，结果列表至少应满足：

- 每条都有 `title`
- 每条都有可点击的 `url`
- 每条都已通过目标域名过滤
- 重复 URL / 重复标题已完成基础去重
- 缺失时间的条目已显式准备输出为“时间未标注”

## 输出映射建议

最终逐条输出时，优先按以下映射：

- 标题：`title`
- 摘要：基于 `snippet` 与页面正文提炼，不编造超出来源的信息
- 来源：优先 `matchedDomain`，否则 `sourceDomain`
- 时间：`publishedAt`，缺失则写“时间未标注”
- 链接：`url`
