# AGENTS.md

本仓库是 `openclaw-dev` 总开发工作区，不是业务项目仓库。

## 仓库定位

- 真实项目根目录：`/home/fzhlian/Code/codex-dev`
- 当前核心可发布 skill 项目：`skill/` 对应的 `codex-dev`
- 运行态映射、agent 配置、wrapper workspace 也围绕这个仓库维护

## 工作原则

- 先在本仓库完成判断，再决定是否需要查看 `~/.openclaw/skills`、`~/.openclaw/agents`、`~/.openclaw/workspace-*`
- 需要修改可发布 skill 时，优先编辑仓库源码，而不是直接改运行态副本
- 需要修改 agent 路由、审批、会话、workspace 约定时，再去改 `~/.openclaw/*`
- 任何会写文件的请求，都必须明确目标目录；默认工作目录是 `/home/fzhlian/Code/codex-dev`

## 开发行为

- 先读现有文件和 git 状态，再下结论，不要跳过仓库上下文直接凭印象回答
- 搜索文本或文件时，优先使用 `rg`
- 优先做小而清晰、可验证的修改，不做与当前目标无关的扩散性重构
- 修改完成后，尽量做最小验证，并明确告诉用户验证结果或未验证部分
- 如果用户要求 review，先给发现的问题，再给概述
- 回答保持简洁直接，少做寒暄，少重复铺垫
- 语气保持中性、专业、克制；不要使用“爸爸”“宝贝”“亲爱的”等亲密或角色扮演式称呼
- 即使用户使用了亲昵称呼，也不要模仿；技术汇报仍保持正常工程口吻
- 不要用表演式、撒娇式或过度拟人化表达来包裹技术结果

## 开发逻辑

- 先建立上下文：确认目标文件、相关约定、当前 diff、分支状态和用户真正目标
- 先诊断后动手：优先解释根因、边界和影响面，再决定最小改动方案
- 保持和现有仓库风格一致：沿用已有命名、结构、文档组织和实现模式
- 区分通用能力与一次性任务：任务专用参数写到 example、reference 或 preset，不污染通用默认行为
- 先完成主目标，再处理顺手问题；顺手问题若会扩大改动面，应单独说明
- 修改后优先做最小闭环：至少确认目标文件、关键命令或关键路径已按预期工作
- 结论要基于真实文件和实际结果，不用聊天惯性、历史印象或模板文本代替当前仓库事实
- 若用户已经明确发出开发/修改请求，且范围足够清晰，则在完成最小诊断后直接实施；不要重复停在“如果你同意我再改”
- 只有在范围冲突、风险显著扩大、会碰到无关脏改动，或目标仍不明确时，才额外请求确认
- 若用户提到“刚才/上一条/前面那个方案”，先以当前线程可见上下文为准；若当前线程里确实没有，就用一句话请求用户重贴，不要自己去猜
- 对普通仓库开发任务，不要通过 `memory_search`、`sessions_*` 或 `~/.openclaw` 会话日志去回溯“刚才的方案”；只有用户明确要求查日志/查历史记录时才这么做

## Telegram 与本地对齐规则

- Telegram 侧和本地 IDE 侧都应以这个仓库为主上下文
- 不要把 wrapper workspace 当成真实源码仓库
- 不要把当前一次任务的关键词、站点、项目名固化成通用 skill 的默认行为
- 如果某次任务需要固定配置，应写成 example、reference 或单独 preset，而不是写进通用默认路径
- 对通用 skill 的修改，先考虑可复用性，再考虑本次任务便利性

## 推荐阅读顺序

1. `README.md`
2. `docs/conventions.md`
3. `skill/SKILL.md`
4. `skill/references/local-setup.md`
5. 需要时再看 `~/.openclaw/openclaw.json`、`~/.openclaw/exec-approvals.json`

## 写入型请求

- 本地直接开发：可直接在当前仓库修改并验证
- Telegram 异步开发：优先走 `codex-dev` / `codex-dev-dispatch`
- 如果用户显式给出 `--workdir`，必须原样透传
- 如果用户未给出 `--workdir`，默认使用 `/home/fzhlian/Code/codex-dev`
- Telegram 侧开发也应遵守和本地一样的判断顺序：先读上下文，再确定改动，再决定执行路径
- 对会明显扩大范围的写入，应先收窄变更面，再继续实现
- Telegram 侧做仓库只读预检查时，必须优先使用 `codex-dev-read-status`，不要默认调用 `git status`
- 只有在 `codex-dev-read-status` 无法满足问题时，才允许补充其他只读 git 命令
- 如果只需查看某个子目录或文件的 git 状态与最近提交，优先使用 `codex-dev-git-path-report <path>`
- 如果要同时看“仓库状态 + 某个 skill 目录现状”，优先使用 `codex-dev-skill-inspect <skill-path>`，不要再拼一长串 `pwd && git status && find && rg`
- 对“先检查当前仓库状态和某个 skill 现状，再给方案”这类请求，默认必须使用 `codex-dev-skill-inspect <skill-path>`；只有用户显式要求更细的 diff/grep 时，才额外补命令
- 字面范例：如果用户说“继续完善今天的 news-digest 技能；先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案”，默认第一条也是唯一预检查命令应为 `codex-dev-skill-inspect skills/news-digest`
- 对上述范例，不要改写成 `git status && git diff && find ...` 或 `pwd && ...` 这类多段只读命令链
- 若用户已经明确要求继续开发，则完成必要预检查后直接进入实现、验证和汇报，不要把“最小方案”再次当成阻塞点

## 审批稳定性

- 如果 Telegram 侧已经收到 exec 审批单，在用户完成 `/approve` 前，不要重启 `openclaw-gateway.service`
- gateway 重启会使当前待审批 ID 失效，随后 Telegram 会报 `unknown or expired approval id`
- 需要调整 agent、workspace、gateway 配置时，优先避开待审批窗口；必要时先让用户重新触发一次命令，再处理配置变更
- 如果正在做“多轮连续开发对齐”测试，不要主动清空 Telegram session；否则新一轮会看不到上一条里刚给出的最小方案或上下文
