from __future__ import annotations

import pytest
from pathlib import Path

from app.scheduler import build_systemd_service_unit, build_systemd_timer_unit, cron_expr_to_daily_on_calendar


def test_systemd_units_are_rendered_for_daily_schedule():
    project_root = Path("/tmp/workspace-main")
    service = build_systemd_service_unit(project_root)
    timer = build_systemd_timer_unit(cron_expr="0 20 * * *")
    assert "WorkingDirectory=/tmp/workspace-main" in service
    assert "ExecStart=/usr/bin/python3 /tmp/workspace-main/skills/article-digest/scripts/send_digest.py --env-file /tmp/workspace-main/.env" in service
    assert "OnCalendar=*-*-* 20:00:00" in timer
    assert "Persistent=true" in timer


def test_systemd_timer_rejects_non_daily_cron():
    with pytest.raises(ValueError):
        cron_expr_to_daily_on_calendar("*/15 * * * *")
