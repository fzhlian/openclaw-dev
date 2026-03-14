# 自研资产清单 | Self-Developed Asset Inventory

本文档记录当前 `openclaw-dev` 工作区里由用户维护的 skill、agent 与 workspace 配置，并明确区分“仓库源码 / 可发布对象 / 运行态映射”。
This document records the user-maintained skills, agents, and workspace configuration in the current `openclaw-dev` workspace, and distinguishes between repository source, publishable artifacts, and runtime mappings.

## 1. 仓库内自研 skill | Repo Skills

### `skills/news-digest/`

- 类型：仓库内独立自研 skill 源码目录
- 关键文件：`skills/news-digest/SKILL.md`
- 当前状态：存在于仓库内，但本次盘点结果中未显示为运行态已安装 skill

- Type: standalone custom skill source directory in the repository
- Key file: `skills/news-digest/SKILL.md`
- Current status: present in the repository, but not shown as a runtime-installed skill in this inventory

## 2. 当前主可发布 skill | Current Primary Publishable Skill

### `skill/`

- 类型：当前主项目 `codex-dev` 的可发布 skill 目录
- 关键文件：`skill/SKILL.md`
- 运行态安装名：`codex-dev`
- 运行态来源：`/home/fzhlian/Code/codex-dev/skill`

- Type: publishable skill directory for the current primary project `codex-dev`
- Key file: `skill/SKILL.md`
- Runtime installed name: `codex-dev`
- Runtime source: `/home/fzhlian/Code/codex-dev/skill`

## 3. 运行态 agent | Runtime Agent

### `openclaw-dev-codex`

- 类型：当前本地运行态 agent
- workspace：`/home/fzhlian/Code/codex-dev`
- agentDir：`/home/fzhlian/.openclaw/agents/openclaw-dev-codex/agent`
- model：`openai-codex/gpt-5.4`

- Type: active local runtime agent
- Workspace: `/home/fzhlian/Code/codex-dev`
- Agent directory: `/home/fzhlian/.openclaw/agents/openclaw-dev-codex/agent`
- Model: `openai-codex/gpt-5.4`

## 4. 仓库内 workspace 配置源码 | Repo Workspace Configuration Source

### `.openclaw/workspaces/openclaw-dev-codex/`

当前已纳入版本控制的 workspace 配置文件：
Currently versioned workspace configuration files are:

- `BOOTSTRAP.md`
- `HEARTBEAT.md`
- `IDENTITY.md`
- `TOOLS.md`
- `USER.md`

这些文件用于定义该 workspace 的启动约定、身份、工具使用习惯和用户协作偏好。
These files define bootstrap rules, identity, tool usage conventions, and user collaboration preferences for the workspace.

## 5. 运行态 workspace 映射 | Runtime Workspace Mapping

### `~/.openclaw/workspace-openclaw-dev-codex/`

当前运行态 workspace 包含：
The current runtime workspace contains:

- `AGENTS.md`
- `BOOTSTRAP.md` -> `.openclaw/workspaces/openclaw-dev-codex/BOOTSTRAP.md`
- `HEARTBEAT.md` -> `.openclaw/workspaces/openclaw-dev-codex/HEARTBEAT.md`
- `IDENTITY.md` -> `.openclaw/workspaces/openclaw-dev-codex/IDENTITY.md`
- `SOUL.md`
- `TOOLS.md` -> `.openclaw/workspaces/openclaw-dev-codex/TOOLS.md`
- `USER.md` -> `.openclaw/workspaces/openclaw-dev-codex/USER.md`

说明：
Notes:

- `BOOTSTRAP.md / HEARTBEAT.md / IDENTITY.md / TOOLS.md / USER.md` 已与仓库内源码目录建立映射。
- `AGENTS.md` 与 `SOUL.md` 当前表现为运行态侧单独存在的文件，不在上述仓库 workspace 源码目录列表中。

- `BOOTSTRAP.md / HEARTBEAT.md / IDENTITY.md / TOOLS.md / USER.md` are mapped from the repository workspace source directory.
- `AGENTS.md` and `SOUL.md` currently appear as runtime-side standalone files and are not part of the versioned workspace source file list above.

## 6. 简短结论 | Short Summary

当前可明确识别的用户自研资产：
Currently identifiable user-maintained assets are:

- 仓库内自研 skill：1 个（`skills/news-digest`）
- 当前主可发布 skill：1 个（`skill/`，发布/安装为 `codex-dev`）
- 运行态 agent：1 个（`openclaw-dev-codex`）
- workspace：1 套（`openclaw-dev-codex`，含仓库源码与运行态映射）

- Repo custom skills: 1 (`skills/news-digest`)
- Primary publishable skill: 1 (`skill/`, published/installed as `codex-dev`)
- Runtime agents: 1 (`openclaw-dev-codex`)
- Workspaces: 1 (`openclaw-dev-codex`, including repo source and runtime mapping)
