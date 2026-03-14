# 自研资产清单

本文档记录当前 `openclaw-dev` 工作区内由用户维护的 skill、agent 与 workspace 配置，并明确区分：

- 仓库源码
- 可发布对象
- 运行态映射

## 1. 总览

### 1.1 仓库内自研 skill

- `skills/news-digest/`
  - 关键文件：`skills/news-digest/SKILL.md`
  - 性质：仓库内独立 skill 源码目录
  - 当前状态：存在于仓库中，但当前盘点结果里未显示为运行态已安装 skill

### 1.2 当前主可发布 skill

- `skill/`
  - 关键文件：`skill/SKILL.md`
  - 性质：当前主项目 `codex-dev` 的可发布 skill 目录
  - 运行态安装名：`codex-dev`
  - 运行态来源：`/home/fzhlian/Code/codex-dev/skill`

### 1.3 运行态 agent

- `openclaw-dev-codex`
  - workspace：`/home/fzhlian/Code/codex-dev`
  - agentDir：`/home/fzhlian/.openclaw/agents/openclaw-dev-codex/agent`
  - model：`openai-codex/gpt-5.4`

### 1.4 workspace 配置

- 仓库内 workspace 源码：`.openclaw/workspaces/openclaw-dev-codex/`
- 运行态 workspace：`/home/fzhlian/.openclaw/workspace-openclaw-dev-codex/`

## 2. 分类清单

### 2.1 仓库内 skill 源码

| 名称 | 路径 | 说明 |
| --- | --- | --- |
| news-digest | `skills/news-digest/` | 仓库内独立自研 skill，当前未显示为运行态已安装 |

### 2.2 可发布 skill

| 名称 | 路径 | 说明 |
| --- | --- | --- |
| codex-dev | `skill/` | 当前运行态已安装 skill 对应的可发布源码目录 |

### 2.3 运行态已安装 skill

| 安装名 | 来源路径 | 对应源码 |
| --- | --- | --- |
| codex-dev | `/home/fzhlian/Code/codex-dev/skill` | `skill/` |

### 2.4 运行态 agent

| 名称 | workspace | agentDir | model |
| --- | --- | --- | --- |
| openclaw-dev-codex | `/home/fzhlian/Code/codex-dev` | `/home/fzhlian/.openclaw/agents/openclaw-dev-codex/agent` | `openai-codex/gpt-5.4` |

### 2.5 仓库内 workspace 配置文件

目录：`.openclaw/workspaces/openclaw-dev-codex/`

- `BOOTSTRAP.md`
- `HEARTBEAT.md`
- `IDENTITY.md`
- `TOOLS.md`
- `USER.md`

### 2.6 运行态 workspace 文件

目录：`/home/fzhlian/.openclaw/workspace-openclaw-dev-codex/`

- `AGENTS.md`
- `BOOTSTRAP.md` -> `/home/fzhlian/Code/codex-dev/.openclaw/workspaces/openclaw-dev-codex/BOOTSTRAP.md`
- `HEARTBEAT.md` -> `/home/fzhlian/Code/codex-dev/.openclaw/workspaces/openclaw-dev-codex/HEARTBEAT.md`
- `IDENTITY.md` -> `/home/fzhlian/Code/codex-dev/.openclaw/workspaces/openclaw-dev-codex/IDENTITY.md`
- `SOUL.md`
- `TOOLS.md` -> `/home/fzhlian/Code/codex-dev/.openclaw/workspaces/openclaw-dev-codex/TOOLS.md`
- `USER.md` -> `/home/fzhlian/Code/codex-dev/.openclaw/workspaces/openclaw-dev-codex/USER.md`

## 3. 关系说明

### 3.1 `skills/news-digest/` 与当前运行态的关系

`skills/news-digest/` 是仓库中的独立 skill 源码目录，但当前盘点结果未显示它已安装到运行态。因此它应视为“仓库内自研资产”，而不是“当前正在挂载使用的运行态 skill”。

### 3.2 `skill/` 与当前运行态的关系

当前运行态已安装的 skill 名称是 `codex-dev`，其来源直接指向仓库中的 `skill/`。因此：

- 修改 `skill/` 会影响当前运行态所使用的主 skill 源码
- `skill/` 是当前这套环境里最直接对应运行态的可发布 skill 目录

### 3.3 workspace 源码与运行态映射关系

当前 workspace 配置分成两层：

- 仓库内版本控制层：`.openclaw/workspaces/openclaw-dev-codex/`
- 运行态目录层：`/home/fzhlian/.openclaw/workspace-openclaw-dev-codex/`

其中：

- `BOOTSTRAP.md`
- `HEARTBEAT.md`
- `IDENTITY.md`
- `TOOLS.md`
- `USER.md`

这几项已由运行态目录映射回仓库内源码文件。

而下列文件当前仍表现为运行态侧单独存在：

- `AGENTS.md`
- `SOUL.md`

这意味着当前 workspace 配置还不是“全部由仓库源码统一收敛管理”，仍存在部分运行态本地文件。

## 4. 简短结论

当前可明确识别的用户自研资产如下：

- 仓库内自研 skill：1 个
  - `skills/news-digest/`
- 当前主可发布 skill：1 个
  - `skill/`（运行态安装名：`codex-dev`）
- 运行态 agent：1 个
  - `openclaw-dev-codex`
- workspace：1 套
  - `openclaw-dev-codex`

补充判断：

- 当前“正在运行/挂载”的主 skill 是 `skill/` -> `codex-dev`
- `skills/news-digest/` 目前更像仓库中的独立研发资产，而非当前运行态安装对象
- workspace 配置已部分纳入仓库版本控制，但 `AGENTS.md`、`SOUL.md` 仍未完全并入仓库内 workspace 源码目录
