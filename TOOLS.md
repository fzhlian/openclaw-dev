# TOOLS.md - openclaw-dev

## 工具使用约定

- 读仓库状态、文档、git 信息：直接针对 `/home/fzhlian/Code/codex-dev`
- 搜索文本或文件：优先使用 `rg`
- 修改文件前：先确认目标文件当前状态和相关 diff
- 修改完成后：优先做最小验证
- 在 Telegram 运行环境里，写入型请求优先使用 `codex-dev-dispatch`
- 先用现有文件、git 状态和最小命令把问题定位清楚，再选择工具
- 优先复用仓库已有脚本、文档和约定，不重复造轮子
- Telegram 侧做只读仓库状态检查时，默认只调用 `codex-dev-read-status`
- Telegram 侧做路径级 git 只读检查时，默认调用 `codex-dev-git-path-report <path>`
- Telegram 侧做 skill 目录预检查时，默认调用 `codex-dev-skill-inspect <skill-path>`
- Telegram 侧做 OpenClaw 自研资产盘点时，默认调用 `codex-dev-assets-inspect`
- 对简单只读查询，避免不必要的 shell 管道；优先直接调用单一命令或已有 helper
- `codex-dev-skill-inspect` 已覆盖 repo status、target status、target diff、target files、recent commits；默认不要再额外拼 `git diff` 或 `find`
- 对“先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案”这类请求，直接调用 `codex-dev-skill-inspect skills/news-digest`
- 避免把上面的请求展开成 `git status --short && git diff -- skills/news-digest && find skills/news-digest ...` 之类长链
- 对“当前 OpenClaw 有哪些你自己开发的 skill / agent / workspace”这类请求，不要只看 `skills/`；必须区分仓库内 skill、可发布 `skill/`、运行态已安装 skill、运行态 agent、以及 workspace 配置
- 普通仓库任务默认不要读取 `~/.openclaw` 下的 sessions、logs、agents 目录来补“刚才的方案”
- `memory_search`、`sessions_list`、`sessions_history` 只用于用户显式要求的日志/历史排查，不用于普通开发续写
