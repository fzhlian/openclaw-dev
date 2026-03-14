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
