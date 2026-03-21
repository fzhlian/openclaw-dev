from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import send_digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Send queued article digest.")
    parser.add_argument("--env-file", help="Optional .env path")
    parser.add_argument("--dry-run", action="store_true", help="Build digest but do not send it")
    args = parser.parse_args()
    result = send_digest(env_file=args.env_file) if not args.dry_run else send_digest(env_file=args.env_file, runner=lambda *a, **k: None, telegram_sender=lambda *a, **k: {"result": {"message_id": "dry-run"}})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"sent", "empty"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

