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

    def test_skips_all_when_folder_creation_fails(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=False)
        pdfs = [Path("output/Feed/article.pdf"), Path("output/Feed/article2.pdf")]
        result = uploader.upload_pdfs(pdfs)
        assert result == {"uploaded": 0, "failed": 0, "skipped": 2}

    def test_extracts_subfolder_from_path(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)

        upload_pdf_mock = mocker.patch.object(uploader, "upload_pdf", return_value=True)
        pdfs = [Path("output/My Feed/article.pdf")]
        uploader.upload_pdfs(pdfs)

        upload_pdf_mock.assert_called_once_with(pdfs[0], "My Feed")

    def test_handles_exception_per_file(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "file_exists_in_remarkable", side_effect=Exception("boom"))
        pdfs = [Path("output/Feed/article.pdf")]
        result = uploader.upload_pdfs(pdfs)
        assert result["failed"] == 1


class TestEnsureFolderExists:
    def test_returns_true_when_folder_found(self, uploader, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="AtomFeeds\n")
        assert uploader.ensure_folder_exists() is True

    def test_creates_folder_when_not_found(self, uploader, mocker):
        find_result = MagicMock(returncode=1, stdout="")
        mkdir_result = MagicMock(returncode=0, stdout="")
        mocker.patch("subprocess.run", side_effect=[find_result, mkdir_result])
        assert uploader.ensure_folder_exists() is True

    def test_returns_true_when_mkdir_says_already_exists(self, uploader, mocker):
        find_result = MagicMock(returncode=1, stdout="")
        mkdir_result = MagicMock(returncode=1, stderr="already exists")
        mocker.patch("subprocess.run", side_effect=[find_result, mkdir_result])
        assert uploader.ensure_folder_exists() is True

    def test_returns_false_when_mkdir_fails(self, uploader, mocker):
        find_result = MagicMock(returncode=1, stdout="")
        mkdir_result = MagicMock(returncode=1, stderr="permission denied")
        mocker.patch("subprocess.run", side_effect=[find_result, mkdir_result])
        assert uploader.ensure_folder_exists() is False

    def test_returns_false_on_timeout(self, uploader, mocker):
        import subprocess
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rmapi", 30))
        assert uploader.ensure_folder_exists() is False


class TestEnsureSubfolderExists:
    def test_returns_true_when_subfolder_found(self, uploader, mocker):
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="AtomFeeds/My Feed\n")
        assert uploader.ensure_subfolder_exists("AtomFeeds/My Feed") is True

    def test_creates_subfolder_when_not_found(self, uploader, mocker):
        find_result = MagicMock(returncode=1, stdout="")
        mkdir_result = MagicMock(returncode=0, stdout="")
        mocker.patch("subprocess.run", side_effect=[find_result, mkdir_result])
        assert uploader.ensure_subfolder_exists("AtomFeeds/My Feed") is True

    def test_returns_false_when_mkdir_fails(self, uploader, mocker):
        find_result = MagicMock(returncode=1, stdout="")
        mkdir_result = MagicMock(returncode=1, stderr="error")
        mocker.patch("subprocess.run", side_effect=[find_result, mkdir_result])
        assert uploader.ensure_subfolder_exists("AtomFeeds/My Feed") is False

    def test_returns_false_on_timeout(self, uploader, mocker):
        import subprocess
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rmapi", 30))
        assert uploader.ensure_subfolder_exists("AtomFeeds/My Feed") is False


class TestUploadPdf:
    def test_skips_when_file_exists(self, uploader, mocker):
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=True)
        result = uploader.upload_pdf(Path("output/Feed/article.pdf"), "Feed")
        assert result is True

    def test_uploads_successfully_with_subfolder(self, uploader, mocker):
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "ensure_subfolder_exists", return_value=True)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0)

        result = uploader.upload_pdf(Path("output/Feed/article.pdf"), "Feed")
        assert result is True

    def test_uploads_successfully_without_subfolder(self, uploader, mocker):
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0)

        result = uploader.upload_pdf(Path("output/article.pdf"))
        assert result is True

    def test_returns_false_when_folder_creation_fails(self, uploader, mocker):
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=False)

        result = uploader.upload_pdf(Path("output/Feed/article.pdf"), "Feed")
        assert result is False

    def test_returns_false_on_upload_failure(self, uploader, mocker):
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "ensure_subfolder_exists", return_value=True)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stderr="upload failed")

        result = uploader.upload_pdf(Path("output/Feed/article.pdf"), "Feed")
        assert result is False

    def test_returns_false_on_timeout(self, uploader, mocker):
        import subprocess
        mocker.patch.object(uploader, "file_exists_in_remarkable", return_value=False)
        mocker.patch.object(uploader, "ensure_folder_exists", return_value=True)
        mocker.patch.object(uploader, "ensure_subfolder_exists", return_value=True)
        mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rmapi", 120))

        result = uploader.upload_pdf(Path("output/Feed/article.pdf"), "Feed")
        assert result is False


class TestListRemarkableFiles:
    def test_returns_file_list_on_success(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="file1\nfile2\n")

        result = uploader.list_remarkable_files()
        assert result == "file1\nfile2\n"

    def test_returns_none_when_rmapi_unavailable(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=False)
        assert uploader.list_remarkable_files() is None

    def test_returns_none_on_failure(self, uploader, mocker):
        mocker.patch.object(uploader, "check_rmapi_available", return_value=True)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        assert uploader.list_remarkable_files() is None
