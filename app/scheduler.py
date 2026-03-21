from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable


SYSTEMD_UNIT_NAME = "article-digest"


def resolve_openclaw_agent(project_root: Path, agent_id: str | None = None) -> str | None:
    if agent_id:
        return agent_id
    if project_root.name == "workspace-main":
        return "main"
    return None


def build_openclaw_cron_command(project_root: Path, *, env_file: str = ".env") -> str:
    script = project_root / "skills" / "article-digest" / "scripts" / "send_digest.py"
    env_path = Path(env_file)
    if not env_path.is_absolute():
        env_path = project_root / env_path
    return f"python3 {script} --env-file {env_path}"


def resolve_env_path(project_root: Path, env_file: str = ".env") -> Path:
    env_path = Path(env_file)
    if not env_path.is_absolute():
        env_path = project_root / env_path
    return env_path


def build_openclaw_cron_message(project_root: Path, *, env_file: str = ".env") -> str:
    command = build_openclaw_cron_command(project_root, env_file=env_file)
    return (
        "Execute this exact shell command now and do not ask follow-up questions:\n"
        f"{command}\n\n"
        "Rules:\n"
        "- Do not inspect the workspace first.\n"
        "- Do not change the command.\n"
        "- If the command prints JSON, return that output directly.\n"
        "- If the command fails, return the error output and exit code."
    )


def build_openclaw_cron_example(
    project_root: Path,
    *,
    cron_expr: str,
    tz_name: str,
    env_file: str = ".env",
    agent_id: str | None = None,
) -> str:
    agent = resolve_openclaw_agent(project_root, agent_id)
    example = (
        "openclaw cron add "
        '--name "article-digest" '
        f'--cron "{cron_expr}" '
        f'--tz "{tz_name}" '
    )
    if agent:
        example += f'--agent "{agent}" '
    example += (
        '--light-context '
        '--thinking "minimal" '
        '--session isolated '
        f'--message "{build_openclaw_cron_message(project_root, env_file=env_file)}" '
        "--no-deliver"
    )
    return example


def cron_expr_to_daily_on_calendar(cron_expr: str) -> str:
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError("systemd timer fallback 仅支持 5 段 cron 表达式")
    minute, hour, day_of_month, month, day_of_week = parts
    if day_of_month != "*" or month != "*" or day_of_week != "*":
        raise ValueError("systemd timer fallback 当前仅支持每天固定时刻的 cron 表达式")
    if not minute.isdigit() or not hour.isdigit():
        raise ValueError("systemd timer fallback 仅支持数字化的小时与分钟")
    return f"*-*-* {int(hour):02d}:{int(minute):02d}:00"


def build_systemd_service_unit(project_root: Path, *, env_file: str = ".env") -> str:
    script = project_root / "skills" / "article-digest" / "scripts" / "send_digest.py"
    env_path = resolve_env_path(project_root, env_file)
    return "\n".join(
        [
            "[Unit]",
            "Description=article-digest digest sender",
            "",
            "[Service]",
            "Type=oneshot",
            f"WorkingDirectory={project_root}",
            "Environment=PYTHONUNBUFFERED=1",
            f"ExecStart=/usr/bin/python3 {script} --env-file {env_path}",
            "",
        ]
    )


def build_systemd_timer_unit(*, cron_expr: str) -> str:
    on_calendar = cron_expr_to_daily_on_calendar(cron_expr)
    return "\n".join(
        [
            "[Unit]",
            "Description=Run article-digest on schedule",
            "",
            "[Timer]",
            f"OnCalendar={on_calendar}",
            "Persistent=true",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )


def install_systemd_timer(
    project_root: Path,
    *,
    cron_expr: str,
    env_file: str = ".env",
    unit_name: str = SYSTEMD_UNIT_NAME,
    user_systemd_dir: Path | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, object]:
    systemd_dir = user_systemd_dir or (Path.home() / ".config" / "systemd" / "user")
    systemd_dir.mkdir(parents=True, exist_ok=True)
    service_path = systemd_dir / f"{unit_name}.service"
    timer_path = systemd_dir / f"{unit_name}.timer"
    service_text = build_systemd_service_unit(project_root, env_file=env_file)
    timer_text = build_systemd_timer_unit(cron_expr=cron_expr)
    service_path.write_text(service_text, encoding="utf-8")
    timer_path.write_text(timer_text, encoding="utf-8")
    runner(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True, text=True, timeout=30)
    result = runner(
        ["systemctl", "--user", "enable", "--now", timer_path.name],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "service_path": str(service_path),
        "timer_path": str(timer_path),
        "on_calendar": cron_expr_to_daily_on_calendar(cron_expr),
        "stdout": getattr(result, "stdout", ""),
        "stderr": getattr(result, "stderr", ""),
    }


def build_openclaw_cron_args(
    project_root: Path,
    *,
    cron_expr: str,
    tz_name: str,
    env_file: str = ".env",
    agent_id: str | None = None,
) -> list[str]:
    args = [
        "openclaw",
        "cron",
        "add",
        "--name",
        "article-digest",
        "--cron",
        cron_expr,
        "--tz",
        tz_name,
    ]
    agent = resolve_openclaw_agent(project_root, agent_id)
    if agent:
        args += ["--agent", agent]
    args += [
        "--light-context",
        "--thinking",
        "minimal",
        "--session",
        "isolated",
        "--message",
        build_openclaw_cron_message(project_root, env_file=env_file),
        "--no-deliver",
    ]
    return args


def install_openclaw_cron(
    project_root: Path,
    *,
    cron_expr: str,
    tz_name: str,
    env_file: str = ".env",
    agent_id: str | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, object]:
    args = build_openclaw_cron_args(
        project_root,
        cron_expr=cron_expr,
        tz_name=tz_name,
        env_file=env_file,
        agent_id=agent_id,
    )
    result = runner(args, check=True, capture_output=True, text=True, timeout=30)
    return {"command": args, "stdout": getattr(result, "stdout", ""), "stderr": getattr(result, "stderr", "")}
