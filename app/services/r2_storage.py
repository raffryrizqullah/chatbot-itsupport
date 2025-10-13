"""
Cloudflare R2 storage service for PDF file management.

This module provides S3-compatible storage operations for Cloudflare R2,
including upload, download, delete, and automatic cleanup of old files.
"""

import logging
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
from io import BytesIO
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.exceptions import StorageError

logger = logging.getLogger(__name__)


class R2StorageService:
    """
    Service for managing PDF files in Cloudflare R2 storage.

    Provides S3-compatible operations for file upload, download, deletion,
    and automatic cleanup of files older than retention period.
    """

    def __init__(self) -> None:
        """Initialize R2 storage client with configuration from settings."""
        try:
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto",  # R2 uses auto region
            )
            self.bucket_name = settings.r2_bucket_name
            self.retention_days = settings.pdf_retention_days
            logger.info(f"R2 storage client initialized for bucket: {self.bucket_name}")
        except Exception as e:
            msg = f"Failed to initialize R2 storage client: {str(e)}"
            logger.error(msg)
            raise StorageError(msg)

    def upload_file(
        self, file_obj: BinaryIO, key: str, content_type: str = "application/pdf"
    ) -> str:
        """
        Upload a file to R2 storage.

        Args:
            file_obj: File-like object to upload.
            key: Storage key (path) for the file.
            content_type: MIME type of the file.

        Returns:
            Storage key of the uploaded file.

        Raises:
            StorageError: If upload fails.
        """
        try:
            # Add metadata with upload timestamp
            metadata = {
                "uploaded_at": datetime.utcnow().isoformat(),
            }

            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": metadata,
                },
            )

            logger.info(f"Successfully uploaded file to R2: {key}")
            return key

        except ClientError as e:
            msg = f"Failed to upload file to R2: {str(e)}"
            logger.error(msg)
            raise StorageError(msg)

    def download_file(self, key: str) -> BytesIO:
        """
        Download a file from R2 storage.

        Args:
            key: Storage key of the file to download.

        Returns:
            BytesIO object containing file contents.

        Raises:
            StorageError: If download fails or file not found.
        """
        try:
            file_obj = BytesIO()
            self.client.download_fileobj(self.bucket_name, key, file_obj)
            file_obj.seek(0)  # Reset to beginning for reading

            logger.info(f"Successfully downloaded file from R2: {key}")
            return file_obj

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                msg = f"File not found in R2: {key}"
            else:
                msg = f"Failed to download file from R2: {str(e)}"
            logger.error(msg)
            raise StorageError(msg)

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from R2 storage.

        Args:
            key: Storage key of the file to delete.

        Returns:
            True if deletion was successful.

        Raises:
            StorageError: If deletion fails.
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Successfully deleted file from R2: {key}")
            return True

        except ClientError as e:
            msg = f"Failed to delete file from R2: {str(e)}"
            logger.error(msg)
            raise StorageError(msg)

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in R2 storage.

        Args:
            key: Storage key of the file to check.

        Returns:
            True if file exists, False otherwise.
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            msg = f"Error checking file existence: {str(e)}"
            logger.error(msg)
            return False

    def delete_old_files(self, retention_days: Optional[int] = None) -> int:
        """
        Delete files older than retention period from R2 storage.

        Args:
            retention_days: Number of days to retain files (uses config default if None).

        Returns:
            Number of files deleted.

        Raises:
            StorageError: If cleanup operation fails.
        """
        retention = retention_days or self.retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=retention)
        deleted_count = 0

        try:
            # List all objects in bucket
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name)

            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    # Check if object is older than retention period
                    last_modified = obj["LastModified"]

                    # Convert to offset-naive for comparison
                    if last_modified.tzinfo is not None:
                        last_modified = last_modified.replace(tzinfo=None)

                    if last_modified < cutoff_date:
                        try:
                            self.delete_file(obj["Key"])
                            deleted_count += 1
                        except StorageError as e:
                            msg = f"Failed to delete old file {obj['Key']}: {e}"
                            logger.error(msg)
                            continue

            logger.info(
                f"Cleanup complete: deleted {deleted_count} files older than {retention} days"
            )
            return deleted_count

        except ClientError as e:
            msg = f"Failed to cleanup old files from R2: {str(e)}"
            logger.error(msg)
            raise StorageError(msg)

    def generate_presigned_url(
        self, key: str, expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary file access.

        Args:
            key: Storage key of the file.
            expiration: URL expiration time in seconds (default: 1 hour).

        Returns:
            Presigned URL string, or None if generation fails.
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            logger.info(f"Generated presigned URL for: {key}")
            return url

        except ClientError as e:
            msg = f"Failed to generate presigned URL: {str(e)}"
            logger.error(msg)
            return None
