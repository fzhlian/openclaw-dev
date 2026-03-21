from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_config
from app.db import connect_db, get_settings, init_db, set_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize article-digest SQLite schema and seed runtime settings.")
    parser.add_argument("--env-file", help="Optional .env path")
    args = parser.parse_args()
    config = load_config(args.env_file)
    conn = connect_db(config.db_path)
    init_db(conn)
    set_settings(
        conn,
        {
            "digest_schedule": config.digest_schedule,
            "digest_tz": config.digest_tz,
            "send_mode": config.send_mode,
            "max_digest_items": str(config.max_digest_items),
            "max_message_chars": str(config.max_message_chars),
            **({"telegram_chat_id": config.telegram_chat_id} if config.telegram_chat_id else {}),
            **({"telegram_thread_id": config.telegram_thread_id} if config.telegram_thread_id else {}),
            **({"openclaw_agent": config.openclaw_agent} if config.openclaw_agent else {}),
            **({"openclaw_target": config.openclaw_target} if config.openclaw_target else {}),
        },
    )
    print(json.dumps({"db_path": str(config.db_path), "settings": get_settings(conn)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
