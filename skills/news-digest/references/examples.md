# examples

以下示例用于说明 `news-digest` 的典型输入方式与输出目标。

## 用例 1：日报

- 场景：每天汇总 AI 行业重点动态
- 输入：
  - 关键词：`OpenAI`、`Anthropic`、`Gemini`
  - 网站：`openai.com`、`anthropic.com`、`blog.google`
  - 时间范围：最近 1 天
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
  - 返回条数：12
- 预期输出：
  - 先给当日核心动态摘要
  - 再按主题归类给出逐条文章清单（含链接与时间）

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
