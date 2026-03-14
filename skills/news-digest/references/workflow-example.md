# workflow-example

用于展示 `news-digest` 在最小闭环下如何把“检索源原始字段”收敛为“标准字段”，再进入过滤与最终输出。

## 场景

- 主题：OpenAI
- 站点：`openai.com`
- 时间范围：最近 7 天
- 目标：展示同一批候选结果如何从原始搜索字段进入标准结果对象，并经过 `filter_results.py --normalize` 过滤

## Step 1：检索源原始字段

假设外部检索源返回如下结果：

```json
[
  {
    "title": "OpenAI policy update",
    "url": "https://openai.com/index/policy-update",
    "description": "policy summary from search result"
  },
  {
    "title": "OpenAI roadmap note",
    "url": "https://openai.com/index/roadmap",
    "summary": "roadmap summary",
    "published_at": "2026-03-14",
    "domain": "openai.com"
  },
  {
    "title": "Offsite mirror",
    "url": "https://example.com/mirror-story",
    "content": "should drop"
  }
]
```

特点：

- 摘要字段并不统一，分别使用了 `description`、`summary`、`content`
- 时间字段使用了 `published_at`
- 来源字段使用了 `domain`
- 第三条不在目标域名内，后续应被丢弃

## Step 2：归一化后的标准字段

按 `references/result-schema.md` 的约定，归一化后应收敛为：

```json
[
  {
    "title": "OpenAI policy update",
    "url": "https://openai.com/index/policy-update",
    "snippet": "policy summary from search result",
    "snippetZh": "OpenAI 发布了新的政策更新摘要",
    "sourceDomain": "openai.com"
  },
  {
    "title": "OpenAI roadmap note",
    "url": "https://openai.com/index/roadmap",
    "snippet": "roadmap summary",
    "snippetZh": "OpenAI 路线图更新聚焦后续产品方向",
    "publishedAt": "2026-03-14",
    "sourceDomain": "openai.com"
  },
  {
    "title": "Offsite mirror",
    "url": "https://example.com/mirror-story",
    "snippet": "should drop",
    "sourceDomain": "example.com"
  }
]
```

归一化规则：

- `description` / `summary` / `content` -> `snippet`
- 若已整理中文摘要，则补充 `snippetZh`
- `published_at` -> `publishedAt`
- `domain` -> `sourceDomain`
- 若没有 `sourceDomain`，则从 `url` 自动提取主域名

## Step 3：过滤后输出

执行：

```bash
python3 skills/news-digest/scripts/filter_results.py \
  --input sample-results.json \
  --site "openai.com" \
  --normalize \
  --keep-dropped
```

预期输出要点：

```json
{
  "summary": {
    "input": 3,
    "kept": 2,
    "dropped": 1
  },
  "results": [
    {
      "title": "OpenAI policy update",
      "url": "https://openai.com/index/policy-update",
      "snippet": "policy summary from search result",
      "sourceDomain": "openai.com",
      "matchedDomain": "openai.com",
      "normalizedUrl": "https://openai.com/index/policy-update"
    },
    {
      "title": "OpenAI roadmap note",
      "url": "https://openai.com/index/roadmap",
      "snippet": "roadmap summary",
      "publishedAt": "2026-03-14",
      "sourceDomain": "openai.com",
      "matchedDomain": "openai.com",
      "normalizedUrl": "https://openai.com/index/roadmap"
    }
  ]
}
```

解释：

- 第 1 条保留，但没有 `publishedAt`；摘要阶段应输出“时间未标注”
- 第 2 条保留，并保留标准字段 `publishedAt`
- 第 3 条因域名不匹配被丢弃，不进入摘要

## Step 4：进入最终摘要时的映射

过滤后的结果进入最终输出时，建议按以下方式映射：

- 标题：`title`
- 摘要：基于 `snippet`
- 来源：`matchedDomain`
- 时间：`publishedAt`，缺失则写“时间未标注”
- 链接：`url`

示例：

```markdown
1. **OpenAI policy update**
   - 摘要：OpenAI 发布了新的政策更新摘要
   - 来源：openai.com ｜ 时间：时间未标注
   - 链接：https://openai.com/index/policy-update

2. **OpenAI roadmap note**
   - 摘要：OpenAI 路线图更新聚焦后续产品方向
   - 来源：openai.com ｜ 时间：2026-03-14
   - 链接：https://openai.com/index/roadmap
```

## 最小闭环检查点

这个示例展示的最小闭环是：

1. 原始检索字段允许不统一
2. 进入过滤前先归一化到标准字段
3. 过滤后只保留目标域名结果
4. 摘要阶段只消费过滤后的标准结果对象
5. 缺失时间时明确写“时间未标注”，不编造
6. 若过滤后结果拿不到稳定原始 URL，则不要继续渲染正常 `文章清单`，而应改走降级输出
