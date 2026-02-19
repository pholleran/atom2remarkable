import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser
from jinja2 import Environment, FileSystemLoader, select_autoescape
import requests
from weasyprint import HTML, CSS

from config import Config
from remarkable import RemarkableUploader

class AtomFeedProcessor:
    def __init__(self):
        """Initialize the Atom feed processor for reMarkable Cloud upload"""
        self.setup_logging()
        Config.setup_directories()
        
        if Config.TEMPLATE_FILE:
            template_path = Path(Config.TEMPLATE_FILE)
            template_dir = str(template_path.parent)
            self.template_name = template_path.name
        else:
            template_dir = Config.TEMPLATE_DIR
            self.template_name = 'article.html'

        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Initialize reMarkable uploader
        self.remarkable_uploader = RemarkableUploader()
        
        # Statistics
        self.stats = {
            'feeds_processed': 0,
            'feeds_failed': 0,
            'entries_found': 0,
            'entries_recent': 0,
            'pdfs_generated': 0,
            'pdfs_skipped': 0,
            'pdfs_failed': 0,
            'remarkable_uploaded': 0,
            'remarkable_skipped': 0,
            'remarkable_failed': 0
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = Path(Config.LOG_DIR) / f"atom_processor_{date_str}.log"
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt=Config.LOG_DATE_FORMAT
        )
        
        # Setup file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Setup logger
        self.logger = logging.getLogger('AtomProcessor')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Prevent duplicate logs
        self.logger.propagate = False
    
    def load_feeds(self) -> List[str]:
        """Load feed URLs from feeds.txt file"""
        feeds_file = Path(Config.FEEDS_FILE)
        
        if not feeds_file.exists():
            self.logger.error(f"Feeds file not found: {feeds_file}")
            return []
        
        try:
            with open(feeds_file, 'r', encoding='utf-8') as f:
                feeds = [
                    line.strip() for line in f 
                    if line.strip() and not line.startswith('#')
                ]
            
            self.logger.info(f"Loaded {len(feeds)} feed URLs from {feeds_file}")
            return feeds
            
        except Exception as e:
            self.logger.error(f"Error reading feeds file: {e}")
            return []
    
    def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse a single feed"""
        try:
            self.logger.info(f"Fetching feed: {feed_url}")
            
            headers = {
                'User-Agent': Config.USER_AGENT,
                'Accept': (
                    'application/atom+xml, application/rss+xml, '
                    'application/xml, text/xml'
                )
            }
            
            response = requests.get(
                feed_url, 
                headers=headers, 
                timeout=Config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                self.logger.warning(
                    f"Feed has parsing issues but continuing: {feed_url}"
                )
            
            feed_title = feed.feed.get('title', 'Unknown Feed')
            entries_count = len(feed.entries)
            self.logger.info(
                f"Successfully parsed feed '{feed_title}' with {entries_count} entries"
            )
            
            return feed
            
        except requests.RequestException as e:
            self.logger.error(f"Network error fetching feed {feed_url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing feed {feed_url}: {e}")
            return None
    
    def is_entry_recent(self, entry) -> Tuple[bool, Optional[datetime]]:
        """Check if an entry was published within the recent time window"""
        cutoff_time = Config.get_cutoff_time()
        
        # Try to get published date
        published_date = None
        
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published_date = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        if not published_date and hasattr(entry, 'published'):
            try:
                published_date = date_parser.parse(entry.published)
                # Remove timezone info for comparison if present
                if published_date.tzinfo:
                    published_date = published_date.replace(tzinfo=None)
            except (ValueError, TypeError):
                pass
        
        if (not published_date and 
            hasattr(entry, 'updated_parsed') and 
            entry.updated_parsed):
            try:
                published_date = datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        if not published_date:
            # If no date found, assume it's not recent
            entry_title = entry.get('title', 'Unknown')
            self.logger.warning(
                f"No published date found for entry: {entry_title}"
            )
            return False, None
        
        is_recent = published_date > cutoff_time
        return is_recent, published_date
    
    def clean_html_content(self, content: str) -> str:
        """Clean and process HTML content"""
        if not content:
            return ""
        
        try:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove problematic elements
            for element in soup(['script', 'style', 'iframe', 'object', 'embed']):
                element.decompose()
            
            # Clean up attributes that might cause issues
            for tag in soup.find_all(True):
                # Keep only safe attributes
                safe_attrs = ['href', 'src', 'alt', 'title', 'class', 'id']
                tag.attrs = {
                    k: v for k, v in tag.attrs.items() 
                    if k in safe_attrs
                }
            
            # Convert relative URLs to absolute ones (basic approach)
            # Note: This is simplified - you might want to enhance based on feed base URL
            
            return str(soup)
            
        except Exception as e:
            self.logger.warning(f"Error cleaning HTML content: {e}")
            return content
    
    def extract_entry_data(self, entry, feed_title: str) -> Dict:
        """Extract relevant data from a feed entry"""
        # Get title
        title = entry.get('title', 'Untitled').strip()
        
        # Get content
        content = ""
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value
        elif hasattr(entry, 'summary'):
            content = entry.summary
        elif hasattr(entry, 'description'):
            content = entry.description
        
        # Clean content
        content = self.clean_html_content(content)
        
        # Get metadata
        author = entry.get('author', 'Unknown Author')
        link = entry.get('link', '')
        entry_id = entry.get('id', f"entry_{hash(title)}")
        
        return {
            'entry_title': title,
            'feed_title': feed_title,
            'content': content,
            'author': author,
            'link': link,
            'entry_id': entry_id,
            'generated_date': datetime.now()
        }
    
    def get_pdf_styles(self) -> str:
        """Return CSS styles for PDF generation from external file"""
        try:
            css_path = Path(Config.CSS_FILE)
            if css_path.exists():
                with open(css_path, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                
                # Replace configurable values
                css_content = css_content.replace(
                    '13px', f'{Config.PDF_FONT_SIZE}px'
                )
                css_content = css_content.replace(
                    '400px', f'{Config.MAX_IMAGE_WIDTH}px'
                )
                css_content = css_content.replace('A4', Config.PDF_PAGE_SIZE)
                css_content = css_content.replace('0.375in', Config.PDF_MARGIN)
                
                return css_content
            else:
                self.logger.warning(
                    f"CSS file not found: {css_path}, using fallback styles"
                )
                return self.get_fallback_styles()
        except Exception as e:
            self.logger.error(
                f"Error reading CSS file: {e}, using fallback styles"
            )
            return self.get_fallback_styles()
    
    def get_fallback_styles(self) -> str:
        """Fallback CSS styles if external file is not available"""
        return f"""
        @page {{
            size: {Config.PDF_PAGE_SIZE};
            margin: {Config.PDF_MARGIN};
        }}
        body {{
            font-family: 'Georgia', serif;
            font-size: {Config.PDF_FONT_SIZE}px;
            line-height: 1.5;
            color: #333;
        }}
        h1 {{ font-size: 24px; color: #2c3e50; }}
        .metadata {{ background-color: #f8f9fa; padding: 20px; }}
        .content {{ text-align: justify; }}
        img {{ 
            max-width: {Config.MAX_IMAGE_WIDTH}px; 
            width: 100%; 
            height: auto; 
        }}
        """
    
    def generate_pdf(
        self, 
        entry_data: Dict, 
        published_date: datetime, 
        feed_title: str
    ) -> Tuple[Optional[Path], bool]:
        """Generate PDF from entry data. Returns (path, was_skipped)"""
        try:
            # Load template
            template = self.template_env.get_template(self.template_name)
            
            # Add published date to entry data
            entry_data['published'] = published_date
            
            # Render HTML
            html_content = template.render(**entry_data)
            
            # Create feed subdirectory
            feed_dir = Config.get_feed_directory(feed_title)
            output_feed_path = Path(Config.OUTPUT_DIR) / feed_dir
            output_feed_path.mkdir(exist_ok=True)
            
            # Generate filename (title only)
            base_filename = Config.get_output_filename(
                entry_data['entry_title'],
                feed_title,
                published_date
            )
            
            # Check if file already exists
            output_path = output_feed_path / base_filename
            if output_path.exists():
                self.logger.info(
                    f"PDF already exists, skipping: {feed_dir}/{base_filename}"
                )
                return output_path, True  # Return existing file path and skipped=True
            
            # Use the filename for logging
            self.logger.info(f"Generating PDF: {feed_dir}/{base_filename}")
            
            # Create PDF
            try:
                self.logger.info(f"Creating HTML document...")
                html_doc = HTML(string=html_content)
                self.logger.info(f"Creating CSS document...")
                css_doc = CSS(string=self.get_pdf_styles())
                self.logger.info(f"Writing PDF to {output_path}...")
                html_doc.write_pdf(str(output_path), stylesheets=[css_doc])
            except Exception as pdf_error:
                self.logger.error(f"Detailed PDF error: {pdf_error}")
                self.logger.error(f"Error type: {type(pdf_error)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise pdf_error
            
            self.logger.info(f"PDF generated successfully: {output_path}")
            return output_path, False  # Return new file path and skipped=False
            
        except Exception as e:
            entry_title = entry_data['entry_title']
            self.logger.error(f"Error generating PDF for '{entry_title}': {e}")
            return None, False
    
    def process_feed(self, feed_url: str) -> Tuple[int, List[Path]]:
        """
        Process a single feed and return number of PDFs generated 
        and list of PDF paths
        """
        feed = self.fetch_feed(feed_url)
        if not feed:
            self.stats['feeds_failed'] += 1
            return 0, []
        
        self.stats['feeds_processed'] += 1
        feed_title = feed.feed.get('title', 'Unknown Feed')
        pdfs_generated = 0
        pdf_paths = []
        
        self.stats['entries_found'] += len(feed.entries)
        
        for entry in feed.entries:
            try:
                # Check if entry is recent
                is_recent, published_date = self.is_entry_recent(entry)
                
                if not is_recent:
                    continue
                
                self.stats['entries_recent'] += 1
                
                # Extract entry data
                entry_data = self.extract_entry_data(entry, feed_title)
                
                # Generate PDF
                pdf_path, was_skipped = self.generate_pdf(
                    entry_data, published_date, feed_title
                )
                
                if pdf_path:
                    if was_skipped:
                        self.stats['pdfs_skipped'] += 1
                    else:
                        self.stats['pdfs_generated'] += 1
                    pdfs_generated += 1
                    pdf_paths.append(pdf_path)
                else:
                    self.stats['pdfs_failed'] += 1
                    
            except Exception as e:
                entry_title = entry.get('title', 'Unknown')
                self.logger.error(
                    f"Error processing entry '{entry_title}': {e}"
                )
                self.stats['pdfs_failed'] += 1
                continue
        
        self.logger.info(
            f"Feed '{feed_title}': Generated {pdfs_generated} PDFs from recent entries"
        )
        return pdfs_generated, pdf_paths
    
    def process_all_feeds(self) -> Dict:
        """Process all feeds from feeds.txt and upload to reMarkable Cloud"""
        self.logger.info("=" * 60)
        start_time = datetime.now().strftime(Config.LOG_DATE_FORMAT)
        self.logger.info(f"Starting feed processing run at {start_time}")
        self.logger.info(
            f"Looking for entries published within the last {Config.RECENT_HOURS} hours"
        )
        self.logger.info("=" * 60)
        
        # Reset statistics
        self.stats = {
            'feeds_processed': 0,
            'feeds_failed': 0,
            'entries_found': 0,
            'entries_recent': 0,
            'pdfs_generated': 0,
            'pdfs_skipped': 0,
            'pdfs_failed': 0,
            'remarkable_uploaded': 0,
            'remarkable_skipped': 0,
            'remarkable_failed': 0
        }
        
        feeds = self.load_feeds()
        if not feeds:
            self.logger.error("No feeds to process")
            return self.stats

        generated_pdfs = []  # Track all generated PDFs for reMarkable upload
        total_pdfs = 0

        for feed_url in feeds:
            try:
                pdfs_count, feed_pdfs = self.process_feed(feed_url)
                total_pdfs += pdfs_count
                generated_pdfs.extend(feed_pdfs)
            except Exception as e:
                self.logger.error(
                    f"Unexpected error processing feed {feed_url}: {e}"
                )
                self.stats['feeds_failed'] += 1
                continue

        # Upload to reMarkable Cloud (core functionality)
        if generated_pdfs:
            self.logger.info(
                f"Uploading {len(generated_pdfs)} PDFs to reMarkable Cloud..."
            )
            upload_results = self.remarkable_uploader.upload_pdfs(generated_pdfs)
            self.stats['remarkable_uploaded'] = upload_results['uploaded']
            self.stats['remarkable_skipped'] = upload_results['skipped']
            self.stats['remarkable_failed'] = upload_results['failed']
        
        # Log final statistics
        self.logger.info("=" * 60)
        self.logger.info("PROCESSING SUMMARY:")
        self.logger.info(f"  Feeds processed: {self.stats['feeds_processed']}")
        self.logger.info(f"  Feeds failed: {self.stats['feeds_failed']}")
        self.logger.info(f"  Total entries found: {self.stats['entries_found']}")
        self.logger.info(f"  Recent entries: {self.stats['entries_recent']}")
        self.logger.info(f"  PDFs generated: {self.stats['pdfs_generated']}")
        self.logger.info(f"  PDFs skipped: {self.stats['pdfs_skipped']}")
        self.logger.info(f"  PDFs failed: {self.stats['pdfs_failed']}")
        self.logger.info(f"  reMarkable uploaded: {self.stats['remarkable_uploaded']}")
        self.logger.info(f"  reMarkable skipped: {self.stats['remarkable_skipped']}")
        self.logger.info(f"  reMarkable failed: {self.stats['remarkable_failed']}")
        self.logger.info("=" * 60)
        
        return self.stats

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Process Atom feeds and generate PDFs for reMarkable Cloud'
    )
    parser.add_argument('--feeds-file', help='Path to feeds.txt file')
    parser.add_argument('--output-dir', help='Output directory for PDFs')
    parser.add_argument(
        '--recent-hours', 
        type=int, 
        help='Hours to look back for recent entries'
    )
    parser.add_argument(
        '--remarkable-folder', 
        help='reMarkable folder name (default: AtomFeeds)'
    )
    parser.add_argument('--rmapi-path', help='Path to rmapi binary')
    
    args = parser.parse_args()
    
    # Override config with command line arguments
    if args.feeds_file:
        Config.FEEDS_FILE = args.feeds_file
    if args.output_dir:
        Config.OUTPUT_DIR = args.output_dir
    if args.recent_hours:
        Config.RECENT_HOURS = args.recent_hours
    if args.remarkable_folder:
        Config.REMARKABLE_FOLDER = args.remarkable_folder
    if args.rmapi_path:
        Config.RMAPI_PATH = args.rmapi_path
    
    try:
        # Run once and exit
        processor = AtomFeedProcessor()
        stats = processor.process_all_feeds()
        
        # Exit with appropriate code
        if stats['pdfs_failed'] > 0 and stats['pdfs_generated'] == 0:
            sys.exit(1)  # All failed
        elif stats['feeds_failed'] > 0:
            sys.exit(2)  # Some failures
        else:
            sys.exit(0)  # Success
            
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
