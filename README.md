# atom2reMarkable

Turn your Atom feeds into PDFs on your reMarkable tablet — automatically, every day.

This is a GitHub Action that fetches recent articles from Atom feeds you specify, converts them to clean, e-reader-optimized PDFs, and uploads them to your reMarkable Cloud.

## Using as a GitHub Action

The easiest way to use atom2reMarkable is to create a small private repo that holds your feed list and a workflow that calls this action.

**1. Get your reMarkable device token**

You'll need to authenticate with reMarkable Cloud once to get a device token. Clone this repo temporarily to access the helper script:

```bash
# Clone this repo
git clone https://github.com/pholleran/atom2remarkable.git
cd atom2remarkable

# Install rmapi (macOS)
brew install rmapi

# Authenticate with reMarkable Cloud — this will prompt you to log in via a one-time code
rmapi

# Once authenticated, extract your device token
./TOKEN_RETRIEVER.sh
```

Save the token somewhere safe — you'll add it as a secret in the next step. You can delete the cloned repo once you have it.

**2. Create a private config repo**

Create a new private GitHub repo (e.g. `atom2remarkable-config`) with:

`feeds.txt` — one feed URL per line:
```
https://simonwillison.net/atom/everything/
https://realpython.com/atom.xml
```

`.github/workflows/run.yml`:
```yaml
name: Run Atom2Remarkable

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:
    inputs:
      recent_hours:
        description: 'Hours to look back for recent entries'
        required: false
        default: '24'
        type: string

jobs:
  process-feeds:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: pholleran/atom2remarkable@main
      with:
        device_token: ${{ secrets.DEVICE_TOKEN }}
        recent_hours: ${{ github.event.inputs.recent_hours || '24' }}
```

**3. Add your device token as a secret**

In your config repo, go to Settings → Secrets and variables → Actions, and add `DEVICE_TOKEN`.

That's it. The workflow will run daily and your reMarkable will stay stocked with fresh reading.

## Action Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `device_token` | reMarkable device token | required |
| `feeds_file` | Path to your feeds list | `feeds.txt` |
| `remarkable_folder` | Folder name in reMarkable Cloud | `AtomFeeds` |
| `recent_hours` | How far back to look for new articles | `24` |

## Running Locally

```bash
pip install -r requirements.txt

# Add feed URLs to feeds.txt (one per line)
echo "https://realpython.com/atom.xml" >> feeds.txt

# Set your token and run
export DEVICE_TOKEN="your_token_here"
python main.py
```

### Docker

```bash
echo 'DEVICE_TOKEN="your_token_here"' > .env
docker build -t atom2remarkable .
docker run --rm --env-file .env atom2remarkable

# Or use the helper script
./run.sh
```

## Configuration

All settings can be overridden with environment variables or CLI flags.

| Variable | CLI flag | Default |
|----------|----------|---------|
| `FEEDS_FILE` | `--feeds-file` | `feeds.txt` |
| `OUTPUT_DIR` | `--output-dir` | `output` |
| `LOG_DIR` | — | `logs` |
| `RECENT_HOURS` | `--recent-hours` | `24` |
| `REQUEST_TIMEOUT` | — | `30` |
| `REMARKABLE_FOLDER` | `--remarkable-folder` | `AtomFeeds` |
| `RMAPI_PATH` | `--rmapi-path` | `rmapi` |

## Output

PDFs are organized by feed name with the publication date in the filename:

```
output/
├── Real Python/
│   └── 07-28-2025 Python asyncio A Hands-On Walkthrough.pdf
└── Simon Willison/
    └── 07-28-2025 Notes on a new approach to AI evals.pdf
```

## License

MIT — see LICENSE for details.
