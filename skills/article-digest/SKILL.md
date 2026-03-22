---
name: article-digest
description: 从 Telegram 接收文章链接，抓取正文，生成全文摘要、主要内容、可信度评估与 AI 痕迹估算，并默认直接推送单篇结果到 Telegram；若明确要求统一发送，则写入 SQLite 队列后定时发送 digest。同时支持文章收藏、回看收藏和取消收藏。
---

# 文章研判

这个 skill 负责把“文章研判”变成稳定流水线，而不是把所有逻辑塞给一次性 agent 推理。

## 触发条件

当用户消息包含以下任一模式时使用本 skill：

- 一个或多个 URL
- “帮我收录这篇 / 这几篇”
- “晚上统一发给我”
- “立即分析这篇”
- “收藏这篇 / 收藏刚才这篇 / 收藏 3”
- “查看收藏 / 回看收藏 / 回看收藏 3 / 取消收藏 3”

如果消息中没有可识别 URL，返回简短错误说明，不做长回复。
如果 Telegram 消息主体只是一个或多个 URL，也应直接触发本 skill，不要先把链接写入临时文件或输出伪造工具标签。

## 行为规则

1. 先提取消息中的 URL。
2. 优先直接执行 `scripts/ingest_message.py "<原始消息>"`；只在明确单 URL 且需要命令行查看完整结果时执行 `scripts/ingest_url.py <url> --immediate`。
3. 默认行为是：抓取、分析、写库后，直接推送单篇结果到 Telegram。
4. 如果用户明确说“晚上统一发给我 / 加入队列 / 稍后发送”，才保留为 `queued`，等待 `send_digest.py` 统一发送。
5. 抽取失败时仍保留最小记录，并标记 `extract_failed`。
6. “核心摘要”必须基于全文信息提炼，用 1-2 句话交代文章主要内容，不能只截首段。
7. “主要内容”应比摘要更具体，帮助用户快速知道文章大体在讲什么，禁止输出空泛的“主线一/主线二”式占位文案。
8. 当用户发出收藏相关命令时，优先走数据库收藏流程，而不是重新让模型自由发挥。

## 风险约束

- 可信度评估不是最终事实裁决。
- AI 成分估算只是启发式判断，不是法医级鉴定。
- 禁止输出“已证实为假”“确定是 AI 写的”这类绝对裁决文案。

## 运行入口

- 单链接处理：`skills/article-digest/scripts/ingest_url.py <url>`
- 消息级处理：`skills/article-digest/scripts/ingest_message.py "<telegram text>"`
- 只入队不推送：`skills/article-digest/scripts/ingest_url.py <url> --仅入队`
- 命令行返回单篇完整研判：`skills/article-digest/scripts/ingest_url.py <url> --immediate`
- 初始化数据库：`python3 skills/article-digest/scripts/init_db.py`
- 定时发送：`python3 skills/article-digest/scripts/send_digest.py`
- 生成或安装 cron：`python3 skills/article-digest/scripts/install_cron.py [--apply]`
- 重试失败任务：`python3 skills/article-digest/scripts/retry_failed.py`

## 参考资料

- 评分规则：读取 `references/scoring-rules.md`
- 输出格式：读取 `references/output-format.md`
- 提示语与产品文案：读取 `references/prompts.md`
