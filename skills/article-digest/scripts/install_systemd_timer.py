from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_config
from app.scheduler import build_systemd_service_unit, build_systemd_timer_unit, install_systemd_timer


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or install a user-level systemd timer for article-digest.")
    parser.add_argument("--env-file", help="Optional .env path")
    parser.add_argument("--apply", action="store_true", help="Actually write unit files and enable the timer.")
    args = parser.parse_args()
    config = load_config(args.env_file)
    if args.apply:
        result = install_systemd_timer(
            config.root_dir,
            cron_expr=config.digest_schedule,
            env_file=args.env_file or ".env",
        )
    else:
        user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
        result = {
            "service_path": str(user_systemd_dir / "article-digest.service"),
            "timer_path": str(user_systemd_dir / "article-digest.timer"),
            "service": build_systemd_service_unit(config.root_dir, env_file=args.env_file or ".env"),
            "timer": build_systemd_timer_unit(cron_expr=config.digest_schedule),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
