# TOOLS.md - openclaw-dev-codex

## 工具使用约定

- 读仓库状态、文档、git 信息：直接针对 `/home/fzhlian/Code/codex-dev`
- 搜索文本或文件：优先使用 `rg`
- 写文件型请求：优先使用 `/home/fzhlian/bin/codex-dev-dispatch`
- Telegram 会话内不要直接对真实仓库写文件；小改动也一样
- 若用户显式给出 `--workdir`，必须原样透传
- 若用户未给出 `--workdir`，默认使用 `/home/fzhlian/Code/codex-dev`
- 不要使用 wrapper workspace 的 `.git` 回答仓库问题
- 不要把当前一次任务参数固化成通用 skill 默认行为
- 能做最小验证时，优先先验证再回答
- 先用最少量的读操作把上下文和根因搞清楚，再决定调用什么工具
- 优先复用仓库已有脚本、文档和结构，不重复造轮子
- 仓库只读状态检查默认只使用 `/home/fzhlian/bin/codex-dev-read-status`
- 路径级 git 只读检查默认只使用 `/home/fzhlian/bin/codex-dev-git-path-report <path>`
- skill 目录预检查默认只使用 `/home/fzhlian/bin/codex-dev-skill-inspect <skill-path>`
- 对简单只读命令，避免依赖 shell 管道；能单命令完成就不要走 `| head` 之类组合
- `codex-dev-skill-inspect` 已返回 repo status、target status、target diff、target files、recent commits；默认不要再重复调用 `git diff` / `find`
- 对“先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案”这类请求，直接调用 `/home/fzhlian/bin/codex-dev-skill-inspect skills/news-digest`
- 避免把上面的请求展开成 `git status --short && git diff -- skills/news-digest && find skills/news-digest ...` 之类长链
- 如果任务是审查/review，先读目标文件或 diff，再输出 findings；不要只给实现概述
- 普通仓库任务默认不要读取 `~/.openclaw` 下的 sessions/logs/agents 目录来补上下文
- `memory_search`、`sessions_list`、`sessions_history` 仅用于显式日志/历史排查
