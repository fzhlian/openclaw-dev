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
- 若本轮任务语义是“执行一次/跑一遍”，确认块里也必须显式回显 `频率：一次性`
- 若输入时间范围为 `24h / 1d / 7d / 14d / 30d` 等简写，应先归一化为 `最近 24 小时 / 最近 1 天 / 最近 7 天 / 最近 14 天 / 最近 30 天` 再回显
- 若输入频率为“日报 / 周报 / 执行一次”等自然表达，应先归一化为 `每日 / 每周 / 一次性` 再回显
- 若输入输出模式为“总览+逐条”或“按主题分组 + 逐条”等自然表达，应先归一化为标准模式名再回显
- 若输入关键词或网站使用全角逗号 `，`，也应按普通逗号拆分，而不是把整串当成单个值
- 若输入网站为完整 URL 或带 `www.` 的地址，应先归一化为主域名再回显
- 若输入频率超出 `一次性 / 每日 / 每周`，应直接报错，而不是继续原样回显
- 若用户传入不支持的 `--output-mode`，应直接报错，而不是静默回退到默认模式
- 若用户传入非中文 `--language`，应直接报错，而不是继续假装支持其他输出语言
- 不应再要求补问
- 若用户给的是常见媒体名而非域名，如 `BBC` / `RFI` / `纽约时报` / `DW` / `华尔街见闻`，应在 intake 阶段先归一化为域名再回显
- 若用户给的是无法可靠归一化的裸媒体名，应直接报错或补问，不能把未归一化名称直接往下传

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
- 若关键词或站点使用全角逗号 `，`，仍能正确拆分成多项查询

### 非域名站点输入

```bash
python3 skills/news-digest/scripts/build_query.py \
  -k "OpenAI" \
  -s "BBC"
```

预期：

- 直接报错，提示站点需使用域名，如 `bbc.com`
- 不输出 `site:bbc ...` 这类无效查询

说明：

- 常见媒体名归一化应发生在 `intake_check.py` 这类上游采集阶段
- `build_query.py` 仍要求拿到的输入已经是域名

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
- 若 `--site` 使用全角逗号 `，` 分隔多个域名，仍能正确拆分并过滤

### 非域名站点输入

```bash
python3 skills/news-digest/scripts/filter_results.py \
  --input sample-results.json \
  --site "BBC"
```

预期：

- 直接报错，提示站点需使用域名，如 `bbc.com`
- 不应把 `BBC` 静默归一化成 `bbc`

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
- 可参考 `references/workflow-example.md` 对照“原始字段 -> 标准字段 -> 过滤后输出”的完整样例

## 验证 5：最终摘要渲染

准备一个最小样例文件 `sample-filtered-results.json`：

```json
{
  "results": [
    {
      "title": "OpenAI policy update",
      "url": "https://openai.com/index/policy-update",
      "snippet": "policy summary from search result",
      "matchedDomain": "openai.com"
    },
    {
      "title": "OpenAI roadmap note",
      "url": "https://openai.com/index/roadmap",
      "snippet": "roadmap summary",
      "publishedAt": "2026-03-14",
      "matchedDomain": "openai.com"
    }
  ]
}
```

执行：

```bash
python3 skills/news-digest/scripts/render_digest.py \
  --input sample-filtered-results.json \
  --keywords "OpenAI" \
  --sites "openai.com" \
  --time-range "最近 7 天" \
  --limit 2
```

预期：

- 输出包含 `## 摘要总览`、`## 文章清单`、`## 检索参数`、`## 局限与建议`
- 第一条因缺失 `publishedAt`，应显示“时间未标注”
- 两条结果都保留原始链接
- `## 检索参数` 中包含 `频率`
- `## 检索参数` 中包含 `输出语言`，默认显示 `中文`
- 若渲染输入里传入 `OpenAI,Gemini` 这类逗号分隔关键词，最终 `## 检索参数` 中应回显为 `OpenAI、Gemini`
- 若渲染输入里传入 `OpenAI，Gemini` 或 `openai.com，blog.google` 这类全角逗号分隔值，最终 `## 检索参数` 中也应按多项正确回显
- 若渲染输入里传入完整 URL 或带 `www.` 的站点，最终 `## 检索参数` 中应回显归一化后的主域名
- 若结果对象提供 `snippetZh` / `summaryZh`，应优先使用中文摘要字段
- 若结果对象未提供中文摘要字段，可退回原始 `snippet` / `summary`，不要求脚本在渲染阶段强制翻译
- 若传入不支持的 `--output-mode`，应直接报错，而不是继续输出平铺模板
- 若传入非中文 `--language`，应直接报错，而不是继续输出中文模板
- 若渲染输入里传入 `BBC` 之类非域名站点，应直接报错，而不是原样回显到最终参数区
- 输出结构与 `SKILL.md` 中的模板保持一致

### 按主题分组模式

准备一个最小样例文件 `sample-grouped-results.json`：

```json
{
  "results": [
    {
      "title": "OpenAI policy update",
      "url": "https://openai.com/index/policy-update",
      "snippet": "policy summary from search result",
      "matchedDomain": "openai.com",
      "topic": "OpenAI"
    },
    {
      "title": "Gemini roadmap note",
      "url": "https://blog.google/technology/ai/gemini-roadmap",
      "snippet": "roadmap summary",
      "matchedDomain": "blog.google",
      "topic": "Gemini"
    }
  ]
}
```

执行：

```bash
python3 skills/news-digest/scripts/render_digest.py \
  --input sample-grouped-results.json \
  --keywords "OpenAI,Gemini" \
  --sites "openai.com,blog.google" \
  --time-range "最近 7 天" \
  --limit 2 \
  --output-mode "按主题分组+逐条"
```

预期：

- `## 文章清单` 下按 `### OpenAI`、`### Gemini` 分组输出
- 每个分组内仍保留逐条摘要、来源、时间、链接
- `## 检索参数` 中显示本次 `输出模式`
- `## 检索参数` 中显示本次 `频率`
- `## 检索参数` 中仍显示 `输出语言：中文`
- 若渲染输入里传入 `24h / 7d / 30d` 等时间范围简写，最终 `## 检索参数` 中也应回显标准中文写法
- 若渲染输入里传入“执行一次 / 日报 / 周报”等自然表达，最终 `## 检索参数` 中也应回显归一化后的 `一次性 / 每日 / 每周`
- 若渲染输入里传入“总览+逐条”或“按主题分组 + 逐条”等自然表达，最终 `## 检索参数` 中也应回显标准模式名
- 若渲染输入里传入 `每月` 等不支持频率，应直接报错，而不是继续输出
- 若缺少 `topic` / `queryTopic` / `keyword` / `query` 字段，则应直接报错，而不是输出 `未分组主题`

## 验证 6：缺少稳定链接时必须降级

适用场景：

- 检索结果只能确认主题方向
- 搜索 provider 只返回摘要片段，拿不到稳定原文 URL
- 某站点结果存在主题命中，但没有可直接落地的原始链接

预期：

- 不输出正常 `## 文章清单`
- 不输出 `## 摘要总览`
- 不在逐条条目中写 `链接：暂无`、`链接：未稳定返回`、`只确认主题方向`
- 改为只输出：
  - `## 检索参数`
  - `## 已发现结果`
  - `## 局限与建议`
- 明确说明哪些站点/主题仅确认了方向，哪些结果因为缺少稳定链接被排除
- 降级输出的 `## 检索参数` 中仍应保留 `频率`
- 降级输出的 `## 检索参数` 中仍应保留 `输出语言`
- 如使用 `render_digest.py` 做降级渲染，可传入空 `results` 加 `discoveredResults` / `findings` 字段生成这类输出

## 验证 7：端到端最小闭环

可参考 `references/end-to-end-example.md`，顺序执行：

1. `intake_check.py` 生成参数确认
2. `build_query.py` 生成查询
3. `filter_results.py --normalize` 过滤模拟候选结果
4. `render_digest.py` 渲染最终 Markdown

预期：

- 4 个脚本可以按文档顺序串起来
- 过滤阶段能去掉非目标域名结果
- 渲染阶段能保留链接，并对缺失时间显示“时间未标注”
- 输出结构仍符合 `SKILL.md` 模板

## 回归检查

修改 `SKILL.md` 后，再检查以下约束仍成立：

1. 未确认参数前，不直接进入检索
2. `--expand` / `--auto-english` 只在必要时显式开启
3. 查询生成后，先将候选结果归一化，再做域名过滤与去重，再进入摘要
4. 摘要阶段只基于过滤后的结果，不直接混用原始搜索结果
5. 缺失 `publishedAt` 时，最终输出明确标注“时间未标注”
6. 结果不足时，先放宽时间范围，再扩词，再英文化，最后才放宽站点
7. 正常输出时，逐条结果仍要求附原始链接，并明确局限
8. 降级输出时，不再强行保留逐条条目，而是改为“检索参数 + 已发现结果 + 局限与建议”
