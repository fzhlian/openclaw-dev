# codex-dev

`codex-dev` 现已从 `DataHz` 工作区拆出，作为独立项目维护。

## 项目目标

- 以后台作业方式分发 Codex 任务
- 立即返回作业回执
- 保存日志、摘要和补丁产物
- 支持 Telegram 完成通知
- 支持显式工作目录 `--workdir`

## 目录结构

- `skill/`
  OpenClaw / ClawHub 可发布 skill 包
- `bin/`
  本地便捷命令包装
- `docs/`
  本地迁移与使用说明

推荐先阅读：

- [docs/migration.md](/home/fzhlian/Code/codex-dev/docs/migration.md)
- [docs/conventions.md](/home/fzhlian/Code/codex-dev/docs/conventions.md)

## 当前安装映射

以下本地入口应指向本项目：

- `~/.openclaw/skills/codex-dev`
- `~/.openclaw/publish/codex-dev`
- `~/bin/codex-dev`
- `~/bin/codex-help`
- `~/bin/codex-dev-status`
- `~/bin/codex-dev-show`
- `~/bin/codex-dev-dispatch`
- `~/bin/codex-dev-worker`

## 常用命令

```bash
/home/fzhlian/Code/codex-dev/bin/codex-help
/home/fzhlian/Code/codex-dev/bin/codex-dev "修复一个小问题并总结修改"
/home/fzhlian/Code/codex-dev/bin/codex-dev-status <job-id>
/home/fzhlian/Code/codex-dev/bin/codex-dev-show <job-id>
```

## 发布

发布源目录：

```bash
/home/fzhlian/Code/codex-dev/skill
```

例如：

```bash
clawhub publish /home/fzhlian/Code/codex-dev/skill --slug codex-dev --version 0.1.1
```
