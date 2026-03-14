# Security Hardening | 安全加固记录

This document records the OpenClaw hardening work completed on this machine and the remaining accepted warning state.  
这份文档记录了当前机器上已完成的 OpenClaw 安全加固，以及剩余可接受的告警状态。

## Current Status | 当前状态

- `openclaw security audit --json`
  - `critical: 0`
  - `warn: 1`
  - `info: 1`
- Remaining warning:
  - `gateway.trusted_proxies_missing`
- 当前剩余唯一告警：
  - `gateway.trusted_proxies_missing`

This remaining warning is acceptable in the current setup because the gateway is bound to loopback and is not exposed behind a reverse proxy.  
这个剩余告警在当前环境里可以接受，因为 gateway 仅绑定到 loopback，并未通过反向代理对外暴露。

## Hardening Changes | 已完成的加固项

### 1. Telegram Exposure Reduced | 收紧 Telegram 暴露面

- Changed `channels.telegram.groupPolicy` from `open` to `allowlist`
- 保留 `allowFrom` 为显式允许列表

Result: the previous critical findings for open group exposure were eliminated.  
结果：之前与开放群组暴露相关的 critical 告警已消除。

### 2. Exec Approvals Tightened | 收紧执行审批策略

- Changed approvals defaults from permissive to fail-closed:
  - `security: deny`
  - `ask: on-miss`
  - `askFallback: deny`
- Removed stale historical allowlist entries and old helper scripts
- Kept per-agent allowlists only for currently used commands

Result: Telegram-triggered elevated execution is no longer effectively "always allow".  
结果：Telegram 触发的 elevated 执行不再处于“默认总是放行”的状态。

Additional operator setup:

- Enabled `channels.telegram.execApprovals` for the trusted operator account
- Scoped Telegram approvals to explicit approver IDs and selected agents
- Kept delivery target at `dm` to avoid exposing approval prompts in shared chats

补充的操作者侧配置：

- 已为受信任操作者启用 `channels.telegram.execApprovals`
- 已把 Telegram 审批收敛到显式 approver ID 和指定 agent
- 默认保持 `target=dm`，避免在共享聊天中暴露审批提示

### 3. Secret Tokens Moved Out of Main Config | 将敏感 token 移出主配置

- Moved Telegram bot token and gateway token out of `openclaw.json`
- Added local secret file: `~/.openclaw/.env`
- Replaced plaintext config values with env references:
  - `${OPENCLAW_TELEGRAM_BOT_TOKEN}`
  - `${OPENCLAW_GATEWAY_TOKEN}`

Result: the main runtime config no longer stores these secrets in plaintext.  
结果：主运行配置文件中已不再直接保存这两个明文 secret。

### 4. Removed WhatsApp State | 清理 WhatsApp 状态

- Removed `~/.openclaw/credentials/whatsapp`
- Deleted WhatsApp credential material and runtime state

Result: unused multi-channel credential surface was reduced.  
结果：移除了未使用的多渠道凭证面。

### 5. Tightened Local Permissions | 收紧本地权限

- Set:
  - `~/.codex` to `700`
  - `~/.openclaw/credentials` to `700`
  - `~/.openclaw/.env` to `600`
  - Telegram credential files to `600`
- Removed old config backup files that still contained plaintext secrets

Result: local credential exposure risk is materially lower than before.  
结果：本地凭证暴露风险相比之前已明显下降。

### 6. Reduced Tool Surface | 收紧工具面

- Set global `tools.profile` to `coding`
- Pinned `clawrouter` install spec to an exact version
- Removed ineffective `gateway.nodes.denyCommands` entries instead of keeping misleading pseudo-protection

Result: the plugin reachability warning was removed and the remaining tool policy is closer to an intentional coding-only baseline.  
结果：插件工具可达性告警已消除，当前工具策略更接近“有意收敛的开发基线”。

## Remaining Accepted Warning | 当前接受保留的告警

### `gateway.trusted_proxies_missing`

Why it remains:

- `gateway.bind` is loopback-only
- there is no reverse proxy in front of the Control UI
- there is no current remote proxy trust boundary to configure

保留原因：

- `gateway.bind` 当前仅监听 loopback
- Control UI 当前没有挂在反向代理后
- 当前不存在需要配置 `trustedProxies` 的代理信任边界

When this must be revisited:

- when exposing OpenClaw through Nginx, Caddy, Traefik, or another reverse proxy
- when relying on forwarded headers for local-client checks or auth decisions

以下情况必须重新处理：

- 未来通过 Nginx、Caddy、Traefik 等反向代理暴露 OpenClaw 时
- 未来依赖转发头参与本地客户端识别或鉴权判断时

## Operational Notes | 运行说明

- Git remote sync capability was intentionally preserved.
- Telegram elevated execution is no longer default-permissive, but it is still available within the tightened approvals model.
- `codex-dev-worker` now supports loading Telegram token from `~/.openclaw/.env`.

补充说明：

- 远程 Git 同步能力被有意保留，没有在这轮加固中移除。
- Telegram 的 elevated 执行已不再是默认宽放行，但仍保留在收紧后的 approvals 模型里。
- Telegram 现在可以作为执行审批客户端使用，但默认仍建议只在私聊里审批。
- `codex-dev-worker` 现在支持从 `~/.openclaw/.env` 加载 Telegram token。

## Next Review Triggers | 下次复审触发条件

- introducing a reverse proxy or public ingress
- enabling additional messaging channels
- widening agent tool policies
- adding new elevated commands or new trusted scripts
- switching trust model from single-operator to shared-user access

建议在以下变化发生后重新复审：

- 引入反向代理或公网入口
- 新增消息渠道
- 放宽 agent 工具策略
- 增加新的 elevated 命令或新的受信任脚本
- 从单人操作者模型切换到多人共享访问模型
