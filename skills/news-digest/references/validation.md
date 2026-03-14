# validation

用于手动验证 `news-digest` 当前最小闭环是否可用。优先验证脚本输出与 `SKILL.md` 中的执行约束是否一致。

## 目标

确认以下 3 个环节都能正常工作：

1. 需求不完整时，先生成缺项追问与参数确认块
2. 参数确认后，能按站点生成可执行的查询列表
3. 检索候选结果进入摘要前，能按目标域名过滤并完成基础去重

## 验证 1：需求采集脚本

### 缺项输入

```bash
python3 skills/news-digest/scripts/intake_check.py \
  --topic "OpenAI,Gemini" \
  --time-range "最近 7 天"
```

预期：

- 输出“缺项追问清单”
- 明确追问网站、频率、输出模式
- 参数确认块中未提供的字段显示为“（待确认）”

### 完整输入

```bash
python3 skills/news-digest/scripts/intake_check.py \
  --topic "OpenAI,Gemini" \
  --site "openai.com,blog.google" \
  --time-range "最近 24 小时" \
  --frequency "每日" \
  --limit 6 \
  --output-mode "按主题分组+逐条" \
  --format json
```

预期：

- `missingQuestions` 为空
- `confirm` 中包含关键词、网站、时间范围、频率、结果数、输出模式、输出语言
- 不应再要求补问

## 验证 2：查询生成脚本

### 原始关键词模式

```bash
python3 skills/news-digest/scripts/build_query.py \
  -k "贪官,伊朗,战争,ai" \
  -s "bbc.com,nytimes.com,dw.com,rfi.fr"
```

预期：

- 输出若干 `site:<domain> <keyword>` 查询
- 不自动扩词
- 不自动英文化

### 显式扩词 + 英文化

```bash
python3 skills/news-digest/scripts/build_query.py \
  -k "贪官,伊朗,战争,ai" \
  -s "bbc.com,nytimes.com,dw.com,rfi.fr" \
  --expand \
  --auto-english \
  --format json
```

预期：

- `autoExpand` 为 `true`
- `autoEnglish` 为 `true`
- `keywordPlan` 按站点列出实际使用的关键词
- 英文站点可看到 `corruption`、`Iran`、`war`、`AI` 等英文化词项

## 验证 3：结果过滤脚本

先准备一个最小样例文件 `sample-results.json`：

```json
[
  {
    "title": "Iran conflict update",
    "url": "https://www.bbc.com/news/world-1",
    "snippet": "..."
  },
  {
    "title": "Iran conflict update",
    "url": "https://bbc.com/news/world-1?utm_source=test",
    "snippet": "duplicate url"
  },
  {
    "title": "AI policy brief",
    "url": "https://subdomain.nytimes.com/2026/ai-policy",
    "snippet": "..."
  },
  {
    "title": "Offsite mirror",
    "url": "https://example.com/mirror-story",
    "snippet": "should drop"
  }
]
```

执行：

```bash
python3 skills/news-digest/scripts/filter_results.py \
  --input sample-results.json \
  --site "bbc.com,nytimes.com" \
  --keep-dropped
```

预期：

- `summary.input` 为 `4`
- `summary.kept` 为 `2`
- `summary.dropped` 为 `2`
- `bbc.com` 主域与子域结果都能保留
- 重复 URL 会被丢弃
- 不在目标域名内的结果会被丢弃

## 验证 4：结果归一化与摘要收口

准备一个最小样例文件 `sample-normalized-results.json`：

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
    "published_at": "2026-03-14"
  }
]
```

执行前先按 `references/result-schema.md` 做字段归一化，至少映射为：

- `description` / `summary` -> `snippet`
- `published_at` -> `publishedAt`
- `sourceDomain` 缺失时由 URL 提取

归一化后的结果再进入过滤与摘要阶段，预期：

- 可直接使用 `python3 skills/news-digest/scripts/filter_results.py --input sample-normalized-results.json --site "openai.com" --normalize`
- 两条结果都能保留链接
- 第一条时间缺失，最终输出时标注“时间未标注”
- 摘要应只基于归一化并过滤后的结果，不直接混用原始搜索字段

## 回归检查

修改 `SKILL.md` 后，再检查以下约束仍成立：

1. 未确认参数前，不直接进入检索
2. `--expand` / `--auto-english` 只在必要时显式开启
3. 查询生成后，先将候选结果归一化，再做域名过滤与去重，再进入摘要
4. 摘要阶段只基于过滤后的结果，不直接混用原始搜索结果
5. 缺失 `publishedAt` 时，最终输出明确标注“时间未标注”
6. 结果不足时，先放宽时间范围，再扩词，再英文化，最后才放宽站点
7. 最终输出仍要求逐条附链接，并明确局限
