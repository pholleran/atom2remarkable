"""Tests for Config utility methods"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from config import Config


class TestGetOutputFilename:
    def test_basic_filename(self):
        date = datetime(2025, 7, 28)
        result = Config.get_output_filename("My Article", "Feed", date)
        assert result == "07-28-2025 My Article.pdf"

    def test_strips_special_characters(self):
        date = datetime(2025, 7, 28)
        result = Config.get_output_filename("Article: A & B!", "Feed", date)
        assert result == "07-28-2025 Article A  B.pdf"

    def test_truncates_long_title(self):
        date = datetime(2025, 1, 1)
        long_title = "A" * 100
        result = Config.get_output_filename(long_title, "Feed", date)
        # Title portion should be truncated to 60 chars
        assert len(result) <= len("01-01-2025 ") + 60 + len(".pdf")

    def test_date_format(self):
        date = datetime(2025, 12, 3)
        result = Config.get_output_filename("Title", "Feed", date)
        assert result.startswith("12-03-2025")


class TestGetFeedDirectory:
    def test_basic_name(self):
        result = Config.get_feed_directory("Simon Willison")
        assert result == "Simon Willison"

    def test_strips_special_characters(self):
        result = Config.get_feed_directory("Feed: Name & More!")
        assert result == "Feed Name  More"

    def test_truncates_long_name(self):
        long_name = "A" * 100
        result = Config.get_feed_directory(long_name)
        assert len(result) <= 50

    def test_preserves_hyphens_and_underscores(self):
        result = Config.get_feed_directory("My-Feed_Name")
        assert result == "My-Feed_Name"


class TestGetCutoffTime:
    def test_cutoff_is_in_the_past(self):
        cutoff = Config.get_cutoff_time()
        assert cutoff < datetime.now()

    def test_cutoff_respects_recent_hours(self):
        with patch.object(Config, 'RECENT_HOURS', 48):
            cutoff = Config.get_cutoff_time()
            expected = datetime.now() - timedelta(hours=48)
            # Allow 1 second of tolerance
            assert abs((cutoff - expected).total_seconds()) < 1
