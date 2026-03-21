from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_config
from app.db import connect_db, init_db, mark_article_status
from app.pipeline import ingest_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Retry failed article records.")
    parser.add_argument("--env-file", help="Optional .env path")
    parser.add_argument(
        "--statuses",
        nargs="*",
        default=["send_failed", "analysis_failed", "extract_failed"],
        help="Statuses to retry.",
    )
    args = parser.parse_args()
    config = load_config(args.env_file)
    conn = connect_db(config.db_path)
    init_db(conn)
    placeholders = ",".join("?" for _ in args.statuses)
    rows = conn.execute(
        f"SELECT id, url, status FROM articles WHERE status IN ({placeholders}) ORDER BY id ASC",
        args.statuses,
    ).fetchall()
    requeued = 0
    reprocessed = 0
    results = []
    for row in rows:
        status = str(row["status"])
        if status == "send_failed":
            mark_article_status(conn, int(row["id"]), "queued", error_message=None)
            requeued += 1
            results.append({"id": int(row["id"]), "url": row["url"], "status": "queued"})
            continue
        result = ingest_url(str(row["url"]), conn=conn, env_file=args.env_file)
        reprocessed += 1
        results.append({"id": int(row["id"]), "url": row["url"], "status": result.get("status")})
    print(
        json.dumps(
            {
                "retried_count": len(rows),
                "requeued_count": requeued,
                "reprocessed_count": reprocessed,
                "statuses": args.statuses,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
