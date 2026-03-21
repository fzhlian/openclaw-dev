# WSL Brain Shell Runbook | WSL 主脑接壳机运行手册

This runbook documents the safe way to turn a WSL-hosted OpenClaw instance into the
"brain" while using another machine as the remote shell/node host.

这份运行手册记录了一个安全做法：当 OpenClaw 主脑跑在 WSL 里时，如何把另一台机器接成远程壳机 / node host。

## Why This Exists | 为什么需要这份文档

When OpenClaw runs inside WSL2, the Linux guest is not the same thing as the Windows host.
Remote connectivity, SSH exposure, Tailscale, and port forwarding all need to account for
that split.

当 OpenClaw 跑在 WSL2 里时，Linux 客体和 Windows 宿主机不是一回事。
远程连通性、SSH 暴露、Tailscale、端口转发都必须把这层拆分考虑进去。

## Current Findings On This Machine | 这台机器当前的结论

As checked on March 18, 2026 after enabling WSL-side Tailscale:

截至 2026 年 3 月 18 日，并完成 WSL 内 Tailscale 接入后，当前环境结论如下：

- OpenClaw Gateway and router are already running in WSL.
- `gateway.bind=loopback`, `gateway.tailscale.mode=serve`, and `gateway.nodes` is still empty.
- The runtime is `Ubuntu 24.04` on `WSL2`, not a bare-metal Linux host.
- Tailscale is installed and authenticated inside WSL, and the brain has a MagicDNS name.
- The Windows host still has no Windows `sshd`, no Windows `tailscale`, and no Windows `portproxy`, but that is no longer blocking because the supported path is now WSL Tailscale Serve.
- Therefore the system is already a good local "brain", and the remaining work is to pair a remote node host.

- OpenClaw Gateway 和 router 已经在 WSL 内运行。
- 当前 `gateway.bind=loopback`、`gateway.tailscale.mode=serve`，并且 `gateway.nodes` 还是空的。
- 运行时是 `WSL2` 里的 `Ubuntu 24.04`，不是裸 Linux 主机。
- WSL 内的 Tailscale 已安装并完成认证，主脑已经有 MagicDNS 名称。
- Windows 宿主机虽然仍然没有 Windows `sshd`、Windows `tailscale`、`portproxy`，但这已经不再构成阻塞，因为当前走的是 WSL Tailscale Serve 方案。
- 所以它已经是一个合格的本地主脑，剩余工作主要是把远端 node host 配对进来。

Use the helper script to re-check the exact live state:

用下面这个脚本可以随时重查当前实时状态：

```bash
./bin/codex-dev-brain-shell-inspect
```

## Recommended Route Order | 建议的路径顺序

### 1. Preferred For This Setup: Tailscale Inside WSL | 当前最推荐：把 Tailscale 装进 WSL

This is the least moving-parts option for the current architecture because OpenClaw itself is
already running inside WSL.

这条路对当前架构来说改动最少，因为 OpenClaw 本身就已经跑在 WSL 里。

Official Tailscale docs call WSL installation an advanced setup, but they document it directly:

Tailscale 官方把 WSL 安装归类为高级用法，但确实提供了官方步骤：

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Because `tailscaled` runs as `root` on Linux, OpenClaw's user-level systemd service
cannot manage `tailscale serve` unless you grant the current user operator access once:

由于 Linux 上的 `tailscaled` 默认由 `root` 运行，而 OpenClaw gateway 是用户级
systemd 服务，所以如果你希望它自动管理 `tailscale serve`，还需要一次性把当前
用户设为 operator：

```bash
sudo tailscale set --operator="$USER"
```

After Tailscale is authenticated in WSL:

当 WSL 内的 Tailscale 认证完成后：

```bash
openclaw config set gateway.bind loopback
openclaw config set gateway.tailscale.mode serve
openclaw config set gateway.auth.allowTailscale false
systemctl --user restart openclaw-gateway.service
```

If Tailscale replies with a message like `Serve is not enabled on your tailnet`,
open the URL it prints once and enable Serve for that node/tailnet first. Then
restart the OpenClaw gateway or rerun `tailscale serve --bg --yes 18789`.

如果 Tailscale 返回类似 `Serve is not enabled on your tailnet`，先打开它打印出来
的 URL，在 tailnet 侧为该节点/网络启用 Serve。启用后再重启 OpenClaw gateway，
或者手动重跑一次 `tailscale serve --bg --yes 18789`。

Then connect the office desktop as a node host:

然后把单位台式机作为 node host 接上：

```bash
export OPENCLAW_GATEWAY_TOKEN="<gateway-token-from-the-brain>"
openclaw node install --host <brain-magicdns> --port 443 --tls --display-name office-shell
openclaw node restart
```

Example:

例如：

```bash
export OPENCLAW_GATEWAY_TOKEN="<gateway-token-from-the-brain>"
openclaw node install --host wrf.tailb58e31.ts.net --port 443 --tls --display-name office-shell
openclaw node restart
```

If `gateway.auth.allowTailscale` is `false`, the node host must still present the
gateway token even though the traffic goes through Tailscale Serve.

如果 `gateway.auth.allowTailscale` 为 `false`，那么即使流量走的是 Tailscale Serve，
node host 仍然必须携带 gateway token。

Approve the first pairing request on the brain:

回到主脑上批准首次配对：

```bash
openclaw devices list
openclaw devices approve <requestId>
openclaw nodes status
```

Finally bind the Telegram-facing agent to the remote exec host:

最后再把 Telegram 面向的 agent 绑到远程 exec 主机：

```bash
openclaw config set agents.list[1].tools.exec.host node
openclaw config set agents.list[1].tools.exec.security allowlist
openclaw config set agents.list[1].tools.exec.ask on-miss
openclaw config set agents.list[1].tools.exec.node office-shell
```

### 2. Alternative: Windows-Host Tailscale Or SSH + Portproxy | 备选：Windows 宿主机 Tailscale 或 SSH + portproxy

This path is possible, but it is more complex for a WSL-hosted gateway because the Windows host
must become the ingress layer and forward traffic into WSL.

这条路不是不行，但对 WSL 内 Gateway 来说更复杂，因为 Windows 宿主机必须承担入口层，再把流量转发进 WSL。

You will need all of the following:

你至少需要同时处理下面几件事：

- Windows `tailscale` or Windows `sshd`
- Windows firewall rules
- Windows `netsh interface portproxy`
- A non-loopback OpenClaw bind inside WSL, because Windows cannot forward into the WSL guest if the gateway only listens on `127.0.0.1`

- Windows `tailscale` 或 Windows `sshd`
- Windows 防火墙放行
- Windows `netsh interface portproxy`
- WSL 内的 OpenClaw 不能继续只绑 `127.0.0.1`，因为 Windows 无法把流量转发给只监听 guest loopback 的 Gateway

For the current machine, this path is strictly more work than installing Tailscale inside WSL.

对当前这台机子，这条路径的工作量明显高于“直接把 Tailscale 装进 WSL”。

## Important Constraints | 重要约束

- `node host` moves `exec` and host-side tools, not the agent workspace itself.
- If you want to edit a repository that physically exists on the office desktop, you still need a shared filesystem, a mounted path, or a separate agent/workspace there.
- Exec approvals are enforced on the node host itself via `~/.openclaw/exec-approvals.json`.
- For `host=node`, `env.PATH` overrides are ignored; install toolchains on the node host or set them in its service environment.
- On this WSL setup, the brain should test its own gateway through local loopback (`ws://127.0.0.1:18789`), not by calling its own tailnet URL from the same machine.
- The stock `openclaw nodes run ... --url https://<brain-magicdns>` path is flaky here; use the local wrapper in this repository for reliable shell verification.

- `node host` 搬走的是 `exec` 和宿主机工具，不是代理工作区本身。
- 如果你想直接编辑单位台式机物理存在的仓库，仍然需要共享文件系统、挂载目录，或者干脆在那台机上单独跑 agent/workspace。
- `exec` 审批是 node host 本机执行的，落在它自己的 `~/.openclaw/exec-approvals.json`。
- 当 `host=node` 时，`env.PATH` 覆写不会帮你补远端环境；需要在 node host 自己安装好工具链，或写进它的 service 环境。
- 在这套 WSL 环境里，主脑测试自己 Gateway 时应优先走本地 loopback（`ws://127.0.0.1:18789`），不要在同一台机器上用自己的 tailnet URL 自回环。
- 当前默认的 `openclaw nodes run ... --url https://<brain-magicdns>` 在这里不稳定；稳定验壳机请用仓库里新增的本地包装脚本。

## Stable Brain-Side Shell Tests | 主脑侧稳定壳机测试

This repository now ships a wrapper command for reliable office-shell checks:

仓库里现在提供了一个稳定的办公室壳机测试包装命令：

```bash
./bin/openclaw-office-shell status
./bin/openclaw-office-shell quick
./bin/openclaw-office-shell doctor
./bin/openclaw-office-shell doctor-json
./bin/openclaw-office-shell describe
./bin/openclaw-office-shell caps
./bin/openclaw-office-shell path
./bin/openclaw-office-shell approvals
./bin/openclaw-office-shell approvals-json
./bin/openclaw-office-shell policy /usr/bin/git --version
./bin/openclaw-office-shell policy-json /usr/bin/git --version
./bin/openclaw-office-shell toolchain
./bin/openclaw-office-shell toolchain-json
./bin/openclaw-office-shell which git python3
./bin/openclaw-office-shell hostname
./bin/openclaw-office-shell git-version
./bin/openclaw-office-shell uname
./bin/openclaw-office-shell proof
./bin/openclaw-office-shell proof-hostname
```

What the wrapper does:

这个包装命令做了两件事：

- Uses a minimal CLI config at `~/.openclaw/openclaw-cli-min.json`
- Forces the brain to talk to its own gateway through `ws://127.0.0.1:18789`
- Retries transient local loopback failures a few times before surfacing an error

- 用 `~/.openclaw/openclaw-cli-min.json` 这个极简 CLI 配置
- 强制主脑通过 `ws://127.0.0.1:18789` 访问自己的 Gateway
- 遇到本地 loopback 的瞬时失败时，会先自动重试几次再报错

That avoids the flaky self-loop path where the brain tries to reach itself through
`wss://<brain-magicdns>` or through the heavier default CLI startup path.

这样可以避开主脑通过 `wss://<brain-magicdns>` 自己绕自己，以及默认 CLI 启动路径过重导致的不稳定问题。

It also absorbs a class of transient local CLI failures such as `handshake timeout`,
`gateway closed`, `closed before connect`, and short-lived `unknown node` responses
seen on this machine's loopback path.

它还会吸收一类这台机器上常见的本地 CLI 瞬时故障，比如 `handshake timeout`、
`gateway closed`、`closed before connect`，以及短暂出现的 `unknown node`。

Also note a current CLI quirk:

还要注意一个当前 CLI 的行为问题：

- `openclaw nodes invoke` works reliably on this machine when forced to local loopback.
- `openclaw nodes run` may still hang even though the underlying `node.invoke` succeeds.
- Local tracing showed `nodes run` issuing an extra `exec.approval.request` wait path before `system.run`, which is enough to make routine shell checks feel broken.

- 在这台机器上，强制走本地 loopback 时，`openclaw nodes invoke` 是稳定的。
- 但 `openclaw nodes run` 即使底层 `node.invoke` 已经成功，也仍可能卡住。
- 本地跟踪显示，`nodes run` 在 `system.run` 之前还会多走一层 `exec.approval.request` 等待路径，足以让日常壳机测试看起来像坏了一样。

For day-to-day checks, prefer the built-in shortcuts:

日常检查优先用内置快捷子命令：

```bash
./bin/openclaw-office-shell quick
./bin/openclaw-office-shell doctor
./bin/openclaw-office-shell doctor-json
./bin/openclaw-office-shell caps
./bin/openclaw-office-shell path
./bin/openclaw-office-shell approvals
./bin/openclaw-office-shell policy /usr/bin/git --version
./bin/openclaw-office-shell toolchain
./bin/openclaw-office-shell hostname
./bin/openclaw-office-shell git-version
./bin/openclaw-office-shell uname
./bin/openclaw-office-shell proof-hostname
```

`quick` is the fastest liveness probe. It only checks node connectivity, hostname,
and the proof-hostname marker.

`quick` 是最快的存活探针。它只检查节点在线状态、主机名和 proof-hostname 标记。

`doctor` is the fastest fuller health check. It verifies:

`doctor` 是最快的完整健康检查命令。它会同时验证：

- Node presence and connectivity
- Pairing state
- Remote hostname
- Proof files on the office shell
- `git --version`
- `uname -a`

- 节点是否存在且在线
- 配对状态
- 远端主机名
- 办公室壳机上的 proof 文件
- `git --version`
- `uname -a`

Example:

示例：

```bash
./bin/openclaw-office-shell quick
./bin/openclaw-office-shell doctor
```

For script-friendly output, use:

如果你要给脚本消费，用下面这些：

```bash
./bin/openclaw-office-shell doctor-json
./bin/openclaw-office-shell caps
./bin/openclaw-office-shell path
```

- `doctor-json` returns the same health snapshot as `doctor`, but as a JSON object.
- `caps` returns node capabilities and advertised commands.
- `path` prints the remote node's claimed `PATH` environment.
- `approvals` shows the current exec-approval allowlist snapshot stored on the office shell.
- `approvals-json` returns the same approval snapshot as JSON.
- `policy` combines allowlist state and `system.run.prepare` into a single preflight result.
- `policy-json` returns the same preflight result as JSON.
- `toolchain` checks whether common developer binaries are visible on the office shell's PATH.
- `toolchain-json` returns the same tool visibility snapshot as JSON.
- `OPENCLAW_OFFICE_SHELL_TIMEOUT_SECONDS` overrides the per-call timeout.
- `OPENCLAW_OFFICE_SHELL_RETRIES` overrides the retry count for transient loopback failures.
- `OPENCLAW_OFFICE_SHELL_RETRY_DELAY_SECONDS` overrides the delay between retries.

- `doctor-json` 返回和 `doctor` 同一份健康快照，但格式是 JSON。
- `caps` 返回节点能力和它声明支持的命令。
- `path` 打印远端节点声明的 `PATH` 环境。
- `approvals` 显示办公室壳机当前保存的 exec 审批 allowlist 快照。
- `approvals-json` 以 JSON 返回同一份审批快照。
- `policy` 把 allowlist 状态和 `system.run.prepare` 结果合并成一条执行前预判。
- `policy-json` 以 JSON 返回同一份执行前预判结果。
- `toolchain` 检查常用开发工具是否在办公室壳机的 PATH 里可见。
- `toolchain-json` 以 JSON 返回同一份工具可见性快照。
- `OPENCLAW_OFFICE_SHELL_TIMEOUT_SECONDS` 可覆盖单次调用超时。
- `OPENCLAW_OFFICE_SHELL_RETRIES` 可覆盖本地 loopback 瞬时故障的重试次数。
- `OPENCLAW_OFFICE_SHELL_RETRY_DELAY_SECONDS` 可覆盖每次重试之间的等待时间。

Examples:

示例：

```bash
./bin/openclaw-office-shell approvals
./bin/openclaw-office-shell approvals-json
./bin/openclaw-office-shell policy /usr/bin/git --version
./bin/openclaw-office-shell policy /usr/bin/python3 --version
./bin/openclaw-office-shell policy /usr/bin/echo hello
./bin/openclaw-office-shell toolchain
./bin/openclaw-office-shell toolchain-json
./bin/openclaw-office-shell toolchain git python3 node npm pnpm bun go cargo
```

`toolchain` is intentionally a PATH-level check. It tells you whether the binary is
discoverable on the office shell, not whether every interpreter/runtime command is
approval-free. On this setup, `python3 --version` and `node --version` can still be
gated by stricter exec policy even when `toolchain` reports the binary path.

`toolchain` 故意只做 PATH 层面的检查。它回答的是“这个二进制在办公室壳机上能不能找到”，
不是“所有解释器 / 运行时命令都已经免审批可执行”。在这套环境里，即使 `toolchain`
报告找到了 `python3` 或 `node`，`python3 --version`、`node --version`
这类命令仍可能被更严格的执行策略拦住。

`prepare` is useful when you want the policy engine to validate a command before
execution. It now correctly surfaces binding/policy errors instead of failing
silently. For example, some interpreter/runtime commands can return:

`prepare` 适合在真正执行前先让策略引擎验证一次命令。现在它已经会正确返回绑定 /
策略错误，不再静默失败。比如某些解释器 / 运行时命令可能会返回：

```text
INVALID_REQUEST: SYSTEM_RUN_DENIED: approval cannot safely bind this interpreter/runtime command
```

Example:

示例：

```bash
./bin/openclaw-office-shell prepare /usr/bin/git --version
./bin/openclaw-office-shell prepare /usr/bin/python3 --version
```

`policy` goes one step further than `prepare`:

`policy` 比 `prepare` 更进一步：

- `ready`: prepare passed and the argv0 already matches an allowlist entry.
- `review`: prepare passed, but argv0 is not currently allowlisted, so approval may still be needed.
- `denied`: prepare itself was rejected by policy/runtime binding rules.

- `ready`：prepare 已通过，而且 argv0 已命中 allowlist。
- `review`：prepare 已通过，但 argv0 当前不在 allowlist 中，后续仍可能走审批。
- `denied`：prepare 本身就被策略 / 运行时绑定规则拒绝了。

At the moment, the node advertises `browser.proxy`, but browser-proxy requests are
not stable enough on this machine's local loopback path to be part of the default
verification flow yet.

目前这个节点虽然声明支持 `browser.proxy`，但在这台机器的本地 loopback 路径上，
浏览器代理请求还不够稳定，所以暂时不纳入默认验收流程。

Use absolute paths with `run` or `exec` when possible:

`run` 或 `exec` 最好直接传绝对路径：

```bash
./bin/openclaw-office-shell run /usr/bin/hostname
./bin/openclaw-office-shell run /usr/bin/git --version
./bin/openclaw-office-shell exec /usr/bin/hostname
./bin/openclaw-office-shell exec /usr/bin/git --version
```

If you need to inspect files under the office shell's home directory, avoid `~`
and pass the absolute path:

如果你要读取办公室壳机家目录下的文件，不要写 `~`，直接传绝对路径：

```bash
./bin/openclaw-office-shell read /home/fzhlian/.openclaw/office-shell-hostname.txt
```

## Suggested Sequence For This Machine | 这台机器的建议顺序

1. Run `./bin/codex-dev-brain-shell-inspect`.
2. Install `tailscale` inside WSL.
3. Authenticate `tailscale up`.
4. Switch OpenClaw to `gateway.bind=loopback` + `gateway.tailscale.mode=serve`.
5. Pair the office desktop as `office-shell`.
6. Bind `openclaw-dev-codex` exec to that node.

1. 先运行 `./bin/codex-dev-brain-shell-inspect`。
2. 在 WSL 内安装 `tailscale`。
3. 完成 `tailscale up` 认证。
4. 把 OpenClaw 切到 `gateway.bind=loopback` + `gateway.tailscale.mode=serve`。
5. 把单位台式机配对成 `office-shell`。
6. 再把 `openclaw-dev-codex` 的 exec 绑定到这个节点。

## References | 参考

- OpenClaw network model: https://docs.openclaw.ai/gateway/network-model
- OpenClaw nodes: https://docs.openclaw.ai/nodes
- OpenClaw node CLI: https://docs.openclaw.ai/cli/node
- Tailscale Linux install: https://tailscale.com/docs/install/linux
- Tailscale on WSL2: https://tailscale.com/docs/install/windows/wsl2
