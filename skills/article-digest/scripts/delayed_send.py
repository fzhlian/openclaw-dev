#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import send_article_by_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a single queued article after a delay.")
    parser.add_argument("--article-id", type=int, required=True, help="Article id to send")
    parser.add_argument("--delay-seconds", type=int, required=True, help="Seconds to wait before sending")
    parser.add_argument("--wait-ready-seconds", type=int, default=900, help="How long to wait for the article to become ready")
    parser.add_argument("--env-file", help="Optional .env path")
    args = parser.parse_args()

    if args.delay_seconds > 0:
        time.sleep(args.delay_seconds)

    result = send_article_by_id(
        args.article_id,
        env_file=args.env_file,
        wait_ready_seconds=max(0, args.wait_ready_seconds),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "sent" else 1


if __name__ == "__main__":
    raise SystemExit(main())
