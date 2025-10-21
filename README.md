# atom2reMarkable

Turn your favorite Atom feeds into PDFs on your reMarkable tablet. This Python app fetches recent articles, converts them to clean PDFs, and uploads them to your reMarkable Cloud automatically.

## Quick Start

### Authentication

You'll need a reMarkable device token to upload PDFs. Here's how to get one:

1. Clone this repo and install dependencies (see below)
2. Run `rmapi` once and complete the authentication flow
3. Run `./TOKEN_RETRIEVER.sh` to extract your device token
4. Save the token as a `DEVICE_TOKEN` environment variable or repository secret
   
### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Add your feed URLs to feeds.txt (one per line)
echo "https://realpython.com/atom.xml" >> feeds.txt

# Run it
python main.py
```

### Docker

```bash
# Create .env file with your token
echo 'DEVICE_TOKEN="your_token_here"' > .env

# Build and run
docker build -t atom2remarkable .
docker run --rm --env-file .env atom2remarkable

# Or use the helper script
./run.sh

# Customize the time window
docker run --rm --env-file .env -e RECENT_HOURS=48 atom2remarkable
```

### GitHub Actions Deployment

The application includes an example GitHub Actions workflow that:

- Runs daily at 6:00 AM UTC
- Can be triggered manually with custom parameters
- Generates PDFs inside the container
- Automatically uploads to reMarkable Cloud
- Extracts and uploads results as artifacts

**Setup:**
1. Push this repository to GitHub
2. Add your `DEVICE_TOKEN` as a repository secret
3. The workflow is defined in `.github/workflows/atom-feed-processor.yml`
4. PDFs will be uploaded to your reMarkable device and available as downloadable artifacts

**Manual trigger:**
- Go to Actions tab in your GitHub repository
- Select "Atom Feed Processor" workflow
- Click "Run workflow" to process feeds immediately
docker run --rm \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/logs:/app/logs" \
  atom2remarkable

## Configuration

### Environment Variables

- `FEEDS_FILE`: Path to feeds list file (default: `feeds.txt`)
- `OUTPUT_DIR`: Directory for generated PDFs (default: `output`)
- `LOG_DIR`: Directory for log files (default: `logs`)
- `RECENT_HOURS`: Hours to look back for recent entries (default: `24`)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: `30`)

### reMarkable Cloud Integration

- `DEVICE_TOKEN`: Your reMarkable device token (required for upload)
- `REMARKABLE_FOLDER`: Folder name in reMarkable Cloud (default: `AtomFeeds`)

### Command Line Options

```bash
python main.py [OPTIONS]

Options:
  --feeds-file PATH        Override feeds.txt file location
  --output-dir PATH        Override output directory
  --recent-hours INT       Override recent entry window
  --remarkable-folder NAME reMarkable folder name
  --rmapi-path PATH        Path to rmapi binary
```

## Output

### PDF Files

PDFs are organized into subdirectories by feed name, with publication date and article titles as filenames:

```
output/
├── Feed Name 1/
│   ├── MM-DD-YYYY Article Title 1.pdf
│   ├── MM-DD-YYYY Article Title 2.pdf
│   └── MM-DD-YYYY Another Article Title.pdf
└── Feed Name 2/
    ├── MM-DD-YYYY Different Article.pdf
    └── MM-DD-YYYY Some Other Article.pdf
```

Example: `output/Real Python/07-28-2025 Pythons asyncio A Hands-On Walkthrough.pdf`

If duplicate article titles exist within the same feed on the same date, a counter is appended (e.g., `07-30-2025 Article Title.pdf`, `07-30-2025 Article Title 1.pdf`).

### PDF Formatting

PDFs of the Atom feeds are generated using the `arcicle.html` and `style.css` files within the `/templates` directory.

## Testing
Run the consolidated test script to verify all functionality:

```bash
python test.py
```

## License

MIT License - see LICENSE file for details.
