# BOOTSTRAP.md - openclaw-dev

每次新会话先做这几件事：

1. 确认真实仓库是 `/home/fzhlian/Code/codex-dev`
2. 先读 `AGENTS.md`
3. 再按需读：
   - `README.md`
   - `docs/conventions.md`
   - `skill/SKILL.md`
   - `skill/references/local-setup.md`
4. 先看 git 状态和相关文件，再决定是否修改
5. 需要修改时，优先做小而清晰、可验证的改动
6. 先确认根因、影响面和现有实现模式，再决定改动范围
7. 修改后优先做最小验证，并明确哪些部分已验证、哪些部分未验证
8. 若用户已经明确要求继续开发，且目标范围清晰，则直接实施；不要在给出最小方案后再次停下等确认
9. 若用户提到“刚才的方案”，先看当前线程可见上下文；若确实缺失，则简短请求用户重贴，不要主动翻 `~/.openclaw` 会话日志
10. 若用户要继续某个 skill，先用单一 helper 看 skill 现状；优先 `codex-dev-skill-inspect <skill-path>`，避免巨型只读命令链
11. 若 `codex-dev-skill-inspect` 已能回答问题，不要再追加 `git diff`、`find`、`rg` 等补充只读命令
12. 若用户原话接近“继续完善今天的 news-digest 技能；先检查当前仓库状态和 skills/news-digest 现状，再给出最小实现方案”，则直接运行 `codex-dev-skill-inspect skills/news-digest`
13. 对上面这个范例，不要自行展开成 `git status + git diff + find + rg` 的组合命令
