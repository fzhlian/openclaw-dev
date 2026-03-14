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

### 4. Skill 预检查

测试语句：

```text
继续完善今天的 news-digest 技能；先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案。
```

通过标准：

- 预检查优先使用 `codex-dev-skill-inspect skills/news-digest`
- 不展开成 `git status + git diff + find + rg` 长链
- 回答基于真实仓库状态

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
