#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.scoring import build_scoring_result, load_json, load_rules


def main() -> None:
    parser = argparse.ArgumentParser(description="运行确定性业务评分")
    parser.add_argument("--profile-id", default="USR-001")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    accounts = load_json(ROOT / "mock_data" / "accounts.json")["records"]
    market = load_json(ROOT / "mock_data" / "market.json")["records"]
    trends = load_json(ROOT / "mock_data" / "trends.json")["records"]
    profile = next((row for row in accounts if row["profile_id"] == args.profile_id), None)
    if profile is None:
        raise SystemExit(f"找不到 profile_id: {args.profile_id}")
    result = build_scoring_result(profile, market, trends, load_rules())
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
