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

## 审批稳定性

- 如果 Telegram 侧已经收到 exec 审批单，在用户完成 `/approve` 前，不要重启 `openclaw-gateway.service`
- gateway 重启会使当前待审批 ID 失效，随后 Telegram 会报 `unknown or expired approval id`
- 需要调整 agent、workspace、gateway 配置时，优先避开待审批窗口；必要时先让用户重新触发一次命令，再处理配置变更
