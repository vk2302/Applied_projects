
# при помощи ChatGPT 5.4
from datetime import datetime, timezone
import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.routes.auth import router as auth_router
from app.api.routes.links import router as links_router
from app.api.routes.projects import router as projects_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.archived_link import ArchivedLink  # noqa: F401
from app.models.link import Link  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.user import User  # noqa: F401
from app.services.cache import (
    delete_cached_stats,
    get_cached_original_url,
    set_cached_original_url,
)
from app.services.cleanup import start_scheduler, stop_scheduler


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)


def wait_for_db(max_retries: int = 20, delay_seconds: int = 2) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("Database is ready.")
            return
        except OperationalError:
            print(f"Database is not ready yet. Attempt {attempt}/{max_retries}...")
            time.sleep(delay_seconds)

    raise RuntimeError("Database is not available after several retries.")


@app.on_event("startup")
def on_startup():
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(links_router)


@app.get("/{short_code}")
def redirect_short_link(
    short_code: str,
    db: Session = Depends(get_db),
):
    cached_url = get_cached_original_url(short_code)
    link = db.query(Link).filter(Link.short_code == short_code).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    now = datetime.now(timezone.utc)
    if link.expires_at and link.expires_at <= now:
        raise HTTPException(status_code=404, detail="Link has expired")

    link.click_count += 1
    link.last_accessed_at = now
    db.commit()

    delete_cached_stats(short_code)

    original_url = cached_url if cached_url else link.original_url
    set_cached_original_url(short_code, original_url)

    return RedirectResponse(url=original_url, status_code=307)
