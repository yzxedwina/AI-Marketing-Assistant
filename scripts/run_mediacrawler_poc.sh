#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CRAWLER_ROOT="$PROJECT_ROOT/tools/mediacrawler/MediaCrawler-main"
UV_BIN="$PROJECT_ROOT/tools/uv-bootstrap/bin/uv"

if [ ! -x "$UV_BIN" ]; then
  echo "MediaCrawler bootstrap environment is missing." >&2
  exit 1
fi

cd "$CRAWLER_ROOT"
export UV_CACHE_DIR="$PROJECT_ROOT/tools/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PROJECT_ROOT/tools/.uv-python"
export PLAYWRIGHT_BROWSERS_PATH="$PROJECT_ROOT/tools/.mediacrawler-browsers"

echo "PoC scope: Xiaohongshu / keyword 兽设 / max 20 / no comments or media / no proxy"
echo "Stop immediately if the platform shows verification, account abnormality, or access restriction."
exec "$UV_BIN" run main.py --platform xhs --lt qrcode --type search
