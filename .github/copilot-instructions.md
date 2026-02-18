# Copilot Instructions

This repo is a GitHub Action that fetches recent articles from Atom feeds, converts them to e-reader-optimized PDFs, and uploads them to reMarkable Cloud via the `rmapi` CLI.

## Architecture

- `main.py` — `AtomFeedProcessor`: fetches feeds, filters by recency, cleans HTML, renders PDFs
- `remarkable.py` — `RemarkableUploader`: wraps `rmapi` subprocess calls for cloud upload
- `config.py` — all configuration; ENV vars override class-level defaults
- `templates/` — Jinja2 HTML template and CSS for PDF rendering (WeasyPrint)
- `action.yml` — Docker-based GitHub Action definition
- `tests/` — pytest unit tests (no external services); `tests/integration_test.py` requires live rmapi

## Key conventions

- All external calls (HTTP via `requests`, reMarkable via `subprocess`) must be mocked in unit tests
- Never commit directly to `main` — always use a branch
- Configuration lives in `Config` class in `config.py`; add new settings there with an ENV var override
- PDF output path: `output/{FeedName}/{MM-DD-YYYY ArticleTitle}.pdf`
- `rmapi` is the only interface to reMarkable Cloud — no direct API calls

## Running tests

```bash
pytest                        # unit tests (no credentials needed)
python tests/integration_test.py  # requires live rmapi + DEVICE_TOKEN
```
