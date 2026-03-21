#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import ingest_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest one article URL into the digest queue.")
    parser.add_argument("url", help="Article URL")
    parser.add_argument("--immediate", action="store_true", help="Return the single-article analysis instead of queue acknowledgement.")
    parser.add_argument("--env-file", help="Optional .env path")
    args = parser.parse_args()
    result = ingest_url(args.url, immediate=args.immediate, env_file=args.env_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"queued", "duplicate"} or args.immediate else 1


if __name__ == "__main__":
    raise SystemExit(main())
