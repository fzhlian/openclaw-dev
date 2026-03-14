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

## 最小闭环结果示意

```markdown
## 摘要总览
- OpenAI policy update
- OpenAI roadmap note

## 文章清单
1. **OpenAI policy update**
   - 摘要：policy summary from search result
   - 来源：openai.com ｜ 时间：时间未标注
   - 链接：https://openai.com/index/policy-update

2. **OpenAI roadmap note**
   - 摘要：roadmap summary
   - 来源：openai.com ｜ 时间：2026-03-14
   - 链接：https://openai.com/index/roadmap

## 检索参数
- 关键词：OpenAI
- 网站：openai.com
- 时间范围：最近 7 天
- 结果数：2
```

## 适用边界

这个示例用于验证当前 skill 的最小闭环是否连通，不负责：

- 真实联网检索质量
- 多主题分组摘要
- 多站点混合聚合后的排序策略
- 更复杂的摘要压缩或主题归纳
- 搜索 provider 只能返回主题方向、却拿不到稳定原文链接时的降级输出（该场景改看 `references/validation.md` 的“缺少稳定链接时必须降级”）
