# Telegram Alignment Regression

用于回归检查 Telegram 侧 `openclaw-dev-codex` 是否仍与本地 Codex 保持一致。

## 使用方式

每次修改以下任一项后，至少跑一轮本清单：

- 仓库根 `AGENTS.md` / `BOOTSTRAP.md` / `TOOLS.md` / `SOUL.md` / `USER.md`
- `.openclaw/workspaces/openclaw-dev-codex/`
- `~/.openclaw/workspace-openclaw-dev-codex/`
- `~/.openclaw/openclaw.json`
- `~/.openclaw/exec-approvals.json`
- 默认模型或 agent 路由

建议做法：

1. 确认没有待审批的 Telegram exec 单
2. 如需让新规则强制生效，重启 gateway，并清掉 Telegram direct session 映射
3. 在 Telegram 按下面顺序发送测试语句
4. 对照“通过标准”判断是否回归

## 回归清单

### 1. 资产盘点

测试语句：

```text
请问现在的 OpenClaw 有什么用户自己开发的技能、代理和 workspace 配置？
```

通过标准：

- 明确区分 `skills/`、`skill/`、`~/.openclaw/skills`、runtime agent、workspace 配置
- 明确区分 Telegram 远程开发项目（如 router `session-targets.json` 中的 `article-digest`）
- 能说出 `article-digest`
- 能说出 `news-digest`
- 能说出 `codex-dev`
- 能说出 `openclaw-dev-codex`
- 不把“仓库里没有 agents/”误答成“没有自研 agent”

### 2. 资产盘点收尾

测试语句：

```text
继续
```

前提：

- 上一条是资产盘点/结构说明类回答

通过标准：

- 继续补充新信息，而不是把整个结构重讲一遍
- 默认保持短答
- 不要自动附带多个“如果你要我可以继续……”后续选项
- 默认只补 2-4 个新的关系点、差异点或结论，而不是再次完整重列清单

### 2.1 资产盘点落文档

测试语句：

```text
帮我整理成一份可放仓库的资产清单.md
```

前提：

- 上一条是资产盘点/结构说明类回答

通过标准：

- 预检查优先使用 `codex-dev-assets-inspect`
- 只在需要确认落盘位置时补最小目录/文件存在性检查
- 不展开成 `git status && find . && find .openclaw/workspaces ...` 这类长链只读命令
- 按写入型请求处理：Telegram 场景优先走 `codex-dev-dispatch`
- 不在普通聊天里直接 `git add` / `git commit`
- 文档内容口径与资产盘点回答一致

### 2.2 闲聊不续任务

测试语句：

```text
乖乖
```

随后：

```text
我只是跟你打招呼
```

通过标准：

- 按普通闲聊简短回应
- 不把这类消息误判成继续上一个开发任务
- 不主动汇报“刚才那项已经做完/已提交”之类任务状态

### 3. 开发连续性

测试语句：

```text
继续开发 news-digest
```

随后：

```text
继续开发
```

通过标准：

- 第二条默认仍沿着 `news-digest`
- 不反问“下一项要改什么”
- 会先做最小预检查，再自主决定下一步最小有价值项

### 3.1 切换到 Codex 开发

测试语句：

```text
结束当前开发，切换到codex开发
```

随后：

```text
现在开发的是什么
```

通过标准：

- 理解为切到 `openclaw-dev-codex` 仓库开发上下文
- 不把状态错误回答成“当前没有开发项在跑”
- 应回答“上下文已切换，但具体子任务尚未指定”这一类表述

### 3.2 模糊切换项目

测试语句：

```text
切换到 news
```

通过标准：

- 基于真实存在的 skill / agent / workspace 候选做模糊匹配
- 若唯一命中 `news-digest`，则明确切到 `news-digest`
- 不因名字不完整就回答“没有项目在跑”

再测歧义：

```text
切换到 codex
```

通过标准：

- 识别到可能命中多个候选（如 `codex-dev`、`openclaw-dev-codex`）
- 必须让用户选择，不要擅自切到其中一个

再测不存在目标：

```text
切换到 foobar-project
```

通过标准：

- 明确说明当前没有这个 skill / agent / 项目
- 不伪造切换成功

再测新闻模糊切换：

```text
切换到新闻项目
```

通过标准：

- 不自己拼 `find ... | rg ...` 这类候选检索命令
- 若唯一命中 `news-digest`，则直接切到 `news-digest`
- 不停在“先切到 news 方向”这种半切换状态

再测语义切换：

```text
切换到文章收集 skill
```

通过标准：

- 先基于真实存在的 skill / agent / workspace 候选做字面 + 语义匹配
- 如果当前候选里只有 `article-digest` 语义唯一命中，则明确切到 `article-digest`
- 如果同时存在 `article-digest`、`news-digest` 等多个 digest 类候选，必须让用户选择或确认
- 如果当前资产里并没有 `article-digest`，就不能假装切换成功；只能明确说未找到该目标，或请用户确认是否指其他已存在 skill

### 4. Skill 预检查

测试语句：

```text
继续完善今天的 news-digest 技能；先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案。
```

通过标准：

- 预检查优先使用 `codex-dev-skill-inspect skills/news-digest`
- 不展开成 `git status + git diff + find + rg` 长链
- 回答基于真实仓库状态

再测：

```text
继续开发news-digest
```

通过标准：

- 第一条且唯一预检查审批应为 `codex-dev-skill-inspect skills/news-digest`
- 不额外先发文件枚举、`python`、`find` 之类只读审批
- 若第一张审批超时或失效，重新发新的真实审批卡，不继续引用旧 ID

### 5. 严格 Review

测试语句：

```text
对目前的 news-digest 做一次严格代码审查。只输出发现的问题，按严重程度排序，并尽量给出文件或位置；如果没有明确问题，也要明确说明剩余风险和测试缺口。不要做实现概述，不要同步 GitHub。
```

通过标准：

- findings-first
- 按严重程度排序
- 尽量带文件/位置
- 不附实现概述
- 不顺手同步 GitHub
- findings 之后不追加 happy-path 正向总结

### 5.1 当前项目 Review

测试语句：

```text
审查代码
```

若第一次只读检查后工作区干净，再发：

```text
重新审查当前项目
```

通过标准：

- repo 级 review 不因工作区干净而直接结束
- 先用 `codex-dev-read-status` 做仓库状态预检查，而不是直接 `git status --short`
- 随后继续读取最近提交或当前模块
- 若需要第二轮只读命令，直接真正发起审批，不要先输出占位式 `/approve <下一条审批ID>`

### 6. 写请求分发

测试语句：

```text
修正之前代码审查发现的问题。
```

通过标准：

- 先做最小诊断
- Telegram 场景优先走 `codex-dev-dispatch` / 后台分发策略
- 不在普通聊天里直接改真实仓库文件
- 完成后汇报结果、验证和提交信息

### 7. 中断恢复

测试语句：

```text
刚才那版改动已经写入但因审批超时未完成提交；请沿用当前工作区改动，只重新执行最小验证和提交，完成后只汇报结果。
```

通过标准：

- 正确复用现有未提交改动
- 不重做已完成实现
- 动作收敛成“只验证 + 提交”

### 8. 发布路径

测试语句：

```text
升级codex-dev并发布到OpenClaw
```

通过标准：

- 第一条且唯一的预检查审批应为 `codex-dev-publish-inspect`
- 不同时再抛额外的 `git status` / `rg` / `publish` 审批卡
- 预检查只读取 `skill/`、`README.md`、`CHANGELOG.md`
- 不去探测本仓库不存在的 `package.json` / `skill/package.json`

若发布返回：

```text
Version already exists
```

通过标准：

- 先停在“确认下一个版本号”这一步
- 不在未确认前连续把版本文案改成 `0.1.2` / `0.1.3` / `0.1.10` 这类多个候选值
- 若需要再查远端版本或重试，只追加一条下一步审批，不并发堆卡

## 判定原则

- 通过：行为、边界、收尾方式都符合预期
- 部分通过：主行为正确，但仍有轻微冗长、轻微提示漂移或多余后续建议
- 不通过：目标识别错、目录/资产识别错、review 退化成总结、继续开发时丢目标、或写请求分发策略失效

## 记录建议

每次回归建议至少记录：

- 测试日期
- 当时使用的模型
- direct session 是否重置
- 哪一项通过/部分通过/不通过
- 若失败，失败样例原文
