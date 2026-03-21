from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_config
from app.db import connect_db, init_db


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset failed article records back to queued.")
    parser.add_argument("--env-file", help="Optional .env path")
    parser.add_argument(
        "--statuses",
        nargs="*",
        default=["send_failed", "analysis_failed", "extract_failed"],
        help="Statuses to reset back to queued.",
    )
    args = parser.parse_args()
    config = load_config(args.env_file)
    conn = connect_db(config.db_path)
    init_db(conn)
    placeholders = ",".join("?" for _ in args.statuses)
    sql = f"UPDATE articles SET status = 'queued', error_message = NULL WHERE status IN ({placeholders})"
    cursor = conn.execute(sql, args.statuses)
    conn.commit()
    print(json.dumps({"reset_count": cursor.rowcount, "statuses": args.statuses}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
