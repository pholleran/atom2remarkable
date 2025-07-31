#!/usr/bin/env python3
"""
Comprehensive test script for the Atom feed processor
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from main import AtomFeedProcessor
from config import Config
from remarkable import RemarkableUploader

def test_single_feed():
    """Test processing a single feed"""
    print("Testing single feed processing...")
    
    # Override to test with just one feed
    test_feeds = ["https://realpython.com/atom.xml"]
    
    processor = AtomFeedProcessor()
    
    # Save original feeds file
    original_feeds_file = Config.FEEDS_FILE
    
    try:
        # Create temporary feeds file
        with open('test_feeds.txt', 'w') as f:
            f.write('\n'.join(test_feeds))
        
        Config.FEEDS_FILE = 'test_feeds.txt'
        
        # Process feeds
        stats = processor.process_all_feeds()
        
        print("\nTest Results:")
        print(f"  Feeds processed: {stats['feeds_processed']}")
        print(f"  Recent entries: {stats['entries_recent']}")
        print(f"  PDFs generated: {stats['pdfs_generated']}")
        
        return stats['feeds_processed'] > 0
        
    finally:
        # Restore original config
        Config.FEEDS_FILE = original_feeds_file
        
        # Clean up
        if os.path.exists('test_feeds.txt'):
            os.remove('test_feeds.txt')

def test_recent_filtering():
    """Test the recent entry filtering"""
    processor = AtomFeedProcessor()
    
    # Create a mock entry
    class MockEntry:
        def __init__(self, published_time):
            self.published = published_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
            self.title = "Test Entry"
    
    # Test recent entry (1 hour ago)
    recent_entry = MockEntry(datetime.now() - timedelta(hours=1))
    is_recent, date = processor.is_entry_recent(recent_entry)
    print(f"Entry from 1 hour ago - Recent: {is_recent}")
    
    # Test old entry (48 hours ago)
    old_entry = MockEntry(datetime.now() - timedelta(hours=48))
    is_recent, date = processor.is_entry_recent(old_entry)
    print(f"Entry from 48 hours ago - Recent: {is_recent}")
    
    return not is_recent  # Old entry should not be recent

def test_remarkable_integration():
    """Test reMarkable integration"""
    print("Testing reMarkable integration...")
    
    uploader = RemarkableUploader()
    
    # Test rmapi availability
    print(f"Testing rmapi availability at: {uploader.rmapi_path}")
    available = uploader.check_rmapi_available()
    print(f"rmapi available: {available}")
    
    if not available:
        print("⚠️  rmapi not available. Install and configure rmapi first:")
        print("1. Download rmapi from https://github.com/ddvk/rmapi/releases")
        print("2. Run 'rmapi' to authenticate with reMarkable Cloud")
        return False
    
    # Test folder creation
    print(f"Testing folder creation: {uploader.folder_name}")
    folder_ok = uploader.ensure_folder_exists()
    print(f"Folder setup: {folder_ok}")
    
    # Find existing PDFs
    output_dir = Path(Config.OUTPUT_DIR)
    pdf_files = list(output_dir.glob("**/*.pdf"))
    
    if pdf_files:
        print(f"Found {len(pdf_files)} PDF files that could be uploaded:")
        for pdf in pdf_files[:3]:  # Show first 3
            print(f"  - {pdf}")
    else:
        print("No PDF files found. Generate some PDFs first by running the "
              "main application.")
    
    return available and folder_ok

def test_css_loading():
    """Test CSS file loading"""
    print("Testing CSS file loading...")
    
    processor = AtomFeedProcessor()
    css_content = processor.get_pdf_styles()
    
    if css_content and len(css_content) > 100:  # Basic sanity check
        print("✓ CSS loaded successfully")
        print(f"  CSS content length: {len(css_content)} characters")
        return True
    else:
        print("✗ CSS loading failed or content too short")
        return False

def test_directory_structure():
    """Test directory creation and structure"""
    print("Testing directory structure...")
    
    Config.setup_directories()
    
    required_dirs = [Config.OUTPUT_DIR, Config.LOG_DIR, Config.TEMPLATE_DIR]
    all_exist = True
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✓ Directory exists: {dir_path}")
        else:
            print(f"✗ Directory missing: {dir_path}")
            all_exist = False
    
    # Check for CSS file
    css_path = Path(Config.CSS_FILE)
    if css_path.exists():
        print(f"✓ CSS file exists: {Config.CSS_FILE}")
    else:
        print(f"✗ CSS file missing: {Config.CSS_FILE}")
        all_exist = False
    
    return all_exist

def run_all_tests():
    """Run all tests and return overall success"""
    print("Running Atom Feed Processor Tests")
    print("=" * 50)
    
    tests = [
        ("Directory Structure", test_directory_structure),
        ("CSS Loading", test_css_loading),
        ("Recent Filtering", test_recent_filtering),
        ("reMarkable Integration", test_remarkable_integration),
        ("Single Feed Processing", test_single_feed),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"Result: ✗ ERROR - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    return passed == len(results)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
