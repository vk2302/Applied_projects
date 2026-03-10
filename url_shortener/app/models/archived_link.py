# при поддержки chatGPT 5.4 Thinking

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class ArchivedLink(Base):
    __tablename__ = "archived_links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(Text, nullable=False)
    short_code = Column(String(64), nullable=False, index=True)

    owner_id = Column(Integer, nullable=True)
    project_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False)
    archived_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    click_count = Column(Integer, default=0, nullable=False)
    archive_reason = Column(String(50), nullable=False)
