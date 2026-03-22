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
    parser = argparse.ArgumentParser(description="抓取单篇文章链接，完成分析，并按配置直接推送或入队。")
    parser.add_argument("url", help="文章链接")
    parser.add_argument("--immediate", action="store_true", help="额外返回单篇完整研判文本")
    parser.add_argument("--仅入队", action="store_true", help="只写入队列，不立即推送 Telegram")
    parser.add_argument("--env-file", help="可选的 .env 文件路径")
    args = parser.parse_args()
    result = ingest_url(args.url, immediate=args.immediate, 仅入队=args.仅入队, env_file=args.env_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"queued", "duplicate", "sent"} or args.immediate else 1


if __name__ == "__main__":
    raise SystemExit(main())
