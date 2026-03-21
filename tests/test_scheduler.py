from __future__ import annotations

from pathlib import Path

from app.scheduler import build_openclaw_cron_args, build_openclaw_cron_message, resolve_openclaw_agent


def test_workspace_main_defaults_to_main_agent():
    project_root = Path("/tmp/workspace-main")
    args = build_openclaw_cron_args(project_root, cron_expr="0 20 * * *", tz_name="Asia/Taipei")
    assert "--agent" in args
    agent_index = args.index("--agent")
    assert args[agent_index + 1] == "main"
    assert "--no-deliver" in args
    assert "--light-context" in args
    thinking_index = args.index("--thinking")
    assert args[thinking_index + 1] == "minimal"


def test_explicit_agent_override_is_preserved():
    project_root = Path("/tmp/workspace-main")
    args = build_openclaw_cron_args(
        project_root,
        cron_expr="0 20 * * *",
        tz_name="Asia/Taipei",
        agent_id="digest-worker",
    )
    agent_index = args.index("--agent")
    assert args[agent_index + 1] == "digest-worker"


def test_non_main_workspace_has_no_implicit_agent():
    assert resolve_openclaw_agent(Path("/tmp/workspace")) is None


def test_cron_message_forces_command_execution():
    message = build_openclaw_cron_message(Path("/tmp/workspace-main"))
    assert "Execute this exact shell command now" in message
    assert "Do not inspect the workspace first." in message
    assert "python3 /tmp/workspace-main/skills/article-digest/scripts/send_digest.py --env-file /tmp/workspace-main/.env" in message
