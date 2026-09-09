#!/usr/bin/env python3
"""Small read-only Playwright probe for public Huajia pages."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://huajia.163.com/main/arts"
ALLOWED_HOST = "huajia.163.com"


def normalize(items: list[dict], limit: int) -> list[dict]:
    output, seen = [], set()
    for item in items:
        url = str(item.get("url") or "").strip()
        text = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
        path = urlparse(url).path
        is_navigation = bool(re.fullmatch(r"/board/artist/list(?:/\d+)?/?", path))
        if not url or url in seen or len(text) < 2 or is_navigation:
            continue
        seen.add(url)
        output.append({"title": text[:120], "public_url": url, "visible_text": text[:600]})
        if len(output) >= limit:
            break
    return output


def normalize_artist_payload(payload: dict, limit: int) -> list[dict]:
    artists = ((payload.get("data") or {}).get("artist_list") or [])
    records = []
    for artist in artists[:limit]:
        uid = str(artist.get("uid") or artist.get("unique_id") or "").strip()
        name = re.sub(r"\s+", " ", str(artist.get("name") or "")).strip()
        if not uid or not name:
            continue
        grade = artist.get("artist_grade_tag") or {}
        works = artist.get("detailed_show_works") or []
        records.append({
            "artist_id": uid,
            "artist_name": name,
            "public_url": f"https://{ALLOWED_HOST}/main/profile/{uid}",
            "average_score": artist.get("artist_average_score"),
            "evaluation_count": artist.get("from_buyer_evaluation_count"),
            "online_showcase_count": artist.get("online_goods_count"),
            "public_work_count": artist.get("valid_work_count"),
            "artist_grade": grade.get("title"),
            "intro": str(artist.get("intro") or "")[:1000],
            "sample_work_tags": sorted({tag for work in works for tag in (work.get("show_tags") or [])}),
            "sample_work_like_counts": [work.get("like_count") for work in works if work.get("like_count") is not None],
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="验证画加公开网页的小规模读取能力")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--min-wait", type=float, default=4.0)
    parser.add_argument("--max-wait", type=float, default=8.0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "collected" / "huajia")
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        parser.error("只允许访问 https://huajia.163.com")
    if not 1 <= args.limit <= 5:
        parser.error("首次验证 limit 必须在 1—5 之间")
    if args.min_wait < 3 or args.max_wait < args.min_wait:
        parser.error("等待区间必须满足 3 <= min-wait <= max-wait")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"public_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result = {"schema_version": "1.0.0", "source_platform": "huajia", "source_url": args.url,
              "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(locale="zh-CN", viewport={"width": 1440, "height": 1000})
            api_responses: list[dict] = []

            def remember_response(response) -> None:
                request = response.request
                if request.resource_type not in {"xhr", "fetch"}:
                    return
                if urlparse(response.url).hostname != ALLOWED_HOST:
                    return
                api_responses.append({"url": response.url, "status": response.status,
                                      "resource_type": request.resource_type})

            page.on("response", remember_response)
            response = page.goto(args.url, wait_until="domcontentloaded", timeout=30_000)
            wait_seconds = random.SystemRandom().uniform(args.min_wait, args.max_wait)
            page.wait_for_timeout(round(wait_seconds * 1000))
            page.mouse.wheel(0, 700)
            page.wait_for_timeout(1200)
            body = page.locator("body").inner_text(timeout=10_000)
            gate_locator = page.locator("text=/访问过于频繁|安全验证/")
            visible_gate = any(gate_locator.nth(index).is_visible() for index in range(gate_locator.count()))
            if visible_gate:
                raise RuntimeError("platform_verification_or_rate_limit")
            items = page.evaluate("""() => [...document.querySelectorAll('a[href]')].map(a => {
              const u = new URL(a.href); const path = u.pathname;
              const isArtist = path.includes('/main/profile/') || path.includes('/profile/') || /^\/board\/artist\/(?!list(?:\/|$))/.test(path);
              const isGoods = path.includes('/main/goods/details/');
              if (!(isArtist || isGoods)) return null;
              let card = a;
              for (let i=0; i<5 && card.parentElement; i++) {
                card = card.parentElement;
                const t=(card.innerText||'').trim();
                if (t.length>=15 && t.length<=1200) break;
              }
              return {url:a.href, text:(card.innerText||a.innerText||'').trim()};
            }).filter(Boolean)""")
            records = normalize(items, args.limit)
            artist_api_url = (
                f"https://{ALLOWED_HOST}/napp/artist/list"
                f"?page=1&page_size={args.limit}&tab=recommend&artist_sub_types="
            )
            artist_response = page.request.get(artist_api_url, timeout=20_000)
            if artist_response.ok:
                api_records = normalize_artist_payload(artist_response.json(), args.limit)
                if api_records:
                    records = api_records
            diagnostic_links = page.evaluate("""() => [...document.querySelectorAll('a[href]')]
              .slice(0, 40).map(a => ({
                text: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 120),
                href: a.href
              }))""")
            result.update({"final_url": page.url, "http_status": response.status if response else None,
                           "collection_status": "success" if records else "no_public_records",
                           "collected_count": len(records), "records": records,
                           "limits": {"public_only": True, "login_used": False, "maximum_items": args.limit,
                                      "concurrency": 1, "automatic_retries": 0, "wait_seconds": round(wait_seconds, 2)},
                           "diagnostics": {"page_title": page.title()[:160],
                                           "body_excerpt": re.sub(r"\s+", " ", body).strip()[:1000],
                                           "links": diagnostic_links,
                                           "api_responses": api_responses[:40]}})
            browser.close()
    except (PlaywrightError, RuntimeError, OSError) as error:
        result.update({"collection_status": "blocked_or_failed", "collected_count": 0, "records": [],
                       "reason": re.sub(r"\s+", " ", str(error)).strip()[:300]})
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["collection_status"], "collected": result["collected_count"], "output": str(output_path)}, ensure_ascii=False))
    return 0 if result["collection_status"] == "success" else 2


if __name__ == "__main__":
    sys.exit(main())
