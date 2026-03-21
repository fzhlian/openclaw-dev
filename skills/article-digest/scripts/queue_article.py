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
    parser = argparse.ArgumentParser(description="Queue one article URL for daily digest delivery.")
    parser.add_argument("url")
    parser.add_argument("--env-file")
    args = parser.parse_args()
    result = ingest_url(args.url, immediate=False, env_file=args.env_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "queued" else 1


if __name__ == "__main__":
    raise SystemExit(main())

