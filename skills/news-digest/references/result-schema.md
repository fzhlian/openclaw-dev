# result-schema

用于约定 `news-digest` 在“外部检索结果 -> 过滤结果 -> 最终摘要”之间的最小数据接口，避免不同检索来源输出结构不一致。

## 最小结果对象

进入过滤阶段前，先尽量整理为以下字段：

```json
{
  "title": "文章标题",
  "url": "https://example.com/post",
  "snippet": "搜索摘要或抓取后的核心片段",
  "snippetZh": "供最终中文输出使用的摘要",
  "publishedAt": "2026-03-14",
  "sourceDomain": "example.com"
}
```

其中：

- `title`：必填；用于最终输出与标题去重
- `url`：必填；用于域名校验、链接输出与 URL 去重
- `snippet`：建议提供；作为摘要阶段的基础材料
- `snippetZh` / `summaryZh`：可选但推荐；若最终输出语言是中文，优先使用这些字段
- `publishedAt`：可缺失；缺失时不要编造，最终输出标注“时间未标注”
- `sourceDomain`：建议提供；缺失时可由 URL 提取主域名

## 归一化要求

在调用 `scripts/filter_results.py` 前，先做以下整理：

1. 丢弃明显缺少 `title` 或 `url` 的条目，或接受其被过滤脚本丢弃
2. 将不同搜索源中的摘要字段（如 `description`、`summary`、`content`）统一映射到 `snippet`
3. 若上游已经完成中文摘要整理，可额外提供 `snippetZh` 或 `summaryZh`
4. 将不同时间字段（如 `published_at`、`date`、`time`）统一映射到 `publishedAt`
5. 将来源字段（如 `domain`、`site`、`source`）统一映射到 `sourceDomain`
6. 若没有 `sourceDomain`，从 `url` 解析主域名

## 过滤后结果

`filter_results.py` 当前会补充以下字段：

- `matchedDomain`
- `normalizedUrl`
- `normalizedTitle`

摘要阶段应优先使用过滤后的结果对象，不要回退到原始搜索结果混合总结。

## 降级输出载荷

当搜索 provider 只能返回主题方向、摘要片段，或结果被过滤后已不足以形成有效摘要时，可直接构造降级输出载荷给 `render_digest.py`：

```json
{
  "results": [],
  "forceDegraded": true,
  "discoveredResults": [
    {
      "topic": "BBC",
      "note": "仅确认伊朗相关主题方向，未拿到稳定原文链接"
    },
    {
      "site": "rfi.fr",
      "detail": "确认存在 AI 与信息战相关结果，但当前 provider 未返回可直接落地的原文 URL"
    }
  ]
}
```

约定：

- `results`：保留为空列表，表示不输出正常 `文章清单`
- `forceDegraded`：显式要求走降级渲染
- `discoveredResults`：可选；用于承载“已发现结果”
- `findings`：可选；与 `discoveredResults` 等价，可作为兼容别名
- `discoveredResults[*].topic/title/site`：三者取其一作为条目标识
- `discoveredResults[*].summary/note/detail`：三者取其一作为条目说明
- 若没有 `discoveredResults`，降级输出中的 `## 已发现结果` 会回落为“暂未拿到满足约束的可输出结果”

## 进入摘要前的最低要求

进入摘要前，结果列表至少应满足：

- 每条都有 `title`
- 每条都有可点击的 `url`
- 每条都已通过目标域名过滤
- 重复 URL / 重复标题已完成基础去重
- 缺失时间的条目已显式准备输出为“时间未标注”
- 若某条结果只有主题方向、摘要片段或搜索摘要，但拿不到稳定原始 URL，应在进入摘要前剔除
- 若剔除缺链接条目后已不足以形成有效摘要，不输出正常 `文章清单`，改走“检索参数 + 已发现结果 + 局限说明”

## 输出映射建议

最终逐条输出时，优先按以下映射：

- 标题：`title`
- 摘要：优先 `snippetZh` / `summaryZh`，否则退回 `snippet`
- 来源：优先 `matchedDomain`，否则 `sourceDomain`
- 时间：`publishedAt`，缺失则写“时间未标注”
- 链接：`url`
- 不要把 `暂无链接`、`未稳定返回链接`、`仅确认主题方向` 一类占位文本写进 `链接` 字段
