#!/usr/bin/env python3
"""Create a local Playwright session after the user logs in manually."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION = ROOT / "data" / "browser_profiles" / "mihuashi"


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化米画师本地 Playwright 登录会话")
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION)
    args = parser.parse_args()
    args.session_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(args.session_dir),
            headless=False,
            locale="zh-CN",
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.mihuashi.com/stalls", wait_until="domcontentloaded", timeout=30_000)
        print("请在打开的 Chromium 窗口中亲自完成备用账号登录。")
        print("不要把密码、验证码或 Cookie 粘贴到终端。")
        input("确认页面已显示登录后的米画师橱窗入口后，回到终端按 Enter 保存会话：")
        body = page.locator("body").inner_text(timeout=10_000)
        if "/login" in page.url or "登录后" in body[:600]:
            print("未检测到有效登录页面，会话未通过验证。")
            context.close()
            return 2
        context.close()
    print(f"本地会话已保存：{args.session_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
