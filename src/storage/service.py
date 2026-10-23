"""Storage service for MinIO S3-compatible storage with automatic local fallback."""
import io
import os
import logging
from datetime import timedelta
from typing import Optional
from minio import Minio
from minio.error import S3Error

from src.config import settings

logger = logging.getLogger(__name__)


class StorageException(Exception):
    """Raised when object storage upload or retrieval fails."""
    code: str = "STORAGE_ERROR"
    retryable: bool = True

    def __init__(self, message: str, code: Optional[str] = None, retryable: Optional[bool] = None):
        super().__init__(message)
        if code:
            self.code = code
        if retryable is not None:
            self.retryable = retryable


class StorageService:
    """Manages audio file storage and generates presigned download links."""

    def __init__(self):
        self.backend = settings.storage_backend
        self.local_dir = os.path.abspath(settings.local_storage_dir)
        os.makedirs(self.local_dir, exist_ok=True)
        self._minio_client: Optional[Minio] = None

        if self.backend == "minio":
            try:
                self._minio_client = Minio(
                    settings.minio_endpoint,
                    access_key=settings.minio_access_key,
                    secret_key=settings.minio_secret_key,
                    secure=settings.minio_secure,
                )
                # Ensure bucket exists
                if not self._minio_client.bucket_exists(settings.minio_bucket):
                    self._minio_client.make_bucket(settings.minio_bucket)
                logger.info("Connected to MinIO bucket '%s'", settings.minio_bucket)
            except Exception as e:
                logger.warning(
                    "Could not connect to MinIO at %s: %s. Falling back to local storage.",
                    settings.minio_endpoint,
                    e,
                )
                self.backend = "local"

    def is_healthy(self) -> bool:
        """Verify storage backend connectivity."""
        if self.backend == "local":
            return os.path.isdir(self.local_dir) and os.access(self.local_dir, os.W_OK)
        elif self._minio_client:
            try:
                return self._minio_client.bucket_exists(settings.minio_bucket)
            except Exception:
                return False
        return False

    def upload_file(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "audio/wav",
        expires_hours: int = 24,
    ) -> str:
        """Upload raw bytes and return a downloadable URL."""
        if self.backend == "minio" and self._minio_client:
            try:
                stream = io.BytesIO(data)
                self._minio_client.put_object(
                    bucket_name=settings.minio_bucket,
                    object_name=object_name,
                    data=stream,
                    length=len(data),
                    content_type=content_type,
                )
                # Generate presigned download URL
                url = self._minio_client.presigned_get_object(
                    bucket_name=settings.minio_bucket,
                    object_name=object_name,
                    expires=timedelta(hours=expires_hours),
                )
                return url
            except Exception as e:
                logger.warning("MinIO upload failed (%s). Falling back to local storage.", e)

        # Local storage fallback
        dest_path = os.path.join(self.local_dir, object_name)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)

        # Return local download URL
        return f"/api/v1/storage/{object_name}"

    def get_local_file_path(self, object_name: str) -> Optional[str]:
        """Retrieve local file path if stored locally."""
        dest_path = os.path.join(self.local_dir, object_name)
        if os.path.exists(dest_path):
            return dest_path
        return None


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Retrieve or initialize global StorageService."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
