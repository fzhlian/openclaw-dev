# end-to-end-example

用于展示 `news-digest` 当前最小完整闭环：

1. 需求采集
2. 查询生成
3. 结果归一化与过滤
4. 最终摘要渲染

这个示例不依赖真实联网检索，而是用最小样例文件模拟“检索候选结果”，用于验证 4 个脚本之间的衔接是否一致。

## 场景

- 主题：OpenAI
- 站点：`openai.com`
- 时间范围：最近 7 天
- 频率：一次性
- 结果数：2
- 输出模式：摘要总览 + 逐条清单

## Step 1：需求采集

执行：

```bash
python3 skills/news-digest/scripts/intake_check.py \
  --topic "OpenAI" \
  --site "openai.com" \
  --time-range "最近 7 天" \
  --frequency "一次性" \
  --limit 2 \
  --output-mode "摘要总览 + 逐条清单" \
  --format json
```

预期要点：

- `missingQuestions` 为空
- `confirm` 中包含关键词、网站、时间范围、频率、结果数、输出模式、输出语言

## Step 2：查询生成

执行：

```bash
python3 skills/news-digest/scripts/build_query.py \
  -k "OpenAI" \
  -s "openai.com" \
  --format json
```

预期要点：

- 输出查询：`site:openai.com OpenAI`
- `autoExpand` 为 `false`
- `autoEnglish` 为 `false`

## Step 3：模拟检索候选结果并过滤

准备样例文件 `sample-e2e-results.json`：

```json
[
  {
    "title": "OpenAI policy update",
    "url": "https://openai.com/index/policy-update",
    "description": "policy summary from search result",
    "snippetZh": "OpenAI 发布了新的政策更新摘要"
  },
  {
    "title": "OpenAI roadmap note",
    "url": "https://openai.com/index/roadmap",
    "summary": "roadmap summary",
    "summaryZh": "OpenAI 路线图更新聚焦后续产品方向",
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

执行：

```bash
python3 skills/news-digest/scripts/filter_results.py \
  --input sample-e2e-results.json \
  --site "openai.com" \
  --normalize \
  --keep-dropped
```

预期要点：

- `summary.input = 3`
- `summary.kept = 2`
- `summary.dropped = 1`
- 保留结果带有：`snippet`、`matchedDomain`、`normalizedUrl`
- 不在目标域名内的结果被丢弃

## Step 4：最终摘要渲染

将上一步过滤后的结果保存为 `sample-e2e-filtered.json` 后执行：

```bash
python3 skills/news-digest/scripts/render_digest.py \
  --input sample-e2e-filtered.json \
  --keywords "OpenAI" \
  --sites "openai.com" \
  --time-range "最近 7 天" \
  --frequency "一次性" \
  --limit 2
```

预期要点：

- 输出包含：
  - `## 摘要总览`
  - `## 文章清单`
  - `## 检索参数`
  - `## 局限与建议`
- 第一条没有 `publishedAt` 时，显示“时间未标注”
- 每条都带原始链接

## Step 4b：provider 受限时的降级渲染

当外部检索只能确认主题方向，拿不到稳定原文链接时，准备样例文件 `sample-e2e-degraded.json`：

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

执行：

```bash
python3 skills/news-digest/scripts/render_digest.py \
  --input sample-e2e-degraded.json \
  --keywords "伊朗,战争,AI" \
  --sites "bbc.com,rfi.fr" \
  --time-range "最近 7 天" \
  --frequency "一次性" \
  --limit 5
```

预期要点：

- 不输出 `## 摘要总览`
- 不输出 `## 文章清单`
- 输出：
  - `## 检索参数`
  - `## 已发现结果`
  - `## 局限与建议`
- `## 已发现结果` 中明确说明哪些站点/主题只确认了方向，哪些结果因缺少稳定链接被排除

## 最小闭环结果示意

```markdown
## 摘要总览
- OpenAI policy update
- OpenAI roadmap note

## 文章清单
1. **OpenAI policy update**
   - 摘要：OpenAI 发布了新的政策更新摘要
   - 来源：openai.com ｜ 时间：时间未标注
   - 链接：https://openai.com/index/policy-update

2. **OpenAI roadmap note**
   - 摘要：OpenAI 路线图更新聚焦后续产品方向
   - 来源：openai.com ｜ 时间：2026-03-14
   - 链接：https://openai.com/index/roadmap

## 检索参数
- 关键词：OpenAI
- 网站：openai.com
- 时间范围：最近 7 天
- 频率：一次性
- 结果数：2
- 输出模式：摘要总览 + 逐条清单
- 输出语言：中文

## 局限与建议
- 局限：来源受限、时间缺失或覆盖不足时，结论仅基于当前检索结果。
- 建议下一步：如需更高覆盖，可放宽时间范围、补充来源或显式开启扩词。
```

## 适用边界

这个示例用于验证当前 skill 的最小闭环是否连通，重点覆盖：

- 基础需求采集
- 标准字段归一化与过滤
- 正常摘要渲染
- provider 受限时的最小降级输出

这个示例仍不负责：

- 真实联网检索质量
- 多主题分组摘要
- 多站点混合聚合后的排序策略
- 更复杂的摘要压缩或主题归纳
- 更复杂的降级判定与回退策略（完整规则仍以 `references/validation.md` 为准）
