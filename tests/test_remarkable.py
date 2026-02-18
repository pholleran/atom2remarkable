"""Tests for RemarkableUploader"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from remarkable import RemarkableUploader


@pytest.fixture
def uploader(mocker):
    mocker.patch("config.Config.RMAPI_PATH", "rmapi")
    mocker.patch("config.Config.REMARKABLE_FOLDER", "AtomFeeds")
    return RemarkableUploader()


class TestCheckRmapiAvailable:
    def test_returns_true_when_rmapi_works(self, uploader, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="v0.0.32", stderr="")
        assert uploader.check_rmapi_available() is True

    def test_returns_false_when_rmapi_fails(self, uploader, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        assert uploader.check_rmapi_available() is False

    def test_returns_false_when_rmapi_not_found(self, uploader, mocker):
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)
        assert uploader.check_rmapi_available() is False

    def test_returns_false_on_timeout(self, uploader, mocker):
        import subprocess
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rmapi", 30))
        assert uploader.check_rmapi_available() is False


class TestGetRemarkableFilePath:
    def test_path_with_subfolder(self, uploader):
        pdf = Path("output/My Feed/07-28-2025 Article.pdf")
        result = uploader.get_remarkable_file_path(pdf, "My Feed")
        assert result == "AtomFeeds/My Feed/07-28-2025 Article"

    def test_path_without_subfolder(self, uploader):
        pdf = Path("output/07-28-2025 Article.pdf")
        result = uploader.get_remarkable_file_path(pdf)
        assert result == "AtomFeeds/07-28-2025 Article"

    def test_strips_pdf_extension(self, uploader):
        pdf = Path("output/My Feed/article.pdf")
        result = uploader.get_remarkable_file_path(pdf, "My Feed")
        assert not result.endswith(".pdf")


class TestFileExistsInRemarkable:
    def test_returns_true_when_file_found(self, uploader, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="AtomFeeds/article")
        assert uploader.file_exists_in_remarkable("AtomFeeds/article") is True

    def test_returns_false_when_file_not_found(self, uploader, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert uploader.file_exists_in_remarkable("AtomFeeds/article") is False

    def test_returns_false_on_empty_output(self, uploader, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert uploader.file_exists_in_remarkable("AtomFeeds/article") is False


class TestUploadPdfs:
    def test_skips_all_when_rmapi_unavailable(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=False)
        pdfs = [Path("output/Feed/article.pdf")]
        result = uploader.upload_pdfs(pdfs)
        assert result == {"uploaded": 0, "failed": 0, "skipped": 1}

    def test_skips_existing_files(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=True)
        pdfs = [Path("output/Feed/article.pdf")]
        result = uploader.upload_pdfs(pdfs)
        assert result["skipped"] == 1
        assert result["uploaded"] == 0

    def test_counts_successful_uploads(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)
        mocker.patch.object(uploader, "upload_pdf", return_value=True)
        pdfs = [Path("output/Feed/article.pdf"), Path("output/Feed/article2.pdf")]
        result = uploader.upload_pdfs(pdfs)
        assert result["uploaded"] == 2
        assert result["failed"] == 0

    def test_counts_failed_uploads(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)
        mocker.patch.object(uploader, "upload_pdf", return_value=False)
        pdfs = [Path("output/Feed/article.pdf")]
        result = uploader.upload_pdfs(pdfs)
        assert result["failed"] == 1
        assert result["uploaded"] == 0
