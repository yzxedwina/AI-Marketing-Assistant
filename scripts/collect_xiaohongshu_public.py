#!/usr/bin/env python3
"""Collect a small, public, logged-out Xiaohongshu sample with Playwright.

This PoC intentionally avoids login, private pages, comments, media downloads,
anti-detection techniques, and CAPTCHA bypass. If access is restricted, the
run records that state and stops.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import Page, async_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "xiaohongshu_public_snapshot.json"
DEFAULT_KEYWORDS = ("手绘", "水彩", "兽设")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact(text: str | None) -> str | None:
    if not text:
        return None
    value = re.sub(r"\s+", " ", text).strip()
    return value or None


async def detect_restriction(page: Page) -> str | None:
    text = compact(await page.locator("body").inner_text()) or ""
    # A dismissible login prompt is not treated as a blocked page when public
    # cards remain available underneath it.
    markers = ("账号异常", "帐号异常", "安全验证", "请完成验证", "访问异常")
    return next((marker for marker in markers if marker in text), None)


def card_links(page: Page):
    return page.locator(
        'section.note-item a[href*="/explore/"], '
        'section.note-item a[href*="/search_result/"], '
        'a.cover[href*="/explore/"], '
        'a.cover[href*="/search_result/"]'
    )


async def wait_for_cards(page: Page, timeout_ms: int) -> int:
    elapsed = 0
    while elapsed < timeout_ms:
        count = await card_links(page).count()
        if count:
            return count
        await page.wait_for_timeout(1000)
        elapsed += 1000
    return 0


async def collect_cards(page: Page, limit: int) -> list[dict]:
    # Public web layouts change regularly. Prefer semantic links and extract
    # only text already rendered to a logged-out visitor.
    links = card_links(page)
    if await links.count() == 0:
        links = page.locator('a[href*="/explore/"], a[href*="/search_result/"]')
    count = min(await links.count(), limit * 4)
    records: list[dict] = []
    seen: set[str] = set()
    for index in range(count):
        link = links.nth(index)
        href = await link.get_attribute("href")
        if not href:
            continue
        url = href if href.startswith("http") else f"https://www.xiaohongshu.com{href}"
        canonical_url = url.split("?")[0]
        if not re.search(r"/(?:explore|search_result)/[0-9a-f]{16,}", canonical_url):
            continue
        if canonical_url in seen:
            continue
        seen.add(canonical_url)
        title = compact(await link.get_attribute("title"))
        card = link.locator("xpath=ancestor::section[1]")
        if await card.count() == 0:
            card = link.locator("xpath=ancestor::article[1]")
        if await card.count() == 0:
            card = link.locator("xpath=ancestor::div[contains(@class,'note-item')][1]")
        visible_text = compact(await card.inner_text()) if await card.count() else compact(await link.inner_text())
        if not title and await card.count():
            title_nodes = card.locator(".title, [class*='title']")
            if await title_nodes.count():
                title = compact(await title_nodes.first.inner_text())
        author = None
        interaction = None
        if await card.count():
            author_nodes = card.locator(".author .name, [class*='author'] [class*='name']")
            count_nodes = card.locator(".like-wrapper .count, [class*='like'] [class*='count']")
            if await author_nodes.count():
                author = compact(await author_nodes.first.inner_text())
            if await count_nodes.count():
                interaction = compact(await count_nodes.first.inner_text())
        records.append(
            {
                "url": canonical_url,
                "title": title,
                "author_display": author,
                "interaction_display": interaction,
                "visible_card_text": visible_text,
            }
        )
        if len(records) >= limit:
            break
    return records


async def collect_page(
    page: Page,
    *,
    label: str,
    url: str,
    limit: int,
    load_timeout_ms: int,
    manual_confirm: bool,
    expected_keyword: str | None,
) -> dict:
    started_at = utc_now()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        if manual_confirm:
            print(
                f"\n[{label}] 页面已打开。请等待内容加载；若出现普通登录弹窗可手动关闭。\n"
                "不要点击帖子。确认列表已经显示后，回到终端按 Enter 采集当前页面。",
                flush=True,
            )
            await asyncio.to_thread(input)
            candidate_count = await card_links(page).count()
        else:
            candidate_count = await wait_for_cards(page, load_timeout_ms)
        redirected_from_search = bool(expected_keyword and "/search_result" not in page.url)
        restriction = await detect_restriction(page)
        records = (
            []
            if redirected_from_search or (restriction and not candidate_count)
            else await collect_cards(page, limit)
        )
        body_excerpt = None
        if not records:
            body_excerpt = compact(await page.locator("body").inner_text())
            body_excerpt = body_excerpt[:800] if body_excerpt else None
        return {
            "label": label,
            "requested_url": url,
            "final_url": page.url,
            "collected_at": started_at,
            "http_status": response.status if response else None,
            "access_status": (
                "restricted"
                if restriction
                else "redirected_from_search"
                if redirected_from_search
                else "ok"
                if records
                else "no_records"
            ),
            "restriction_reason": restriction,
            "expected_keyword": expected_keyword,
            "data_quality_note": (
                "搜索请求被重定向到普通发现页，页面内容不得标记为该关键词样本。"
                if redirected_from_search
                else None
            ),
            "candidate_link_count": candidate_count,
            "body_excerpt_when_empty": body_excerpt,
            "record_count": len(records),
            "records": records,
        }
    except Exception as exc:  # Preserve evidence instead of hiding a failed run.
        return {
            "label": label,
            "requested_url": url,
            "final_url": page.url,
            "collected_at": started_at,
            "access_status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "record_count": 0,
            "records": [],
        }


async def run(args: argparse.Namespace) -> dict:
    targets = [] if args.vertical_only else [
        ("大众热点候选", "https://www.xiaohongshu.com/explore", None)
    ]
    targets.extend(
        (
            f"垂直话题：#{keyword}",
            f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_search_result_notes",
            keyword,
        )
        for keyword in args.keywords
    )
    results = []
    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=not args.headed)
            context = await browser.new_context(
                locale="zh-CN",
                viewport={"width": 1440, "height": 1000},
            )
            page = await context.new_page()
            remaining = args.total_limit
            for label, url, expected_keyword in targets:
                if remaining is not None and remaining <= 0:
                    break
                page_limit = min(args.limit, remaining) if remaining is not None else args.limit
                results.append(
                    await collect_page(
                        page,
                        label=label,
                        url=url,
                        limit=page_limit,
                        load_timeout_ms=args.load_timeout_ms,
                        manual_confirm=args.manual_confirm,
                        expected_keyword=expected_keyword,
                    )
                )
                if remaining is not None:
                    remaining -= results[-1]["record_count"]
                if results[-1]["access_status"] in {"restricted", "redirected_from_search"}:
                    print(
                        "检测到访问限制或搜索页重定向，已停止本轮，不再访问后续页面。",
                        flush=True,
                    )
                    break
                await page.wait_for_timeout(args.wait_ms)
            await browser.close()
        except Exception as exc:
            results = [
                {
                    "label": label,
                    "requested_url": url,
                    "collected_at": utc_now(),
                    "access_status": "runtime_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "record_count": 0,
                    "records": [],
                }
                for label, url, _expected_keyword in targets
            ]
    return {
        "dataset": "xiaohongshu_public_market_sample",
        "schema_version": "1.0.0",
        "generated_at": utc_now(),
        "collection_policy": {
            "login": False,
            "public_visible_text_only": True,
            "media_downloaded": False,
            "comments_collected": False,
            "captcha_bypass": False,
            "sample_limit_per_target": args.limit,
            "total_limit": args.total_limit,
            "manual_confirm": args.manual_confirm,
            "interpretation": "发现页记录仅是公开推荐样本，需经过多次快照和增长规则后才能标记为热点。",
        },
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", nargs="+", default=list(DEFAULT_KEYWORDS))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--total-limit", type=int)
    parser.add_argument(
        "--vertical-only",
        action="store_true",
        help="Only visit keyword result pages; omit the general Explore page.",
    )
    parser.add_argument("--wait-ms", type=int, default=3000)
    parser.add_argument("--load-timeout-ms", type=int, default=30000)
    parser.add_argument(
        "--manual-confirm",
        action="store_true",
        help="Open each page once and wait for Enter before reading it; never auto-refresh while waiting.",
    )
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 1 <= args.limit <= 50:
        raise SystemExit("--limit must be between 1 and 50")
    if args.total_limit is not None and not 1 <= args.total_limit <= 100:
        raise SystemExit("--total-limit must be between 1 and 100")
    payload = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "results": [
        {"label": item["label"], "status": item["access_status"], "records": item["record_count"]}
        for item in payload["results"]
    ]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
