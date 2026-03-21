from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analysis import assess_credibility
from app.config import load_config
from app.extraction import extract_article


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess article credibility heuristically.")
    parser.add_argument("url")
    parser.add_argument("--env-file")
    args = parser.parse_args()
    config = load_config(args.env_file)
    article = extract_article(
        args.url,
        raw_html_dir=config.raw_html_dir,
        extracted_text_dir=config.extracted_text_dir,
    )
    print(json.dumps(assess_credibility(article).to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

