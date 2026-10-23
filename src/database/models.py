"""SQLAlchemy ORM models for job tracking and idempotency."""
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MusicJob(Base):
    """Tracks background audio generation jobs and ensures safe idempotency."""
    __tablename__ = "music_jobs"

    id = Column(String(64), primary_key=True)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=True)
    request_hash = Column(String(64), nullable=False)
    prompt = Column(Text, nullable=False)
    duration_s = Column(Float, nullable=False)
    status = Column(String(32), default="queued", index=True, nullable=False)
    progress = Column(Integer, default=0, nullable=False)

    request_json = Column(Text, nullable=False)
    result_urls_json = Column(Text, nullable=True)
    manifest_json = Column(Text, nullable=True)

    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details_json = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def get_result_urls(self) -> Optional[Dict[str, Any]]:
        if self.result_urls_json:
            try:
                return json.loads(self.result_urls_json)
            except Exception:
                return None
        return None

    def get_manifest(self) -> Optional[Dict[str, Any]]:
        if self.manifest_json:
            try:
                return json.loads(self.manifest_json)
            except Exception:
                return None
        return None

    def get_error(self) -> Optional[Dict[str, Any]]:
        if self.error_code:
            details = {}
            if self.error_details_json:
                try:
                    details = json.loads(self.error_details_json)
                except Exception:
                    pass
            return {
                "code": self.error_code,
                "message": self.error_message or "Unknown failure",
                "retryable": False,
                "details": details,
            }
        return None
