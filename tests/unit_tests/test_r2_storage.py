"""
Unit tests for R2 storage service.

Tests the Cloudflare R2 storage service functionality including
file upload, download, delete, and cleanup operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from app.services.r2_storage import R2StorageService
from app.core.exceptions import StorageError


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 S3 client."""
    with patch("app.services.r2_storage.boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.mark.unit
class TestR2StorageService:
    """Test suite for R2 storage service."""

    def test_initialization_success(self, mock_boto3_client):
        """Test successful R2 storage service initialization."""
        service = R2StorageService()

        assert service.client is not None
        assert service.bucket_name == "chatbot-pdfs"
        assert service.retention_days == 7

    def test_initialization_failure(self, mock_boto3_client):
        """Test R2 storage service initialization failure."""
        mock_boto3_client.side_effect = Exception("Connection failed")

        with pytest.raises(StorageError, match="Failed to initialize R2 storage client"):
            R2StorageService()

    def test_upload_file_success(self, mock_boto3_client):
        """Test successful file upload to R2."""
        service = R2StorageService()
        file_obj = BytesIO(b"test content")
        key = "test.pdf"

        result = service.upload_file(file_obj, key)

        assert result == key
        mock_boto3_client.upload_fileobj.assert_called_once()

    def test_upload_file_with_custom_content_type(self, mock_boto3_client):
        """Test file upload with custom content type."""
        service = R2StorageService()
        file_obj = BytesIO(b"test content")
        key = "test.pdf"

        service.upload_file(file_obj, key, content_type="application/pdf")

        call_args = mock_boto3_client.upload_fileobj.call_args
        assert call_args[1]["ExtraArgs"]["ContentType"] == "application/pdf"

    def test_upload_file_includes_metadata(self, mock_boto3_client):
        """Test file upload includes upload timestamp in metadata."""
        service = R2StorageService()
        file_obj = BytesIO(b"test content")
        key = "test.pdf"

        service.upload_file(file_obj, key)

        call_args = mock_boto3_client.upload_fileobj.call_args
        metadata = call_args[1]["ExtraArgs"]["Metadata"]
        assert "uploaded_at" in metadata

    def test_upload_file_failure(self, mock_boto3_client):
        """Test file upload failure handling."""
        service = R2StorageService()
        mock_boto3_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Error"}},
            "upload_fileobj",
        )

        file_obj = BytesIO(b"test content")
        key = "test.pdf"

        with pytest.raises(StorageError, match="Failed to upload file to R2"):
            service.upload_file(file_obj, key)

    def test_download_file_success(self, mock_boto3_client):
        """Test successful file download from R2."""
        service = R2StorageService()
        key = "test.pdf"

        mock_boto3_client.download_fileobj.return_value = None

        result = service.download_file(key)

        assert isinstance(result, BytesIO)
        mock_boto3_client.download_fileobj.assert_called_once_with(
            service.bucket_name, key, result
        )

    def test_download_file_not_found(self, mock_boto3_client):
        """Test file download when file not found."""
        service = R2StorageService()
        mock_boto3_client.download_fileobj.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "download_fileobj",
        )

        key = "nonexistent.pdf"

        with pytest.raises(StorageError, match="File not found in R2"):
            service.download_file(key)

    def test_download_file_failure(self, mock_boto3_client):
        """Test file download failure handling."""
        service = R2StorageService()
        mock_boto3_client.download_fileobj.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Error"}},
            "download_fileobj",
        )

        key = "test.pdf"

        with pytest.raises(StorageError, match="Failed to download file from R2"):
            service.download_file(key)

    def test_delete_file_success(self, mock_boto3_client):
        """Test successful file deletion from R2."""
        service = R2StorageService()
        key = "test.pdf"

        result = service.delete_file(key)

        assert result is True
        mock_boto3_client.delete_object.assert_called_once_with(
            Bucket=service.bucket_name, Key=key
        )

    def test_delete_file_failure(self, mock_boto3_client):
        """Test file deletion failure handling."""
        service = R2StorageService()
        mock_boto3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Error"}},
            "delete_object",
        )

        key = "test.pdf"

        with pytest.raises(StorageError, match="Failed to delete file from R2"):
            service.delete_file(key)

    def test_file_exists_true(self, mock_boto3_client):
        """Test file_exists returns True when file exists."""
        service = R2StorageService()
        key = "test.pdf"

        mock_boto3_client.head_object.return_value = {"ContentLength": 1024}

        result = service.file_exists(key)

        assert result is True
        mock_boto3_client.head_object.assert_called_once_with(
            Bucket=service.bucket_name, Key=key
        )

    def test_file_exists_false(self, mock_boto3_client):
        """Test file_exists returns False when file not found."""
        service = R2StorageService()
        mock_boto3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "head_object",
        )

        key = "nonexistent.pdf"

        result = service.file_exists(key)

        assert result is False

    def test_file_exists_error(self, mock_boto3_client):
        """Test file_exists returns False on other errors."""
        service = R2StorageService()
        mock_boto3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Error"}},
            "head_object",
        )

        key = "test.pdf"

        result = service.file_exists(key)

        assert result is False

    def test_delete_old_files_success(self, mock_boto3_client):
        """Test successful cleanup of old files."""
        service = R2StorageService()

        # Mock paginator with old and new files
        old_date = datetime.utcnow() - timedelta(days=10)
        new_date = datetime.utcnow() - timedelta(days=3)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "old_file.pdf", "LastModified": old_date},
                    {"Key": "new_file.pdf", "LastModified": new_date},
                ]
            }
        ]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        deleted_count = service.delete_old_files()

        assert deleted_count == 1
        mock_boto3_client.delete_object.assert_called_once()

    def test_delete_old_files_custom_retention(self, mock_boto3_client):
        """Test cleanup with custom retention period."""
        service = R2StorageService()

        old_date = datetime.utcnow() - timedelta(days=20)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "old_file.pdf", "LastModified": old_date}]}
        ]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        deleted_count = service.delete_old_files(retention_days=15)

        assert deleted_count == 1

    def test_delete_old_files_empty_bucket(self, mock_boto3_client):
        """Test cleanup when bucket is empty."""
        service = R2StorageService()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        deleted_count = service.delete_old_files()

        assert deleted_count == 0

    def test_delete_old_files_failure(self, mock_boto3_client):
        """Test cleanup failure handling."""
        service = R2StorageService()
        mock_boto3_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Error"}},
            "list_objects_v2",
        )

        with pytest.raises(StorageError, match="Failed to cleanup old files from R2"):
            service.delete_old_files()

    def test_delete_old_files_partial_failure(self, mock_boto3_client):
        """Test cleanup continues after individual file deletion failure."""
        service = R2StorageService()

        old_date = datetime.utcnow() - timedelta(days=10)

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "file1.pdf", "LastModified": old_date},
                    {"Key": "file2.pdf", "LastModified": old_date},
                ]
            }
        ]
        mock_boto3_client.get_paginator.return_value = mock_paginator

        # First delete fails, second succeeds
        mock_boto3_client.delete_object.side_effect = [
            ClientError(
                {"Error": {"Code": "500", "Message": "Internal Error"}},
                "delete_object",
            ),
            None,
        ]

        deleted_count = service.delete_old_files()

        assert deleted_count == 1

    def test_generate_presigned_url_success(self, mock_boto3_client):
        """Test successful presigned URL generation."""
        service = R2StorageService()
        key = "test.pdf"
        expected_url = "https://example.com/presigned-url"

        mock_boto3_client.generate_presigned_url.return_value = expected_url

        result = service.generate_presigned_url(key)

        assert result == expected_url
        mock_boto3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": service.bucket_name, "Key": key},
            ExpiresIn=3600,
        )

    def test_generate_presigned_url_custom_expiration(self, mock_boto3_client):
        """Test presigned URL with custom expiration."""
        service = R2StorageService()
        key = "test.pdf"
        expiration = 7200

        service.generate_presigned_url(key, expiration=expiration)

        call_args = mock_boto3_client.generate_presigned_url.call_args
        assert call_args[1]["ExpiresIn"] == expiration

    def test_generate_presigned_url_failure(self, mock_boto3_client):
        """Test presigned URL generation failure."""
        service = R2StorageService()
        mock_boto3_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Error"}},
            "generate_presigned_url",
        )

        key = "test.pdf"

        result = service.generate_presigned_url(key)

        assert result is None
