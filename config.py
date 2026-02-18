import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

class Config:
    # Base directory - use environment variable if available
    APP_ROOT = os.environ.get('APP_ROOT', os.path.dirname(os.path.abspath(__file__)))
    
    # Feed list file with absolute path
    FEEDS_FILE = os.getenv('FEEDS_FILE', os.path.join(APP_ROOT, 'feeds.txt'))
    
    # Output directory for PDFs with absolute path
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', os.path.join(APP_ROOT, 'output'))
    
    # Log directory with absolute path
    LOG_DIR = os.getenv('LOG_DIR', os.path.join(APP_ROOT, 'logs'))
    
    # Time window for recent entries (24 hours)
    RECENT_HOURS = int(os.getenv('RECENT_HOURS', '24'))
    
    # PDF settings
    PDF_PAGE_SIZE = 'A4'
    PDF_MARGIN = '0.375in'  # Reduced by 50% for maximum content space on E-Reader
    
    # E-Reader optimization settings
    MAX_IMAGE_WIDTH = int(os.getenv('MAX_IMAGE_WIDTH', '400'))  # pixels
    PDF_FONT_SIZE = int(os.getenv('PDF_FONT_SIZE', '13'))  # base font size
    
    # Template settings with absolute paths
    TEMPLATE_DIR = os.getenv('TEMPLATE_DIR', os.path.join(APP_ROOT, 'templates'))
    CSS_FILE = os.getenv('CSS_FILE', os.path.join(APP_ROOT, 'templates', 'style.css'))
    
    # Date format for filenames and logs
    DATE_FORMAT = '%Y-%m-%d_%H-%M-%S'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Request settings
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    USER_AGENT = 'atom2remarkable/1.0 (Feed to PDF Converter)'
    
    # reMarkable Cloud settings (core functionality)
    # Folder name in reMarkable
    REMARKABLE_FOLDER = os.getenv('REMARKABLE_FOLDER', 'AtomFeeds')
    RMAPI_PATH = os.getenv('RMAPI_PATH', 'rmapi')  # Path to rmapi binary
    
    @staticmethod
    def get_cutoff_time():
        """Get the cutoff time for recent entries (24 hours ago)"""
        return datetime.now() - timedelta(hours=Config.RECENT_HOURS)
    
    @staticmethod
    def get_output_filename(entry_title, feed_title, published_date):
        """Generate a safe filename for the PDF output"""
        # Format the published date as MM-DD-YYYY
        date_str = published_date.strftime('%m-%d-%Y')
        
        # Clean the entry title for use as filename
        safe_entry_title = "".join(
            c for c in entry_title 
            if c.isalnum() or c in (' ', '-', '_')
        ).strip()
        # Keep spaces instead of replacing with underscores 
        # for reMarkable compatibility
        safe_entry_title = safe_entry_title[:60]  # Reduced to make room for date
        
        return f"{date_str} {safe_entry_title}.pdf"
    
    @staticmethod
    def get_feed_directory(feed_title):
        """Generate a safe directory name for the feed"""
        safe_feed_title = "".join(
            c for c in feed_title 
            if c.isalnum() or c in (' ', '-', '_')
        ).strip()
        # Keep spaces instead of replacing with underscores 
        # for reMarkable compatibility
        safe_feed_title = safe_feed_title[:50]  # Limit length
        
        return safe_feed_title
    
    @staticmethod
    def setup_directories():
        """Create necessary directories"""
        
        # Create directories
        Path(Config.OUTPUT_DIR).mkdir(exist_ok=True)
        Path(Config.LOG_DIR).mkdir(exist_ok=True)
        
        # Verify template directory exists but don't create it
        # as it should be included in the Docker image
        if not os.path.exists(Config.TEMPLATE_DIR):
            print(f"WARNING: Template directory not found at {Config.TEMPLATE_DIR}")
            # Try to locate it
            potential_paths = [
                os.path.join(Config.APP_ROOT, 'templates'),
                '/usr/src/app/templates',
                '/templates'
            ]
            for path in potential_paths:
                if os.path.exists(path):
                    print(f"Found templates at: {path}")
                    Config.TEMPLATE_DIR = path
                    Config.CSS_FILE = os.path.join(path, 'style.css')
                    break
