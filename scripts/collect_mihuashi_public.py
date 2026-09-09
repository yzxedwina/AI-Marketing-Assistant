#!/usr/bin/env python3
"""Collect a few public Mihuashi profile fields with Playwright.

This PoC is intentionally read-only and low volume. It does not log in, solve
CAPTCHAs, access messages/orders, or bypass access controls.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from backend.collectors.mihuashi import extract_labeled_counts, normalize_cards


DEFAULT_URL = "https://www.mihuashi.com/artists"
ALLOWED_HOSTS = {"mihuashi.com", "www.mihuashi.com"}


def validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise argparse.ArgumentTypeError("只允许 https://www.mihuashi.com 的公开页面")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_failure_reason(error: Exception) -> str:
    message = str(error)
    if "MachPortRendezvousServer" in message or "Permission denied (1100)" in message:
        return "browser_launch_blocked_by_local_sandbox"
    if isinstance(error, PlaywrightTimeoutError):
        return "page_load_timeout"
    return re.sub(r"\s+", " ", message).strip()[:300]


def validate_loaded_page(requested_url: str, final_url: str, body_text: str) -> None:
    requested = urlparse(requested_url)
    final = urlparse(final_url)
    if final.hostname not in ALLOWED_HOSTS:
        raise RuntimeError("redirected_outside_allowed_host")
    if "/profiles/" in requested.path and "/profiles/" not in final.path:
        raise RuntimeError("invalid_public_page_redirect")
    lowered = body_text.lower()
    if final.path.startswith("/500") or any(marker in lowered for marker in ("页面出错", "服务器错误", "internal server error")):
        raise RuntimeError("platform_error_page")


def collect(url: str, limit: int, headed: bool = False, min_wait: float = 3.0, max_wait: float = 7.0) -> Dict[str, Any]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context(
            locale="zh-CN",
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        )
        page = context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        wait_seconds = random.SystemRandom().uniform(min_wait, max_wait)
        page.wait_for_timeout(round(wait_seconds * 1000))
        final_url = page.url
        body_text = page.locator("body").inner_text(timeout=10_000)
        validate_loaded_page(url, final_url, body_text)
        blocked_terms = ("验证码", "访问过于频繁", "安全验证")
        if any(term in body_text for term in blocked_terms):
            raise RuntimeError("页面要求安全验证，PoC 已停止，不尝试绕过")
        if "/login" in final_url or "登录后" in body_text[:600]:
            raise RuntimeError("公开页面当前要求登录，PoC 已停止")

        headings = page.locator("h1, h2, [class*='name'], [class*='nickname']").all_inner_texts()
        profile_name = next((re.sub(r"\s+", " ", item).strip() for item in headings if item.strip()), None)
        links = page.locator("a[href]").evaluate_all(
            "els => els.map(el => ({text: (el.innerText || el.textContent || '').trim(), url: el.href}))"
        )
        page_type = "artist_list" if urlparse(final_url).path.startswith("/artists") else "profile"
        allowed_link_tokens = (
            ("/profiles/",)
            if page_type == "artist_list"
            else ("/artworks/", "/shops/", "/showcases/", "/work/")
        )
        likely_cards = [item for item in links if any(token in item["url"] for token in allowed_link_tokens)]
        result = {
            "schema_version": "1.0.0",
            "source_platform": "mihuashi",
            "source_type": "public_page_playwright",
            "source_url": url,
            "page_type": page_type,
            "final_url": final_url,
            "http_status": response.status if response else None,
            "collected_at": utc_now(),
            "profile": {
                "display_name": profile_name,
                **extract_labeled_counts(body_text),
            },
            "visible_items": normalize_cards(likely_cards, limit),
            "field_status": {},
            "limits": {
                "maximum_items": limit,
                "public_only": True,
                "login_used": False,
                "private_messages_or_orders": False,
                "concurrency": 1,
                "automatic_retries": 0,
                "wait_seconds": round(wait_seconds, 2),
            },
        }
        for field, value in result["profile"].items():
            result["field_status"][field] = "available" if value not in (None, "") else "not_visible"
        result["field_status"]["visible_items"] = "available" if result["visible_items"] else "not_visible"
        if page_type == "profile" and not any(value not in (None, "") for value in result["profile"].values()) and not result["visible_items"]:
            raise RuntimeError("no_public_business_fields_visible")
        if page_type == "artist_list" and not result["visible_items"]:
            raise RuntimeError("no_public_artist_items_visible")
        browser.close()
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="低频采集米画师公开主页的少量可见字段")
    parser.add_argument("--url", type=validate_url, default=DEFAULT_URL)
    parser.add_argument("--limit", type=int, default=3, choices=range(1, 6), metavar="1-5")
    parser.add_argument("--headed", action="store_true", help="显示 Chromium 窗口用于调试")
    parser.add_argument("--min-wait", type=float, default=3.0, help="页面加载后的最短等待秒数，最低 3 秒")
    parser.add_argument("--max-wait", type=float, default=7.0, help="页面加载后的最长等待秒数")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "collected" / "mihuashi")
    args = parser.parse_args()
    if args.min_wait < 3 or args.max_wait < args.min_wait:
        parser.error("等待区间必须满足 3 <= min-wait <= max-wait")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output_dir / f"profile_{timestamp}.json"
    try:
        result = collect(args.url, args.limit, args.headed, args.min_wait, args.max_wait)
        result["collection_status"] = "success"
        exit_code = 0
    except (PlaywrightError, PlaywrightTimeoutError, RuntimeError, OSError) as error:
        result = {
            "schema_version": "1.0.0",
            "source_platform": "mihuashi",
            "source_url": args.url,
            "collected_at": utc_now(),
            "collection_status": "blocked_or_failed",
            "reason": safe_failure_reason(error),
            "notice": "未绕过登录、验证码或访问限制。",
        }
        exit_code = 2
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["collection_status"], "output": str(output_path)}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
