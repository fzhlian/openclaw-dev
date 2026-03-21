from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_config
from app.scheduler import build_openclaw_cron_args, install_openclaw_cron


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or install the OpenClaw cron job for article-digest.")
    parser.add_argument("--env-file", help="Optional .env path")
    parser.add_argument("--apply", action="store_true", help="Actually call openclaw cron add.")
    args = parser.parse_args()
    config = load_config(args.env_file)
    if args.apply:
        result = install_openclaw_cron(
            config.root_dir,
            cron_expr=config.digest_schedule,
            tz_name=config.digest_tz,
            env_file=args.env_file or ".env",
            agent_id=config.openclaw_agent,
        )
    else:
        result = {
            "command": build_openclaw_cron_args(
                config.root_dir,
                cron_expr=config.digest_schedule,
                tz_name=config.digest_tz,
                env_file=args.env_file or ".env",
                agent_id=config.openclaw_agent,
            )
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
