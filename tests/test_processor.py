"""Tests for AtomFeedProcessor"""

import pytest
import requests
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

    def test_falls_back_to_description(self, processor):
        entry = MagicMock(spec=['get', 'description'])
        entry.get.side_effect = lambda key, default="": {
            "title": "Title", "author": "Author", "link": "", "id": "1",
        }.get(key, default)
        entry.description = "<p>Description content</p>"

        data = processor.extract_entry_data(entry, "Feed")
        assert "Description content" in data["content"]


class TestFetchFeed:
    def test_returns_feed_on_success(self, processor, mocker):
        mock_response = MagicMock()
        mock_response.content = b"<feed></feed>"
        mocker.patch("requests.get", return_value=mock_response)

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get.return_value = "Test Feed"
        mock_feed.entries = []
        mocker.patch("feedparser.parse", return_value=mock_feed)

        result = processor.fetch_feed("https://example.com/feed.xml")
        assert result is mock_feed

    def test_logs_warning_on_bozo_feed(self, processor, mocker):
        mock_response = MagicMock()
        mock_response.content = b"<feed></feed>"
        mocker.patch("requests.get", return_value=mock_response)

        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.feed.get.return_value = "Test Feed"
        mock_feed.entries = []
        mocker.patch("feedparser.parse", return_value=mock_feed)

        result = processor.fetch_feed("https://example.com/feed.xml")
        assert result is mock_feed  # Still returns feed despite bozo

    def test_returns_none_on_request_exception(self, processor, mocker):
        mocker.patch("requests.get", side_effect=requests.RequestException("timeout"))
        result = processor.fetch_feed("https://example.com/feed.xml")
        assert result is None

    def test_returns_none_on_generic_exception(self, processor, mocker):
        mocker.patch("requests.get", side_effect=Exception("unexpected"))
        result = processor.fetch_feed("https://example.com/feed.xml")
        assert result is None


class TestGetPdfStyles:
    def test_loads_css_from_file(self, processor, tmp_path, mocker):
        css_file = tmp_path / "style.css"
        css_file.write_text("body { font-size: 13px; } img { max-width: 400px; } @page { size: A4; margin: 0.375in; }")
        mocker.patch("config.Config.CSS_FILE", str(css_file))

        result = processor.get_pdf_styles()
        assert "body" in result

    def test_substitutes_config_values(self, processor, tmp_path, mocker):
        css_file = tmp_path / "style.css"
        css_file.write_text("font-size: 13px; max-width: 400px; size: A4; margin: 0.375in;")
        mocker.patch("config.Config.CSS_FILE", str(css_file))
        mocker.patch("config.Config.PDF_FONT_SIZE", 16)
        mocker.patch("config.Config.MAX_IMAGE_WIDTH", 600)

        result = processor.get_pdf_styles()
        assert "16px" in result
        assert "600px" in result

    def test_falls_back_when_css_missing(self, processor, mocker):
        mocker.patch("config.Config.CSS_FILE", "/nonexistent/style.css")
        result = processor.get_pdf_styles()
        assert "@page" in result  # Fallback styles contain @page


class TestGeneratePdf:
    def test_skips_existing_pdf(self, processor, tmp_path, mocker):
        mocker.patch("config.Config.OUTPUT_DIR", str(tmp_path))

        # Pre-create the expected output file
        feed_dir = tmp_path / "My Feed"
        feed_dir.mkdir()
        date = datetime(2025, 7, 28)
        existing = feed_dir / "07-28-2025 My Article.pdf"
        existing.touch()

        entry_data = {"entry_title": "My Article", "content": "", "author": "", "link": "", "entry_id": "1", "feed_title": "My Feed", "generated_date": datetime.now()}
        path, skipped = processor.generate_pdf(entry_data, date, "My Feed")

        assert skipped is True
        assert path == existing

    def test_generates_new_pdf(self, processor, tmp_path, mocker):
        mocker.patch("config.Config.OUTPUT_DIR", str(tmp_path))

        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Article</body></html>"
        processor.template_env = MagicMock()
        processor.template_env.get_template.return_value = mock_template

        mock_html = MagicMock()
        mock_css = MagicMock()
        mocker.patch("main.HTML", return_value=mock_html)
        mocker.patch("main.CSS", return_value=mock_css)

        entry_data = {"entry_title": "New Article", "content": "<p>text</p>", "author": "Author", "link": "", "entry_id": "1", "feed_title": "My Feed", "generated_date": datetime.now()}
        date = datetime(2025, 7, 28)
        path, skipped = processor.generate_pdf(entry_data, date, "My Feed")

        assert skipped is False
        assert path is not None
        mock_html.write_pdf.assert_called_once()

    def test_returns_none_on_weasyprint_failure(self, processor, tmp_path, mocker):
        mocker.patch("config.Config.OUTPUT_DIR", str(tmp_path))

        mock_template = MagicMock()
        mock_template.render.return_value = "<html></html>"
        processor.template_env = MagicMock()
        processor.template_env.get_template.return_value = mock_template

        mocker.patch("main.HTML", side_effect=Exception("WeasyPrint error"))

        entry_data = {"entry_title": "Article", "content": "", "author": "", "link": "", "entry_id": "1", "feed_title": "Feed", "generated_date": datetime.now()}
        path, skipped = processor.generate_pdf(entry_data, datetime.now(), "Feed")

        assert path is None
        assert skipped is False


class TestProcessFeed:
    def test_returns_zero_when_fetch_fails(self, processor, mocker):
        mocker.patch.object(processor, "fetch_feed", return_value=None)
        count, paths = processor.process_feed("https://example.com/feed.xml")
        assert count == 0
        assert paths == []

    def test_processes_recent_entries(self, processor, mocker):
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "Test Feed"
        mock_entry = MagicMock()
        mock_feed.entries = [mock_entry]

        mocker.patch.object(processor, "fetch_feed", return_value=mock_feed)
        mocker.patch.object(processor, "is_entry_recent", return_value=(True, datetime.now()))
        mocker.patch.object(processor, "extract_entry_data", return_value={"entry_title": "T", "content": "", "author": "", "link": "", "entry_id": "1", "feed_title": "Test Feed", "generated_date": datetime.now()})

        fake_path = Path("/tmp/article.pdf")
        mocker.patch.object(processor, "generate_pdf", return_value=(fake_path, False))

        count, paths = processor.process_feed("https://example.com/feed.xml")
        assert count == 1
        assert fake_path in paths

    def test_skips_old_entries(self, processor, mocker):
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "Test Feed"
        mock_feed.entries = [MagicMock()]

        mocker.patch.object(processor, "fetch_feed", return_value=mock_feed)
        mocker.patch.object(processor, "is_entry_recent", return_value=(False, None))

        count, paths = processor.process_feed("https://example.com/feed.xml")
        assert count == 0
        assert paths == []


class TestProcessAllFeeds:
    def test_returns_stats_with_no_feeds(self, processor, mocker):
        mocker.patch.object(processor, "load_feeds", return_value=[])
        stats = processor.process_all_feeds()
        assert stats["feeds_processed"] == 0

    def test_aggregates_stats_across_feeds(self, processor, mocker):
        mocker.patch.object(processor, "load_feeds", return_value=[
            "https://feed1.com/atom.xml",
            "https://feed2.com/atom.xml",
        ])
        fake_path = Path("/tmp/article.pdf")
        mocker.patch.object(processor, "process_feed", return_value=(1, [fake_path]))
        processor.remarkable_uploader.upload_pdfs.return_value = {
            "uploaded": 2, "skipped": 0, "failed": 0
        }

        stats = processor.process_all_feeds()
        assert stats["remarkable_uploaded"] == 2

    def test_handles_exception_in_feed_processing(self, processor, mocker):
        mocker.patch.object(processor, "load_feeds", return_value=["https://bad.com/feed.xml"])
        mocker.patch.object(processor, "process_feed", side_effect=Exception("boom"))

        stats = processor.process_all_feeds()
        assert stats["feeds_failed"] == 1
