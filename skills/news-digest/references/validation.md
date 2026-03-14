# validation

用于手动验证 `news-digest` 当前最小闭环是否可用。优先验证脚本输出与 `SKILL.md` 中的执行约束是否一致。

## 目标

确认以下 2 个环节都能正常工作：

1. 需求不完整时，先生成缺项追问与参数确认块
2. 参数确认后，能按站点生成可执行的查询列表

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

## 回归检查

修改 `SKILL.md` 后，再检查以下约束仍成立：

1. 未确认参数前，不直接进入检索
2. `--expand` / `--auto-english` 只在必要时显式开启
3. 结果不足时，先放宽时间范围，再扩词，再英文化，最后才放宽站点
4. 最终输出仍要求逐条附链接，并明确局限
