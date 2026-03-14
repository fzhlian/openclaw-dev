---
name: codex-dev
description: Run Codex as a background local job with an immediate receipt, saved logs and patch artifacts, optional Telegram notifications, and explicit workdir support.
---

# codex-dev

Use this skill when the user wants asynchronous Codex execution instead of a long-lived interactive session.

当用户希望把 Codex 任务放到后台执行、先拿到作业回执、并在完成后查看摘要或接收 Telegram 通知时，使用这个 skill。

## What it does

- Starts a background Codex job and returns a receipt immediately
- 启动后台 Codex 作业，并立即返回回执
- Stores artifacts under `$HOME/.codex-dev/jobs/<job-id>/`
- 将作业产物保存到 `$HOME/.codex-dev/jobs/<job-id>/`
- Supports `task.txt`, `status.json`, `codex.out.log`, `summary.txt`, and `patch.txt`
- 保存 `task.txt`、`status.json`、`codex.out.log`、`summary.txt`、`patch.txt`
- Can optionally send a completion summary to Telegram
- 可选地在完成后把摘要发送到 Telegram
- Supports an explicit work directory via `--workdir`
- 支持通过 `--workdir` 明确指定工作目录
- Works well for Telegram-triggered development flows and local CLI wrappers
- 适合 Telegram 驱动的开发流程和本地命令行包装

## Files

- Main entrypoint: `scripts/codex-dev-dispatch`
- Worker: `scripts/codex-dev-worker`
- Telegram helper: `scripts/telegram-notify`
- Optional installer: `scripts/install-local.sh`
- Local setup reference: `references/local-setup.md`

## When to use it

Prefer this skill for any request that should:

- modify files asynchronously
- return a job receipt first
- run against a specific working directory
- keep a patch/log trail for later inspection

If the user only wants read-only inspection, a normal direct response is usually enough.

Common examples:

- "Fix one small issue, but give me a receipt first."
- "Run this Codex task in the background and notify me in Telegram when it finishes."
- "Only modify files under this specific directory."
- “修一个小问题，但先给我作业回执。”
- “把这个 Codex 任务放到后台跑，完成后发 Telegram 给我。”
- “只修改这个指定目录下的文件。”

## Invocation

Run the dispatcher script directly from the installed skill folder:

```bash
./scripts/codex-dev-dispatch "Inspect the repo and fix one issue."
```

Or with an explicit work directory:

```bash
./scripts/codex-dev-dispatch --workdir /absolute/path "Fix the issue only in this directory."
```

Query status and summary:

```bash
./scripts/codex-dev-dispatch status <job-id>
./scripts/codex-dev-dispatch show <job-id>
./scripts/codex-dev-dispatch help
```

If installed with local wrappers, the same flow can be exposed as:

```bash
codex-dev "Fix one issue and summarize the change."
codex-help
codex-dev-status <job-id>
codex-dev-show <job-id>
```

常见中文用法：

```bash
codex-dev "修复一个小问题并总结修改"
codex-dev --workdir /absolute/path "只在这个目录里完成修改"
codex-help
```

## Environment

Optional environment variables:

- `CODEX_DEV_DEFAULT_WORKDIR`
- `CODEX_DEV_JOBS_ROOT`
- `CODEX_DEV_CHAT_ID`
- `TELEGRAM_BOT_TOKEN`
- `CODEX_DEV_OPENCLAW_CONFIG`

If `TELEGRAM_BOT_TOKEN` is unset, the worker will try to read `botToken` from `CODEX_DEV_OPENCLAW_CONFIG` and then from `~/.openclaw/openclaw.json`.

## Workdir behavior

- `--workdir` must be an absolute existing path
- Codex executes in that work directory
- If the work directory is inside a git repo, `patch.txt` is generated relative to the detected repo root

## Idempotency

For write requests, prefer idempotent changes. If the requested content already exists, do not append or duplicate it; state that clearly in the summary.

## Notes

- This publishable package contains the skill and helper scripts only
- OpenClaw agent bindings, Telegram bindings, and local workspace wrappers remain local installation details
- Use `references/local-setup.md` when you need to wire the installed skill into a local OpenClaw agent
- The package is intentionally generic: repository path, Telegram chat id, and default workdir are all local configuration
- 这个社区包发布的是 skill 和脚本，不包含你的本地 agent 绑定状态
- 仓库路径、Telegram chat id、默认工作目录等都需要在本地自行配置
