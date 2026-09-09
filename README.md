# AI Marketing Assistant

## 五人在线 Demo

项目支持五个预生成账号登录。每个账号的用户画像、稳定偏好、AI 分析历史与结果复盘均通过服务器端 user_id 隔离。账号文件位于本机
data/private/friend_accounts.csv，该目录已被 Git 忽略。

GitHub 与 Render 的部署方法见 docs/deployment.md。

Environment and project skeleton for the AI Marketing Assistant demo. Business features are intentionally not included yet.

## Project rule

The root folder keeps its requested name, `AI Marketing Assistant`. All new subfolders, code directories, and configuration directories inside it must use English characters.

## Directory structure

- `frontend/`: minimal Node/Vite frontend skeleton
- `backend/`: FastAPI backend skeleton
- `data/`: project data
- `mock_data/`: local mock datasets
- `knowledge_base/`: future RAG source material
- `config/`: configuration files
- `scripts/`: utility scripts
- `docs/`: project documentation
- `tests/`: automated tests

## Long-term memory

The MVP uses a local SQLite store for confirmed profile facts, preferences, AI result history, and user/platform-reported outcomes. Initialize the confirmed demo user once:

```bash
source .venv/bin/activate
python scripts/initialize_memory.py
```

The runtime database is `data/memory.sqlite3` and is intentionally ignored by Git. See `docs/memory_design.md` for the write rules and API endpoints.

## Backend setup and start

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers playwright install chromium
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/health` to verify the API.

## Huajia public market collection PoC

The Playwright PoC reads only public artist, showcase-list, and showcase-detail fields. It never accesses login-only messages or orders. The first run creates a market baseline; later snapshots can be compared without treating a missing sample as a confirmed delisting.

```bash
source .venv/bin/activate
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers python scripts/collect_huajia_public.py --limit 5
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers python scripts/collect_huajia_showcases.py --limit 5
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers python scripts/collect_huajia_showcase_details.py --limit 3
python scripts/build_huajia_market_snapshot.py
```

Mihuashi collector scripts and `docs/mihuashi_collection_poc.md` remain as technical history and are not part of the active MVP path.

## Xiaohongshu public sample PoC

This collector reads only text already visible to a logged-out web visitor. It
does not log in, download media, collect comments, or bypass verification. The
default run creates separate samples for the public Explore page and the
keywords `手绘`, `水彩`, and `兽设`.

```bash
source .venv/bin/activate
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers python scripts/collect_xiaohongshu_public.py --limit 10 --headed --manual-confirm
```

Local output is written to `data/xiaohongshu_public_snapshot.json`; production
output is written to the configured persistent market-data directory. A restricted or
failed page is recorded explicitly; missing data is never converted to zero or
replaced by mock records.

An isolated MediaCrawler learning PoC is configured separately under
`tools/mediacrawler/`. It is not part of the application backend. See
`docs/mediacrawler_poc.md` for its fixed scope and stop conditions.

## Frontend setup and start

Node.js and npm must be installed first.

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

Copy `.env.example` to `.env`, then add local credentials. Never commit `.env` or real API keys.
