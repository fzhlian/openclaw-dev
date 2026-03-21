# BOOTSTRAP.md - openclaw-dev

每次新会话先做这几件事：

1. 确认真实仓库是 `/home/fzhlian/Code/codex-dev`
2. 先读 `AGENTS.md`
3. 再按需读：
   - `README.md`
   - `docs/conventions.md`
   - `skill/SKILL.md`
   - `skill/references/local-setup.md`
4. 先看 git 状态和相关文件，再决定是否修改
5. 需要修改时，优先做小而清晰、可验证的改动
6. 先确认根因、影响面和现有实现模式，再决定改动范围
7. 修改后优先做最小验证，并明确哪些部分已验证、哪些部分未验证
8. 若用户已经明确要求继续开发，且目标范围清晰，则直接实施；不要在给出最小方案后再次停下等确认
9. 若用户提到“刚才的方案”，先看当前线程可见上下文；若确实缺失，则简短请求用户重贴，不要主动翻 `~/.openclaw` 会话日志
10. 若用户要继续某个 skill，先用单一 helper 看 skill 现状；优先 `codex-dev-skill-inspect <skill-path>`，避免巨型只读命令链
11. 若 `codex-dev-skill-inspect` 已能回答问题，不要再追加 `git diff`、`find`、`rg` 等补充只读命令
12. 若用户原话接近“继续完善今天的 news-digest 技能；先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案”，则直接运行 `codex-dev-skill-inspect skills/news-digest`
13. 对上面这个范例，不要自行展开成 `git status + git diff + find + rg` 的组合命令
14. 若用户问“当前 OpenClaw 有哪些你自己开发的 skill / agent / workspace”，则直接运行 `codex-dev-assets-inspect`
15. 对这类资产盘点问题，必须同时覆盖仓库内 `skills/`、可发布 `skill/`、运行态 `~/.openclaw/skills`、`~/.openclaw/openclaw.json` 的 agent 列表，以及仓库 / 运行态 workspace 配置
16. 对资产盘点、状态说明、规则分工这类解释型请求，默认先给简短结论；除非用户明确要求展开，否则不要自动写成长篇分层说明
17. 若用户在这类解释型线程里只说“继续”，默认只补新的关键信息，不要把完整结构再讲一遍，也不要主动附带多条后续选项
18. 若用户要把资产盘点整理成仓库文档，预检查仍应先从 `codex-dev-assets-inspect` 开始；只在需要确认落盘位置时补最小文件存在性检查
19. 若用户只是打招呼、寒暄、确认你是否在线，先按闲聊简短回应；不要误判成继续上一个任务
20. 若用户要“整理成一份可放仓库的资产清单.md”之类文档写请求，按写入型请求处理；Telegram 侧优先后台分发，不要内联 `git add/commit`
21. 若用户说“切换到 codex 开发”，默认理解为切到 `openclaw-dev-codex` 仓库开发上下文，而不是清空当前开发位
22. 若用户说“审查代码”或“重新审查当前项目”，即使工作区干净，也继续查看最近提交或当前模块；不要停在 `git status`
23. 若用户要切换 skill / agent / 项目，先做模糊匹配；唯一命中才切，多个命中就让用户选，零命中就直说不存在
24. 切换项目时不要凭名字猜目标；候选集合优先来自 `codex-dev-assets-inspect`
25. 模糊匹配不只看字面，也看常见中英语义别名和 slug 对应；例如 `文章收集` 可对应 `article-digest`，`新闻` 可对应 `news-digest`，但前提仍是候选真实存在
26. 若用户说的是语义名而不是精确名，则只有语义唯一命中时才能直接切；若同时命中多个语义接近候选（如 `article-digest`、`news-digest`），必须让用户选或确认
27. 若用户说“切换到新闻项目 / news 方向”，且唯一命中的是 `news-digest`，则直接切到 `news-digest`；不要停在半切换状态
28. 对项目切换不要自己拼 `find ... | rg ...` 这类候选检索；优先 `codex-dev-assets-inspect`
29. 若用户已明确说 `继续开发 news-digest`，第一条且唯一预检查就是 `codex-dev-skill-inspect skills/news-digest`；不要额外发文件枚举审批
30. 若用户要“升级 codex-dev 并发布到 OpenClaw / ClawHub”，先只跑一次 `codex-dev-publish-inspect`；不要同时发多张审批卡
31. 发布预检查只看 `skill/`、`README.md`、`CHANGELOG.md`；不要去查本仓库并不存在的 `package.json`
32. 若发布失败是 `Version already exists` 或远端版本查询限流，先收敛到“确认下一个版本号”；不要在未确认前连续改多个候选版本
33. 若某张审批已经超时、被拒绝或报 `unknown or expired approval id`，不要再让用户批准旧 ID；应重新发起新的真实审批
