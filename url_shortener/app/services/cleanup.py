# при поддержке ChatGPT 5.4 Thinking

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.archived_link import ArchivedLink
from app.models.link import Link
from app.services.cache import delete_cached_original_url, delete_cached_stats


scheduler = BackgroundScheduler(timezone="UTC")


def archive_and_delete_link(db, link: Link, reason: str) -> None:
    archived = ArchivedLink(
        original_url=link.original_url,
        short_code=link.short_code,
        owner_id=link.owner_id,
        project_id=link.project_id,
        created_at=link.created_at,
        expires_at=link.expires_at,
        last_accessed_at=link.last_accessed_at,
        click_count=link.click_count,
        archive_reason=reason,
    )
    db.add(archived)
    delete_cached_original_url(link.short_code)
    delete_cached_stats(link.short_code)
    db.delete(link)


def cleanup_links() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        expired_links = db.query(Link).filter(
            Link.expires_at.isnot(None),
            Link.expires_at <= now,
        ).all()

        for link in expired_links:
            archive_and_delete_link(db, link, "expired")

        cutoff = now - timedelta(days=settings.inactive_delete_days)

        inactive_links = db.query(Link).filter(
            Link.last_accessed_at.isnot(None),
            Link.last_accessed_at < cutoff,
        ).all()

        for link in inactive_links:
            archive_and_delete_link(db, link, "inactive")

        db.commit()
    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(
            cleanup_links,
            "interval",
            minutes=settings.cleanup_interval_minutes,
            id="cleanup_links_job",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
