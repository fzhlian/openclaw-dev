# OpenClaw Dev Conventions | OpenClaw 开发约定

This document defines how to develop different skills and agents in the shared OpenClaw workspace.  
这份约定用于规范你在总工作区里开发不同 skill 和 agent 的方式。

## 1. Project Layout | 项目层级

Long-lived skills should be maintained as independent projects under:  
推荐把可长期维护的 skill 做成独立项目，放在：

```text
/home/fzhlian/Code/<skill-name>
```

For example / 例如：

- `/home/fzhlian/Code/codex-dev`

Each independent skill project should contain at least:  
每个独立 skill 项目建议至少包含：

- `README.md`
- `skill/`
- `bin/`
- `docs/`

## 2. Runtime vs Source | skill 运行态与源码的关系

Recommended mapping:  
推荐保持这条关系：

- Project source lives in `/home/fzhlian/Code/<skill-name>`  
  项目源码在 `/home/fzhlian/Code/<skill-name>`
- OpenClaw runtime entry lives in `~/.openclaw/skills/<skill-name>`  
  OpenClaw 运行态入口在 `~/.openclaw/skills/<skill-name>`
- Publish entry lives in `~/.openclaw/publish/<skill-name>`  
  发布入口在 `~/.openclaw/publish/<skill-name>`

Whenever possible, both runtime and publish entries should point to the project's `skill/` directory to avoid drift.  
如果可能，运行态入口和发布入口都应指向项目里的 `skill/`，避免多份源码漂移。

## 3. Agent Directory Responsibility | agent 目录职责

`~/.openclaw/agents/` is primarily for runtime agent assets and should not be treated as the primary source repository.  
`~/.openclaw/agents/` 主要放运行态 agent 资产，不建议把它当成源码项目来维护。

Good fit / 适合放：

- Agent auth cache / agent 的认证缓存
- Provider and model config / agent 的 provider 与 model 配置
- Session state / 会话状态

Not a good fit / 不适合放：

- Long-term skill source / 长期维护的 skill 源码
- Versioned project docs / 需要版本管理的独立项目文档

## 4. Wrapper Workspace Role | wrapper workspace 的定位

Directories like `~/.openclaw/workspace-*` are wrapper workspaces for agents.  
像 `~/.openclaw/workspace-*` 这种目录，只是 agent 的包装工作区。

Use them to / 使用原则：

- Handle agent context and runtime traces only  
  只处理代理上下文和运行痕迹
- Avoid treating them as business repositories  
  不把它当成业务仓库
- Avoid treating them as the main skill source  
  不把它当成 skill 的主源码目录

## 5. Bin Entrypoints | bin 入口约定

`~/bin` should only keep stable entrypoints, not primary source files.  
`~/bin` 只保留稳定入口，不作为源码主目录。

Recommended pattern / 推荐：

- `~/bin/<command>` points to scripts inside an independent project  
  `~/bin/<command>` 指向某个独立项目里的脚本
- Command names stay stable while implementation can move  
  入口名稳定，内部实现可以迁移

Example / 例如：

- `~/bin/codex-dev` -> `/home/fzhlian/Code/codex-dev/bin/codex-dev`

## 6. Skill vs Agent Changes | 如何区分开发 skill 与 agent

When changing a skill, prefer editing:  
开发 skill 时，优先改：

- `/home/fzhlian/Code/<skill-name>/skill/`
- `/home/fzhlian/Code/<skill-name>/bin/`
- `/home/fzhlian/Code/<skill-name>/docs/`

When changing an agent, prefer editing:  
开发 agent 时，优先改：

- `~/.openclaw/agents/<agent-id>/`
- `~/.openclaw/openclaw.json`
- `~/.openclaw/exec-approvals.json`
- `~/.openclaw/workspace-*` when needed  
  必要时查看 `~/.openclaw/workspace-*`

Quick rule / 简化判断：

- Capability package, scripts, publish package = skill  
  改能力包、脚本、发布包 = skill
- Routing, auth, model, session, binding = agent  
  改路由、认证、模型、会话、绑定 = agent

## 7. Naming | 命名建议

Skill names / skill 名：

- Use lowercase plus hyphens  
  使用小写加连字符
- Example: `codex-dev`  
  例如：`codex-dev`

Agent names / agent 名：

- Name them by purpose or target repo  
  用用途或目标仓库命名
- Example: `datahz-codex`  
  例如：`datahz-codex`

Workspace names / workspace 名：

- Match the related agent  
  与 agent 对应
- Example: `workspace-datahz-codex`  
  例如：`workspace-datahz-codex`

## 8. New Skill Workflow | 新增 skill 的推荐流程

1. Create `/home/fzhlian/Code/<skill-name>`  
   新建 `/home/fzhlian/Code/<skill-name>`
2. Add `skill/`, `bin/`, and `docs/`  
   建立 `skill/`、`bin/`、`docs/`
3. Put `SKILL.md`, `agents/openai.yaml`, scripts, and references under `skill/`  
   在 `skill/` 中放 `SKILL.md`、`agents/openai.yaml`、脚本和 references
4. Point `~/.openclaw/skills/<skill-name>` to `skill/`  
   把 `~/.openclaw/skills/<skill-name>` 指向 `skill/`
5. Point `~/.openclaw/publish/<skill-name>` to `skill/`  
   把 `~/.openclaw/publish/<skill-name>` 指向 `skill/`
6. Add stable wrappers under `~/bin`  
   在 `~/bin` 建立稳定入口
7. Add agent-side invocation rules if needed  
   必要时为某个 agent 增加调用规则

## 9. Reading Order in the Meta Workspace | 总工作区里的阅读顺序

When debugging in the meta workspace, read in this order:  
当你在总工作区里排查问题时，建议按这个顺序看：

1. `codex-dev Project`
2. `OpenClaw Skills`
3. `OpenClaw Agents`
4. `OpenClaw Bin`
5. `OpenClaw Wrapper Workspace`
6. `OpenClaw Root`

Why / 原因：

- Source code first / 先看源码
- Then runtime-loaded skill contents / 再看运行态加载
- Then agent config / 再看 agent 配置
- Finally wrapper and global state / 最后看包装层和全局状态
