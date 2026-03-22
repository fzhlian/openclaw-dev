#!/usr/bin/env python3

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
    parser = argparse.ArgumentParser(description="处理一条 Telegram 风格消息，提取其中的文章链接并执行后续任务。")
    parser.add_argument("message", help="原始消息文本")
    parser.add_argument("--env-file", help="可选的 .env 文件路径")
    args = parser.parse_args()
    result = ingest_message(args.message, env_file=args.env_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "queued",
        "scheduled",
        "schedule_updated",
        "schedule_partial",
        "partial_failed",
        "duplicate",
        "sent",
        "empty",
        "favorited",
        "unfavorited",
        "favorites_list",
        "favorite_detail",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
