# examples

以下示例用于说明 `news-digest` 的典型输入方式与输出目标。

## 用例 0：先收集需求再执行

- 场景：用户只说“帮我做个新闻跟踪”，信息不完整
- 期望行为：
  1. 先补问主题、来源、时间、频率、输出结构
  2. 给出参数确认清单，用户确认后再检索
- 示例追问：
  - `你最想追踪哪几个主题？可先给 3-8 个关键词。`
  - `你希望限定哪些站点/媒体？`
  - `要看最近 24 小时、7 天，还是 30 天？`
  - `这是一次性检索，还是要做日报/周报模板？`

## 用例 1：日报

- 场景：每天汇总 AI 行业重点动态
- 输入：
  - 关键词：`OpenAI`、`Anthropic`、`Gemini`
  - 网站：`openai.com`、`anthropic.com`、`blog.google`
  - 时间范围：最近 1 天
  - 频率：`每日`
  - 返回条数：6
- 预期输出：
  - 先给 3-5 条日报摘要
  - 再列出逐条新闻，附来源、时间、链接

## 用例 2：竞品监控

- 场景：跟踪 Notion AI 与 Microsoft Copilot 的产品更新
- 输入：
  - 关键词：`Notion AI`、`Microsoft Copilot`、`pricing`、`feature update`
  - 网站：`notion.so`、`microsoft.com`
  - 时间范围：最近 30 天
  - 频率：`一次性`
  - 返回条数：8
- 预期输出：
  - 汇总价格、功能、发布节奏变化
  - 标出可疑的营销页或重复公告

## 用例 3：技术追踪

- 场景：追踪 Python 异步生态的新变化
- 输入：
  - 关键词：`Python asyncio`、`AnyIO`、`Trio`
  - 网站：`docs.python.org`、`github.com`、`hynek.me`
  - 时间范围：最近 14 天
  - 频率：`每周`
  - 返回条数：10
- 预期输出：
  - 先总结技术趋势
  - 再列出版本更新、文档变更、实践文章

## 用例 4：国际时政跟踪

- 场景：按固定站点和关键词每日追踪国际新闻
- 输入：
  - 关键词：`贪官`、`伊朗`、`任命`、`战争`、`ai`
  - 网站：`bbc.com`、`rfi.fr`、`nytimes.com`、`dw.com`
  - 时间范围：最近 1 天
  - 频率：`每日`
  - 返回条数：12
- 预期输出：
  - 先给当日核心动态摘要
  - 再按主题归类给出逐条文章清单（含链接与时间）

## 用例 5：搜索受限时降级输出

- 场景：搜索 provider 只能返回主题摘要，拿不到稳定原文链接
- 输入：
  - 关键词：`伊朗`、`战争`、`AI`
  - 网站：`bbc.com`、`rfi.fr`、`dw.com`
  - 时间范围：最近 7 天
  - 频率：`一次性`
  - 返回条数：5
- 预期输出：
  - 允许保留“摘要总览”或“已发现结果”
  - 不输出正常 `文章清单`
  - 不写 `链接：暂无`、`链接：未稳定返回` 之类的占位文本
  - 改为明确说明：哪些主题只确认了方向、哪些条目因缺少稳定原始链接被排除

## intake_check.py 示例

### 输入不完整（生成追问 + 参数确认）

```bash
python3 scripts/intake_check.py \
  --topic "OpenAI,Gemini" \
  --time-range "最近 7 天"
```

### 输入完整（可直接确认）

```bash
python3 scripts/intake_check.py \
  --topic "OpenAI,Gemini" \
  --site "openai.com,blog.google" \
  --time-range "最近 24 小时" \
  --frequency "每日" \
  --limit 6 \
  --output-mode "按主题分组+逐条"
```

## build_query.py 示例

### 命令行快速生成（显式开启扩词与翻译词）

```bash
python3 scripts/build_query.py \
  -k "贪官,伊朗,战争,ai" \
  -s "bbc.com,nytimes.com,dw.com,rfi.fr" \
  --expand \
  --auto-english \
  -x "广告,招聘"
```

### 文件输入 + JSON 输出

`keywords.txt`:

```text
OpenAI
GPT-5
```

`sites.txt`:

```text
openai.com
github.com
```

```bash
python3 scripts/build_query.py \
  --keyword-file keywords.txt \
  --site-file sites.txt \
  --format json
```
