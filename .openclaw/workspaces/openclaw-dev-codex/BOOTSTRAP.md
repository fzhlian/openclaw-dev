# BOOTSTRAP.md - openclaw-dev-codex

每次新会话先做这几件事：

1. 确认真实仓库是 `/home/fzhlian/Code/codex-dev`
2. 先读 `/home/fzhlian/Code/codex-dev/AGENTS.md`
3. 再按需读：
   - `/home/fzhlian/Code/codex-dev/README.md`
   - `/home/fzhlian/Code/codex-dev/docs/conventions.md`
   - `/home/fzhlian/Code/codex-dev/skill/SKILL.md`
   - `/home/fzhlian/Code/codex-dev/skill/references/local-setup.md`
4. 任何 git / 路径 / 仓库判断，都以 `/home/fzhlian/Code/codex-dev` 为准
5. 任何写入型请求，优先走 `codex-dev-dispatch`
6. 如果当前存在待处理的 Telegram exec 审批单，不要重启 gateway；先等 `/approve` 完成，或让用户重新触发命令
7. 对开发请求，先读相关文件和 git 状态，再确认根因、边界和最小改动面
8. 修改完成后优先做最小验证，并在回执或摘要里说明结果与剩余风险
9. 做只读仓库状态预检查时，默认只使用 `/home/fzhlian/bin/codex-dev-read-status`
10. 做路径级 git 只读检查时，默认只使用 `/home/fzhlian/bin/codex-dev-git-path-report <path>`
11. 若用户已经明确要求继续开发，且范围足够清晰，则完成最小诊断后直接实施，不要在方案阶段再次卡住
12. 若当前任务依赖上一条 Telegram 消息中的方案或上下文，不要主动清 session；优先保持会话连续
13. 若“上一条方案”在当前线程不可见，则简短要求用户重贴；不要主动翻 `~/.openclaw` 会话日志或调用 session/history 工具去猜
14. 若当前目标是继续某个 skill，优先用 `/home/fzhlian/bin/codex-dev-skill-inspect <skill-path>` 做预检查，避免多段只读命令链
15. 若 `codex-dev-skill-inspect` 已足够回答问题，不要追加第二轮只读命令
16. 若用户原话接近“继续完善今天的 news-digest 技能；先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案”，则直接运行 `/home/fzhlian/bin/codex-dev-skill-inspect skills/news-digest`
17. 对上面这个范例，不要自行展开成 `git status + git diff + find + rg` 的组合命令
18. 若用户已明确当前目标为 `news-digest`，后续只说“继续开发”时，默认继续该目标，不要要求用户重复指定下一项
19. 若用户要求“审查 / 复审 / review”，默认按 code review 处理：先查问题与风险，再给概述；不要退化成仓库状态总结
20. 若用户明确说“只输出发现的问题”，则 findings 后不要再补 happy path 说明、实现概述或下一步建议
21. 若用户问“当前 OpenClaw 有哪些你自己开发的 skill / agent / workspace”，默认直接运行 `/home/fzhlian/bin/codex-dev-assets-inspect`
22. 对这类资产盘点问题，必须同时覆盖仓库内 `skills/`、可发布 `skill/`、运行态 `~/.openclaw/skills`、`~/.openclaw/openclaw.json` 里的 agent 列表，以及仓库 / 运行态 workspace 提示配置
23. 若用户在这类说明线程里只说“继续”，默认只补新的关键信息，不要把完整结构重讲一遍，也不要主动附带多条后续选项
24. 若用户要把资产盘点结果整理成仓库文档，预检查仍应先从 `/home/fzhlian/bin/codex-dev-assets-inspect` 开始；只在需要确认落盘位置时补最小文件存在性检查
25. 若用户只是打招呼、寒暄、确认你在不在，先按闲聊简短回应；不要误判成继续上一个任务
26. 若用户要“整理成一份可放仓库的资产清单.md”之类文档写请求，按写入型请求处理；优先后台分发，不要内联 `git add/commit`
27. 若用户说“切换到 codex 开发”，默认理解为切到 `openclaw-dev-codex` 仓库开发上下文，而不是清空当前开发位
28. 若用户说“审查代码”或“重新审查当前项目”，即使工作区干净，也继续查看最近提交或当前模块；不要停在 `git status`
29. 若用户要切换 skill / agent / 项目，先做模糊匹配；唯一命中才切，多个命中就让用户选，零命中就直说不存在
30. 切换项目的候选集合优先来自 `/home/fzhlian/bin/codex-dev-assets-inspect`
31. 模糊匹配不只看字面，也看常见中英语义别名和 slug 对应；例如 `文章收集` 可对应 `article-digest`，`新闻` 可对应 `news-digest`，但候选仍必须真实存在
32. 若用户说的是语义名而不是精确名，则只有语义唯一命中时才能直接切换；若同时命中多个语义接近候选（如 `article-digest`、`news-digest`），必须让用户选或确认
33. 若用户说“切换到新闻项目 / news 方向”，且唯一命中的是 `news-digest`，则直接切到 `news-digest`；不要停在半切换状态
34. 若用户已明确说 `继续开发 news-digest`，第一条且唯一预检查就是 `/home/fzhlian/bin/codex-dev-skill-inspect skills/news-digest`
35. 若用户要“升级 codex-dev 并发布到 OpenClaw / ClawHub”，先只跑一次 `/home/fzhlian/bin/codex-dev-publish-inspect`
36. 发布预检查只看真实存在的 `skill/`、`README.md`、`CHANGELOG.md`；不要去查这个仓库里没有的 `package.json`
37. 若发布失败是 `Version already exists` 或远端版本查询限流，先停在“确认下一个版本号”；不要连续把版本文案改成多个候选值
38. 若某张审批已经超时、被拒绝或报 `unknown or expired approval id`，不要继续要求用户批准旧 ID；应重新发一张新的真实审批卡
