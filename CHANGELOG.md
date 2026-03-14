# Changelog | 更新日志

All notable changes to this project will be tracked here.  
本项目的重要变更都会记录在这里。

## [Unreleased] | [未发布]

- Added a minimal bilingual `CONTRIBUTING.md` for collaboration rules.  
  增加最小双语 `CONTRIBUTING.md`，明确协作规则。
- Polished the GitHub homepage README to use repository-friendly links and commands.  
  调整 GitHub 首页 README，改为适合公开仓库的链接和命令写法。
- Prepared the next community publish update after repository cleanup and documentation polish.  
  在仓库清理和文档整理后，准备下一次社区发布更新。
- Aligned the Telegram-bound OpenClaw agent with the local `openclaw-dev` repository context and renamed the historical agent to `openclaw-dev-codex`.  
  将 Telegram 侧 OpenClaw agent 与本地 `openclaw-dev` 仓库上下文对齐，并把历史 agent 重命名为 `openclaw-dev-codex`。
- Added repository-root and wrapper bootstrap guidance so Telegram sessions start from the same project assumptions as local IDE work.  
  增加仓库根与 wrapper bootstrap 指引，使 Telegram 会话与本地 IDE 共享同一套项目前提。
- Documented an exec-approval stability rule: do not restart the gateway while a Telegram approval prompt is waiting, or the approval id will expire.  
  记录 exec 审批稳定性规则：Telegram 审批单等待期间不要重启 gateway，否则审批 ID 会失效。
- Verified that `gh release create` required adding the `workflow` scope to GitHub CLI, and confirmed local release creation after refreshing auth.  
  验证 `gh release create` 需要为 GitHub CLI 增加 `workflow` scope，并在刷新授权后确认本地可成功创建 release。

## [0.1.1] - 2026-03-14

- Split `codex-dev` out of the `DataHz` workspace into an independent project.  
  将 `codex-dev` 从 `DataHz` 工作区拆出，迁移为独立项目。
- Added a publishable OpenClaw skill package under `skill/`.  
  在 `skill/` 下补齐可发布的 OpenClaw skill 包。
- Added stable local command wrappers under `bin/`.  
  在 `bin/` 下增加稳定的本地命令包装。
- Added Chinese and bilingual skill documentation.  
  增加中文与双语 skill 文档。
- Added async job dispatch, status inspection, summary inspection, and workdir support.  
  增加异步作业分发、状态查询、摘要查询和工作目录支持。
- Added optional Telegram notification support for background jobs.  
  增加后台作业的可选 Telegram 通知支持。
