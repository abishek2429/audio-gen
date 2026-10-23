"""Object storage service supporting MinIO and local fallback."""
from src.storage.service import get_storage_service, StorageService, StorageException

__all__ = ["get_storage_service", "StorageService", "StorageException"]
