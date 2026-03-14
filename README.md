# openclaw-dev

`openclaw-dev` 是一个面向本地 OpenClaw 环境的总开发仓库，用于集中维护 skills、agents、脚本入口、包装工作区约定，以及社区发布流程。  
`openclaw-dev` is a meta-repository for local OpenClaw development, used to maintain skills, agents, wrapper conventions, command entrypoints, and community publishing workflows in one place.

## 仓库定位 | Repository Scope

- 这是 OpenClaw 的总开发工作区仓库，不只是单一 skill。  
  This repository is the OpenClaw development workspace, not just a single skill.
- `codex-dev` 是当前最完整的独立 skill 项目，也是此仓库的核心示例。  
  `codex-dev` is the most complete standalone skill project here and serves as the main reference implementation.
- 运行态的 skills、agents、publish 映射和本地命令入口都围绕这个仓库进行维护。  
  Runtime skills, agents, publish mappings, and local command entrypoints are maintained around this repository.

## 当前核心项目 | Current Primary Project

当前仓库里的核心项目是 `codex-dev`，它提供：  
The primary project in this repository is `codex-dev`, which provides:

- 后台分发 Codex 开发任务，并立即返回作业回执。  
  Dispatch Codex development tasks in the background and return a job receipt immediately.
- 为每个作业保存 `task.txt`、`status.json`、`codex.out.log`、`summary.txt` 和 `patch.txt`。  
  Persist `task.txt`, `status.json`, `codex.out.log`, `summary.txt`, and `patch.txt` for every job.
- 支持 Telegram 完成通知，适合手机驱动的开发流程。  
  Support Telegram completion notifications for phone-driven development workflows.
- 支持 `--workdir`，可显式指定实际执行目录。  
  Support `--workdir` to explicitly control the execution directory.

## 快速开始 | Quick Start

```bash
./bin/codex-help
./bin/codex-dev "修复一个小问题并总结修改"
./bin/codex-dev-status <job-id>
./bin/codex-dev-show <job-id>
```

如需直接在 Telegram 中审批新的执行请求，请在本地 OpenClaw 配置里启用 `channels.telegram.execApprovals`。  
If you want to approve new exec requests directly from Telegram, enable `channels.telegram.execApprovals` in your local OpenClaw config.

## 项目结构 | Project Structure

- `skill/`  
  当前主项目 `codex-dev` 的可发布 OpenClaw / ClawHub skill 包。  
  The publishable OpenClaw / ClawHub skill package for the current primary project, `codex-dev`.
- `bin/`  
  本地稳定命令入口包装。  
  Stable local command wrappers.
- `.openclaw/`
  已纳入版本控制的 workspace 元数据，以及需要与本地运行态对齐的 wrapper 说明文件。
  Versioned workspace metadata and managed wrapper instruction files that mirror local runtime state when needed.
- `docs/`  
  总工作区约定、迁移说明和后续维护文档。  
  Meta-workspace conventions, migration notes, and maintenance documentation.

推荐先阅读：  
Recommended reading:

- [`docs/migration.md`](docs/migration.md)
- [`docs/conventions.md`](docs/conventions.md)
- [`docs/security-hardening.md`](docs/security-hardening.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)

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

当前主项目 `codex-dev` 的发布源目录：`skill/`  
Publish source directory for the current primary project `codex-dev`: `skill/`

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
