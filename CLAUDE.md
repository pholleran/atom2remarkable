# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

`atom2remarkable` fetches articles from Atom/RSS feeds, converts them to e-reader-optimized PDFs, and uploads them to a reMarkable Cloud account. It runs as a scheduled GitHub Actions workflow (daily at 6 AM UTC) or locally via Python/Docker.

## Commands

```bash
# Run the application
python main.py

# Run tests
python test.py

# Install dependencies
pip install -r requirements.txt

# Docker
docker build -t atom2remarkable .
docker run --rm --env-file .env atom2remarkable
./run.sh  # Docker wrapper script
```

## Architecture

**Core flow:**
1. Load feed URLs from `feeds.txt`
2. Fetch, parse, and filter recent entries (configurable `RECENT_HOURS` lookback, default 24h)
3. Clean HTML with BeautifulSoup, render via Jinja2 (`templates/article.html` + `templates/style.css`)
4. Generate PDFs with WeasyPrint → `output/{FeedName}/{MM-DD-YYYY ArticleTitle}.pdf`
5. Upload to reMarkable Cloud via `rmapi` CLI binary

**Key files:**
- `main.py` — `AtomFeedProcessor` class; orchestrates the full pipeline
- `remarkable.py` — `RemarkableUploader` class; wraps `rmapi` subprocess calls
- `config.py` — All configuration with ENV var overrides
- `templates/` — Jinja2 HTML template and e-reader CSS
- `.github/workflows/test-action.yml` — Scheduled GitHub Actions workflow
- `action.yml` — Docker-based GitHub Action definition

**Configuration (ENV vars override defaults):**
- `RECENT_HOURS` — Lookback window (default: 24)
- `DEVICE_TOKEN` — reMarkable authentication (required for uploads)
- `REMARKABLE_FOLDER` — Cloud folder name (default: AtomFeeds)
- `OUTPUT_DIR`, `LOG_DIR`, `FEEDS_FILE` — Path overrides
- `MAX_IMAGE_WIDTH`, `PDF_FONT_SIZE` — PDF rendering options

**Deduplication:** The uploader checks if a PDF already exists in reMarkable Cloud before uploading. Locally, duplicate filenames get a counter suffix (e.g., `Article 1.pdf`).

**Exit codes:** `0` = success, `1` = all PDFs failed, `2` = partial failures.

## Git Workflow

Always create a new branch before making code changes. Never commit directly to `main`.

## External Dependencies

- `rmapi` binary — must be installed separately for local uploads (auto-downloaded in Docker)
- reMarkable Cloud account with a valid device token
