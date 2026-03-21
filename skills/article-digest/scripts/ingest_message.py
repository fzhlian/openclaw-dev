from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import ingest_message


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest one Telegram-style text message containing one or more article URLs.")
    parser.add_argument("message", help="Raw message text")
    parser.add_argument("--env-file", help="Optional .env path")
    args = parser.parse_args()
    result = ingest_message(args.message, env_file=args.env_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"queued", "partial_failed", "duplicate"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

