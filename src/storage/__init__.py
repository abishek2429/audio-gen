"""Object storage service supporting MinIO and local fallback."""
from src.storage.service import get_storage_service, StorageService

__all__ = ["get_storage_service", "StorageService"]
