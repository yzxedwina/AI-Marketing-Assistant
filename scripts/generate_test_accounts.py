#!/usr/bin/env python3
"""Generate local-only credentials for a small friends-and-family trial."""
from __future__ import annotations

import argparse
import csv
import json
import secrets
import string
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIR = ROOT / "data" / "private"


def password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Ama-" + "".join(secrets.choice(alphabet) for _ in range(14))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.count <= 20:
        raise SystemExit("账号数量必须在 1—20 之间")
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    json_path = PRIVATE_DIR / "preseed_accounts.json"
    csv_path = PRIVATE_DIR / "friend_accounts.csv"
    if json_path.exists() or csv_path.exists():
        raise SystemExit("账号文件已存在；为避免覆盖密码，本次未重新生成")
    accounts = [
        {
            "user_id": f"USR-FRIEND-{index:03d}",
            "username": f"friend{index:02d}",
            "password": password(),
            "display_name": f"体验用户 {index}",
        }
        for index in range(1, args.count + 1)
    ]
    json_path.write_text(json.dumps(accounts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=["username", "password", "display_name", "user_id"])
        writer.writeheader()
        writer.writerows(accounts)
    print(json.dumps({"count": len(accounts), "credentials": str(csv_path), "seed": str(json_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
