# OpenClaw Dev Conventions

这份约定用于规范你在总工作区里开发不同 skill 和 agent 的方式。

## 1. 项目层级

推荐把“可长期维护的 skill”做成独立项目，放在：

```text
/home/fzhlian/Code/<skill-name>
```

例如：

- `/home/fzhlian/Code/codex-dev`

每个独立 skill 项目建议至少包含：

- `README.md`
- `skill/`
- `bin/`
- `docs/`

## 2. skill 运行态与源码的关系

推荐保持这条关系：

- 项目源码在 `/home/fzhlian/Code/<skill-name>`
- OpenClaw 运行态入口在 `~/.openclaw/skills/<skill-name>`
- 发布入口在 `~/.openclaw/publish/<skill-name>`

如果可能，运行态入口和发布入口都应指向项目里的 `skill/`，避免多份源码漂移。

## 3. agent 目录职责

`~/.openclaw/agents/` 主要放运行态 agent 资产，不建议把它当成源码项目来维护。

这里适合放：

- agent 的认证缓存
- agent 的 provider / model 配置
- 会话状态

这里不适合放：

- 长期维护的 skill 源码
- 需要版本管理的独立项目文档

## 4. wrapper workspace 的定位

像 `~/.openclaw/workspace-*` 这种目录，只是 agent 的包装工作区。

使用原则：

- 只处理代理上下文和运行痕迹
- 不把它当成业务仓库
- 不把它当成 skill 的主源码目录

## 5. bin 入口约定

`~/bin` 只保留稳定入口，不作为源码主目录。

推荐：

- `~/bin/<command>` 指向某个独立项目里的脚本
- 入口名稳定，内部实现可以迁移

例如：

- `~/bin/codex-dev` -> `/home/fzhlian/Code/codex-dev/bin/codex-dev`

## 6. 如何区分“开发 skill”与“开发 agent”

开发 skill 时，优先改：

- `/home/fzhlian/Code/<skill-name>/skill/`
- `/home/fzhlian/Code/<skill-name>/bin/`
- `/home/fzhlian/Code/<skill-name>/docs/`

开发 agent 时，优先改：

- `~/.openclaw/agents/<agent-id>/`
- `~/.openclaw/openclaw.json`
- `~/.openclaw/exec-approvals.json`
- 必要时查看 `~/.openclaw/workspace-*`

简化判断：

- 改“能力包/脚本/发布包” = skill
- 改“路由/认证/模型/会话/绑定” = agent

## 7. 命名建议

skill 名：

- 使用小写加连字符
- 例如：`codex-dev`

agent 名：

- 用用途或目标仓库命名
- 例如：`datahz-codex`

workspace 名：

- 与 agent 对应
- 例如：`workspace-datahz-codex`

## 8. 新增 skill 的推荐流程

1. 新建 `/home/fzhlian/Code/<skill-name>`
2. 建立 `skill/`、`bin/`、`docs/`
3. 在 `skill/` 中放 `SKILL.md`、`agents/openai.yaml`、脚本和 references
4. 把 `~/.openclaw/skills/<skill-name>` 指向 `skill/`
5. 把 `~/.openclaw/publish/<skill-name>` 指向 `skill/`
6. 在 `~/bin` 建立稳定入口
7. 必要时为某个 agent 增加调用规则

## 9. 总工作区里的阅读顺序

当你在总工作区里排查问题时，建议按这个顺序看：

1. `codex-dev Project`
2. `OpenClaw Skills`
3. `OpenClaw Agents`
4. `OpenClaw Bin`
5. `OpenClaw Wrapper Workspace`
6. `OpenClaw Root`

原因：

- 先看源码
- 再看运行态加载
- 再看 agent 配置
- 最后看包装层和全局状态
