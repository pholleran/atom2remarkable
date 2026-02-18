"""Tests for AtomFeedProcessor"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from main import AtomFeedProcessor


@pytest.fixture
def processor(tmp_path, mocker):
    """Create an AtomFeedProcessor with logging and directories patched to tmp_path."""
    mocker.patch("config.Config.OUTPUT_DIR", str(tmp_path / "output"))
    mocker.patch("config.Config.LOG_DIR", str(tmp_path / "logs"))
    mocker.patch("config.Config.FEEDS_FILE", str(tmp_path / "feeds.txt"))
    mocker.patch("config.Config.setup_directories")
    mocker.patch("main.RemarkableUploader")
    (tmp_path / "logs").mkdir()
    return AtomFeedProcessor()


class TestIsEntryRecent:
    def _make_entry(self, hours_ago):
        """Create a mock feedparser entry published hours_ago hours in the past."""
        pub_time = datetime.now() - timedelta(hours=hours_ago)
        entry = MagicMock()
        entry.published_parsed = pub_time.timetuple()
        entry.published = pub_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        entry.title = "Test Entry"
        return entry

    def test_recent_entry_is_recent(self, processor):
        entry = self._make_entry(1)
        is_recent, date = processor.is_entry_recent(entry)
        assert is_recent is True
        assert date is not None

    def test_old_entry_is_not_recent(self, processor):
        entry = self._make_entry(48)
        is_recent, date = processor.is_entry_recent(entry)
        assert is_recent is False

    def test_entry_at_boundary_is_not_recent(self, processor):
        entry = self._make_entry(25)  # Just outside 24h window
        is_recent, _ = processor.is_entry_recent(entry)
        assert is_recent is False

    def test_entry_with_no_date_returns_false(self, processor):
        entry = MagicMock(spec=['get'])  # No date attributes, but supports .get()
        entry.get.return_value = "No Date Entry"
        is_recent, date = processor.is_entry_recent(entry)
        assert is_recent is False
        assert date is None

    def test_falls_back_to_updated_parsed(self, processor):
        entry = MagicMock(spec=['updated_parsed', 'title'])
        entry.title = "Entry"
        pub_time = datetime.now() - timedelta(hours=1)
        entry.updated_parsed = pub_time.timetuple()
        is_recent, date = processor.is_entry_recent(entry)
        assert is_recent is True


class TestCleanHtmlContent:
    def test_removes_script_tags(self, processor):
        html = "<p>Hello</p><script>alert('xss')</script>"
        result = processor.clean_html_content(html)
        assert "<script>" not in result
        assert "Hello" in result

    def test_removes_iframe_tags(self, processor):
        html = "<p>Content</p><iframe src='evil.com'></iframe>"
        result = processor.clean_html_content(html)
        assert "<iframe>" not in result
        assert "Content" in result

    def test_removes_style_tags(self, processor):
        html = "<p>Text</p><style>body { color: red; }</style>"
        result = processor.clean_html_content(html)
        assert "<style>" not in result

    def test_preserves_safe_content(self, processor):
        html = "<p>Hello <strong>world</strong></p>"
        result = processor.clean_html_content(html)
        assert "Hello" in result
        assert "world" in result

    def test_empty_content_returns_empty(self, processor):
        assert processor.clean_html_content("") == ""
        assert processor.clean_html_content(None) == ""

    def test_strips_unsafe_attributes(self, processor):
        html = '<p onclick="evil()" class="ok">Text</p>'
        result = processor.clean_html_content(html)
        assert "onclick" not in result
        assert 'class="ok"' in result


class TestLoadFeeds:
    def test_loads_valid_feeds(self, processor, tmp_path):
        feeds_file = tmp_path / "feeds.txt"
        feeds_file.write_text(
            "https://example.com/feed1.xml\nhttps://example.com/feed2.xml\n"
        )
        with patch("config.Config.FEEDS_FILE", str(feeds_file)):
            feeds = processor.load_feeds()
        assert feeds == [
            "https://example.com/feed1.xml",
            "https://example.com/feed2.xml",
        ]

    def test_skips_blank_lines_and_comments(self, processor, tmp_path):
        feeds_file = tmp_path / "feeds.txt"
        feeds_file.write_text(
            "https://example.com/feed.xml\n\n# a comment\n"
        )
        with patch("config.Config.FEEDS_FILE", str(feeds_file)):
            feeds = processor.load_feeds()
        assert feeds == ["https://example.com/feed.xml"]

    def test_missing_file_returns_empty(self, processor, tmp_path):
        with patch("config.Config.FEEDS_FILE", str(tmp_path / "nonexistent.txt")):
            feeds = processor.load_feeds()
        assert feeds == []


class TestExtractEntryData:
    def test_extracts_basic_fields(self, processor):
        entry = MagicMock()
        entry.get.side_effect = lambda key, default="": {
            "title": "My Title",
            "author": "Jane Doe",
            "link": "https://example.com/post",
            "id": "entry-123",
        }.get(key, default)
        entry.content = [MagicMock(value="<p>Body</p>")]

        data = processor.extract_entry_data(entry, "My Feed")

        assert data["entry_title"] == "My Title"
        assert data["feed_title"] == "My Feed"
        assert data["author"] == "Jane Doe"
        assert data["link"] == "https://example.com/post"

    def test_falls_back_to_summary(self, processor):
        entry = MagicMock(spec=['get', 'summary'])
        entry.get.side_effect = lambda key, default="": {
            "title": "Title",
            "author": "Author",
            "link": "",
            "id": "1",
        }.get(key, default)
        entry.summary = "<p>Summary content</p>"

        data = processor.extract_entry_data(entry, "Feed")
        assert "Summary content" in data["content"]
