from datetime import datetime
from typing import Optional

from pydantic import AnyHttpUrl, BaseModel, Field


class LinkCreate(BaseModel):
    original_url: AnyHttpUrl
    custom_alias: Optional[str] = Field(default=None, min_length=3, max_length=32)
    expires_at: Optional[datetime] = None
    project_id: Optional[int] = None


class LinkUpdate(BaseModel):
    original_url: Optional[AnyHttpUrl] = None
    expires_at: Optional[datetime] = None
    project_id: Optional[int] = None


class LinkResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    is_custom: bool
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    click_count: int
    owner_id: Optional[int]
    project_id: Optional[int]


class LinkStatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int
    last_accessed_at: Optional[datetime]
    expires_at: Optional[datetime]


class SearchResponse(BaseModel):
    items: list[LinkResponse]


class ArchivedLinkResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    archived_at: datetime
    expires_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    click_count: int
    archive_reason: str
