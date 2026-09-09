#!/usr/bin/env python3
"""Collect up to 200 public Mihuashi stall cards at a courteous rate."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from backend.collectors.mihuashi_stalls import parse_stall_cards


URL = "https://www.mihuashi.com/stalls"
DEFAULT_SESSION = ROOT / "data" / "browser_profiles" / "mihuashi"


def collect(limit: int, max_scrolls: int, min_wait: float, max_wait: float, headed: bool, session_dir: Path) -> dict:
    with sync_playwright() as playwright:
        if not session_dir.exists() or not any(session_dir.iterdir()):
            raise RuntimeError("authenticated_session_not_initialized")
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(session_dir), headless=not headed,
            locale="zh-CN", viewport={"width": 1440, "height": 1100},
        )
        page = context.pages[0] if context.pages else context.new_page()
        response = page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(round(random.SystemRandom().uniform(min_wait, max_wait) * 1000))
        if "/login" in page.url or page.url.rstrip("/").endswith("/500"):
            raise RuntimeError("stalls_page_not_publicly_available")
        body_text = page.locator("body").inner_text(timeout=10_000)
        if "签名错误" in body_text:
            raise RuntimeError("platform_signature_error")

        # Enter through the site's own navigation. Directly constructing the list
        # URL can produce a platform signature error.
        list_links = page.locator('a[href*="/stalls/list"]')
        all_stalls_link = list_links.filter(has_text="全部橱窗")
        target = all_stalls_link.first if all_stalls_link.count() else list_links.first
        if target.count() == 0:
            raise RuntimeError("public_stall_list_entry_not_found")
        target.click()
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        page.wait_for_timeout(round(random.SystemRandom().uniform(min_wait, max_wait) * 1000))
        body_text = page.locator("body").inner_text(timeout=10_000)
        if "签名错误" in body_text:
            raise RuntimeError("platform_signature_error_after_site_navigation")

        all_cards: dict[str, dict] = {}
        unchanged_rounds = 0
        for scroll_index in range(max_scrolls + 1):
            body_text = page.locator("body").inner_text(timeout=10_000)
            if any(term in body_text for term in ("验证码", "访问过于频繁", "安全验证")):
                raise RuntimeError("platform_verification_or_rate_limit")
            cards = page.evaluate(
                """() => {
                  const patterns = ['/stalls/', '/stall/', '/products/', '/product/'];
                  return [...document.querySelectorAll('a[href]')].map(a => {
                    const href = a.href || '';
                    const parsed = new URL(href);
                    if (!patterns.some(p => href.includes(p)) || parsed.pathname === '/stalls' || parsed.pathname === '/stalls/list') return null;
                    let card = a;
                    for (let i = 0; i < 5 && card.parentElement; i++) {
                      const parent = card.parentElement;
                      const text = (parent.innerText || '').trim();
                      if (text.length >= 20 && text.length <= 1200) { card = parent; break; }
                      card = parent;
                    }
                    const text = (card.innerText || a.innerText || a.textContent || '').trim();
                    const lines = text.split(/\\n+/).map(x => x.trim()).filter(Boolean);
                    return {url: href, text, title: lines[0] || '', artist: lines.length > 1 ? lines[1] : ''};
                  }).filter(Boolean);
                }"""
            )
            before = len(all_cards)
            for item in cards:
                all_cards.setdefault(item["url"], item)
                if len(all_cards) >= limit:
                    break
            if len(all_cards) >= limit:
                break
            unchanged_rounds = unchanged_rounds + 1 if len(all_cards) == before else 0
            if unchanged_rounds >= 3:
                break
            page.mouse.wheel(0, 1600)
            page.wait_for_timeout(round(random.SystemRandom().uniform(min_wait, max_wait) * 1000))

        records = parse_stall_cards(all_cards.values(), limit)
        context.close()
        if not records:
            raise RuntimeError("no_public_stall_cards_detected")
        return {
            "schema_version": "1.0.0",
            "source_platform": "mihuashi",
            "source_type": "authenticated_stall_list_playwright",
            "source_url": URL,
            "http_status": response.status if response else None,
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "collection_status": "success" if len(records) >= limit else "partial",
            "requested_count": limit,
            "collected_count": len(records),
            "records": records,
            "limits": {"public_fields_only": True, "login_used": True, "private_messages_or_orders": False, "concurrency": 1, "automatic_retries": 0, "max_scrolls": max_scrolls},
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="低频采集米画师公开橱窗列表")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--max-scrolls", type=int, default=60)
    parser.add_argument("--min-wait", type=float, default=4.0)
    parser.add_argument("--max-wait", type=float, default=8.0)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "collected" / "mihuashi")
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error("limit 必须在 1—200 之间")
    if args.min_wait < 3 or args.max_wait < args.min_wait:
        parser.error("等待区间必须满足 3 <= min-wait <= max-wait")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"stalls_{stamp}.json"
    csv_path = args.output_dir / f"stalls_{stamp}.csv"
    try:
        result = collect(args.limit, args.max_scrolls, args.min_wait, args.max_wait, args.headed, args.session_dir)
        exit_code = 0 if result["collection_status"] == "success" else 1
    except (PlaywrightError, RuntimeError, OSError) as error:
        result = {
            "schema_version": "1.0.0", "source_platform": "mihuashi", "source_url": URL,
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "collection_status": "blocked_or_failed", "requested_count": args.limit,
            "collected_count": 0, "records": [], "reason": re.sub(r"\s+", " ", str(error)).strip()[:300],
        }
        exit_code = 2
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["records"]:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=result["records"][0].keys())
            writer.writeheader()
            writer.writerows(result["records"])
    print(json.dumps({"status": result["collection_status"], "collected": result["collected_count"], "json": str(json_path), "csv": str(csv_path) if result["records"] else None}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
