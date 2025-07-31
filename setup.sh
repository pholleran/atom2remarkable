#!/bin/bash

# Setup script for RemarkableAtom

echo "Setting up RemarkableAtom - Atom Feed to PDF Converter"
echo "======================================================"

# Create necessary directories
echo "Creating directories..."
mkdir -p output
mkdir -p logs
mkdir -p templates

# Check if feeds.txt exists
if [ ! -f "feeds.txt" ]; then
    echo "Creating example feeds.txt..."
    cat > feeds.txt << EOF
# Example Atom/RSS feeds - edit this file to add your own
https://realpython.com/atom.xml
https://feeds.feedburner.com/oreilly/radar
https://planet.python.org/rss20.xml
EOF
    echo "✓ Created feeds.txt with example feeds"
else
    echo "✓ feeds.txt already exists"
fi

# Check if template exists
if [ ! -f "templates/article.html" ]; then
    echo "✗ Template file missing - please ensure templates/article.html exists"
    exit 1
else
    echo "✓ Template file found"
fi

echo ""
echo "Setup complete! You can now:"
echo "1. Edit feeds.txt to add your Atom feed URLs"
echo "2. Run: python main.py"
echo "3. Or run with Docker: docker run --rm --env-file .env atom2remarkable"
echo ""
echo "For scheduled runs, set up a CRON job to run the application periodically."
