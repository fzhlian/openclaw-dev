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
