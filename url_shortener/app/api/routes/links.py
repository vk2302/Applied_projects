
# при поддержке chatGPT 5.4 thinking
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_optional_current_user
from app.core.config import settings
from app.models.archived_link import ArchivedLink
from app.models.link import Link
from app.models.project import Project
from app.models.user import User
from app.schemas.link import (
    ArchivedLinkResponse,
    LinkCreate,
    LinkResponse,
    LinkStatsResponse,
    LinkUpdate,
    SearchResponse,
)
from app.services.cache import (
    delete_cached_original_url,
    delete_cached_stats,
    get_cached_original_url,
    get_cached_stats,
    set_cached_original_url,
    set_cached_stats,
)
from app.services.shortener import generate_short_code

router = APIRouter(prefix="/links", tags=["Links"])


def to_link_response(link: Link) -> LinkResponse:
    return LinkResponse(
        short_code=link.short_code,
        short_url=f"{settings.base_url}/{link.short_code}",
        original_url=link.original_url,
        is_custom=link.is_custom,
        created_at=link.created_at,
        updated_at=link.updated_at,
        expires_at=link.expires_at,
        last_accessed_at=link.last_accessed_at,
        click_count=link.click_count,
        owner_id=link.owner_id,
        project_id=link.project_id,
    )


@router.post("/shorten", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def create_short_link(
    payload: LinkCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    if payload.expires_at and payload.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="expires_at must be in the future")

    project_id = payload.project_id
    if project_id is not None:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Only authorized users can attach links to projects")

        project = db.query(Project).filter(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    if payload.custom_alias:
        existing = db.query(Link).filter(Link.short_code == payload.custom_alias).first()
        if existing:
            raise HTTPException(status_code=400, detail="custom_alias is already taken")
        short_code = payload.custom_alias
        is_custom = True
    else:
        short_code = generate_short_code(db, settings.short_code_length)
        is_custom = False

    link = Link(
        original_url=str(payload.original_url),
        short_code=short_code,
        is_custom=is_custom,
        expires_at=payload.expires_at,
        owner_id=current_user.id if current_user else None,
        project_id=project_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    set_cached_original_url(link.short_code, link.original_url)
    return to_link_response(link)


@router.get("/search", response_model=SearchResponse)
def search_by_original_url(
    original_url: str = Query(...),
    db: Session = Depends(get_db),
):
    items = db.query(Link).filter(Link.original_url == original_url).all()
    return SearchResponse(items=[to_link_response(item) for item in items])


@router.get("/expired-history", response_model=list[ArchivedLinkResponse])
def get_expired_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    archived_links = db.query(ArchivedLink).filter(
        ArchivedLink.owner_id == current_user.id
    ).order_by(ArchivedLink.archived_at.desc()).all()

    return [
        ArchivedLinkResponse(
            short_code=item.short_code,
            original_url=item.original_url,
            created_at=item.created_at,
            archived_at=item.archived_at,
            expires_at=item.expires_at,
            last_accessed_at=item.last_accessed_at,
            click_count=item.click_count,
            archive_reason=item.archive_reason,
        )
        for item in archived_links
    ]


@router.get("/{short_code}/stats", response_model=LinkStatsResponse)
def get_link_stats(
    short_code: str,
    db: Session = Depends(get_db),
):
    cached = get_cached_stats(short_code)
    if cached:
        return cached

    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    payload = {
        "short_code": link.short_code,
        "original_url": link.original_url,
        "created_at": link.created_at,
        "click_count": link.click_count,
        "last_accessed_at": link.last_accessed_at,
        "expires_at": link.expires_at,
    }
    set_cached_stats(short_code, payload)
    return payload



@router.put("/{short_code}", response_model=LinkResponse)
def update_link(
    short_code: str,
    payload: LinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can update only your own links")

    if payload.project_id is not None:
        project = db.query(Project).filter(
            Project.id == payload.project_id,
            Project.owner_id == current_user.id,
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        link.project_id = payload.project_id

    if payload.original_url is not None:
        link.original_url = str(payload.original_url)

    if payload.expires_at is not None:
        if payload.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="expires_at must be in the future")
        link.expires_at = payload.expires_at

    link.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(link)

    delete_cached_original_url(short_code)
    delete_cached_stats(short_code)

    return to_link_response(link)


@router.delete("/{short_code}", status_code=status.HTTP_200_OK)
def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can delete only your own links")

    archived = ArchivedLink(
        original_url=link.original_url,
        short_code=link.short_code,
        owner_id=link.owner_id,
        project_id=link.project_id,
        created_at=link.created_at,
        expires_at=link.expires_at,
        last_accessed_at=link.last_accessed_at,
        click_count=link.click_count,
        archive_reason="manual_delete",
    )

    db.add(archived)
    db.delete(link)
    db.commit()

    delete_cached_original_url(short_code)
    delete_cached_stats(short_code)

    return {"message": "Link deleted successfully"}
