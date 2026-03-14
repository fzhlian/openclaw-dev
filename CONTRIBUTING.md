# Contributing | 参与贡献

感谢你为 `codex-dev` 做贡献。  
Thank you for contributing to `codex-dev`.

## 基本原则 | Ground Rules

- 所有 Markdown 文档默认采用中英文双语。  
  All Markdown documentation should be maintained in Chinese and English by default.
- 改动应尽量小而清晰，避免无关重构。  
  Keep changes small and clear, and avoid unrelated refactors.
- 改脚本时优先保持 Bash 实现简洁、可读、可移植。  
  Keep Bash scripts simple, readable, and portable.
- 任何会影响使用方式的改动，都要同步更新文档。  
  Any change that affects usage must update the documentation in the same change.

## 目录约定 | Layout Expectations

- `skill/` 用于可发布的 OpenClaw / ClawHub skill 包。  
  `skill/` contains the publishable OpenClaw / ClawHub skill package.
- `bin/` 用于本地稳定入口包装。  
  `bin/` contains stable local wrapper entrypoints.
- `docs/` 用于迁移说明、规范和维护文档。  
  `docs/` contains migration notes, conventions, and maintenance docs.

## 提交流程 | Submission Flow

1. 在本地完成改动。  
   Make the change locally.
2. 自查脚本语法和文档一致性。  
   Check script syntax and documentation consistency.
3. 使用清晰的 commit message。  
   Use a clear commit message.
4. 如果 skill 行为发生变化，考虑同步发布新版本。  
   If the skill behavior changes, consider publishing a new version.

## 最低检查项 | Minimum Checks

- 对改过的 Bash 脚本运行 `bash -n`。  
  Run `bash -n` on modified Bash scripts.
- 检查 `README.md`、`skill/SKILL.md` 和相关 reference 文档是否同步。  
  Keep `README.md`, `skill/SKILL.md`, and relevant reference docs in sync.
- 确认公开仓库文案不包含本机私有路径或私密配置。  
  Confirm public repository docs do not expose private local paths or secrets.
