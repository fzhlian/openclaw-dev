# codex-dev

`codex-dev` 是一个面向 OpenClaw 的异步开发 skill，用于把 Codex 任务分发为后台作业，立即返回回执，并保存日志、摘要和补丁产物。  
`codex-dev` is an async development skill for OpenClaw that dispatches Codex work as background jobs, returns an immediate receipt, and stores logs, summaries, and patch artifacts.

## 核心能力 | Highlights

- 后台分发 Codex 开发任务，并立即返回作业回执。  
  Dispatch Codex development tasks in the background and return a job receipt immediately.
- 为每个作业保存 `task.txt`、`status.json`、`codex.out.log`、`summary.txt` 和 `patch.txt`。  
  Persist `task.txt`, `status.json`, `codex.out.log`, `summary.txt`, and `patch.txt` for every job.
- 支持 Telegram 完成通知，适合手机驱动的开发流程。  
  Support Telegram completion notifications for phone-driven development workflows.
- 支持 `--workdir`，可显式指定实际执行目录。  
  Support `--workdir` to explicitly control the execution directory.
- 为 OpenClaw 本地安装、社区发布和脚本维护提供统一项目结构。  
  Provide a single project layout for local OpenClaw installation, community publishing, and script maintenance.

## 快速开始 | Quick Start

```bash
./bin/codex-help
./bin/codex-dev "修复一个小问题并总结修改"
./bin/codex-dev-status <job-id>
./bin/codex-dev-show <job-id>
```

## 项目结构 | Project Structure

- `skill/`  
  OpenClaw / ClawHub 可发布 skill 包。  
  The publishable OpenClaw / ClawHub skill package.
- `bin/`  
  本地便捷命令包装。  
  Local convenience command wrappers.
- `docs/`  
  迁移说明、目录规范和后续维护文档。  
  Migration notes, layout conventions, and maintenance documentation.

推荐先阅读：  
Recommended reading:

- [`docs/migration.md`](docs/migration.md)
- [`docs/conventions.md`](docs/conventions.md)

## 本地安装映射 | Local Install Mapping

以下本地入口应指向本项目：  
The following local entrypoints should resolve to this project:

- `~/.openclaw/skills/codex-dev`
- `~/.openclaw/publish/codex-dev`
- `~/bin/codex-dev`
- `~/bin/codex-help`
- `~/bin/codex-dev-status`
- `~/bin/codex-dev-show`
- `~/bin/codex-dev-dispatch`
- `~/bin/codex-dev-worker`

## 发布 | Publishing

发布源目录：`skill/`  
Publish source directory: `skill/`

示例：  
Example:

```bash
clawhub publish ./skill --slug codex-dev --version 0.1.1
```

## 文档规范 | Documentation Policy

本项目约定所有 Markdown 文档默认采用中英文双语。  
This project requires all Markdown documentation to be maintained in Chinese and English by default.

## 相关文档 | Related Docs

- [`skill/SKILL.md`](skill/SKILL.md)
- [`skill/references/local-setup.md`](skill/references/local-setup.md)
- [`CHANGELOG.md`](CHANGELOG.md)
