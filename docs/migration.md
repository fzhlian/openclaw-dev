# Migration Notes | 迁移说明

`codex-dev` was separated from the `DataHz` workspace and moved into its own project root:  
`codex-dev` 已从 `DataHz` 工作区拆出，并迁移到独立项目根目录：

```text
/home/fzhlian/Code/codex-dev
```

Runtime compatibility is preserved by repointing OpenClaw and shell entrypoints to this project.  
为了保持运行兼容性，OpenClaw 入口和 shell 命令入口都已重定向到这个项目。

The publishable skill remains under:  
可发布的 skill 目录保留在：

```text
/home/fzhlian/Code/codex-dev/skill
```
