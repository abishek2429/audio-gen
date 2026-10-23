"""Tests for StorageService (local and MinIO)."""
import os
from src.storage import get_storage_service


def test_storage_service_local_upload_and_retrieve():
    """Verify local storage uploads files and produces local download URLs."""
    storage = get_storage_service()
    assert storage.is_healthy() is True

    test_bytes = b"RIFF....WAVEfmt...."
    obj_name = "test_job_123/mix.wav"

    url = storage.upload_file(test_bytes, obj_name, content_type="audio/wav")
    assert obj_name in url

    local_path = storage.get_local_file_path(obj_name)
    assert local_path is not None
    assert os.path.exists(local_path)
    with open(local_path, "rb") as f:
        assert f.read() == test_bytes
