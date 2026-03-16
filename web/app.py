"""News Digest Web Application

Unified FastAPI app combining:
- Backend API (Atlas): Database integration, core pipeline
- Web UI (Iris): Templates, static files, HTML pages
"""

from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
import os

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.database import (
    init_db, ensure_default_settings, list_feeds, get_feed, add_feed,
    update_feed, delete_feed, get_setting, set_setting, get_stats,
    list_articles_for_review, add_brief, delete_brief, get_brief
)


# Pydantic models
class FeedCreate(BaseModel):
    url: str
    name: str
    category: str = "GENERAL"
    reliability: float = 0.7


class FeedUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    reliability: Optional[float] = None
    enabled: Optional[bool] = None


class BriefCreate(BaseModel):
    brief: str


class SettingUpdate(BaseModel):
    value: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup."""
    init_db()
    ensure_default_settings()
    yield


app = FastAPI(
    title="News Digest Manager",
    version="2.0.0",
    lifespan=lifespan
)

# Static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# CORS for API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# HTML PAGES (Iris)
# ============================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard with feed health and brief queue."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/feeds", response_class=HTMLResponse)
async def feeds_page(request: Request):
    """Feed management page."""
    return templates.TemplateResponse("feeds.html", {"request": request})


@app.get("/briefs", response_class=HTMLResponse)
async def briefs_page(request: Request):
    """Brief editor / review queue page."""
    return templates.TemplateResponse("briefs.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings management page."""
    return templates.TemplateResponse("settings.html", {"request": request})


# ============================================
# API ENDPOINTS (Atlas + Iris Integration)
# ============================================

# ----- Feed Management -----

@app.get("/api/v1/feeds")
def get_feeds(enabled_only: bool = False, status: Optional[str] = None, category: Optional[str] = None):
    """List all feeds with optional filtering."""
    feeds = list_feeds(enabled_only=enabled_only)
    
    # Apply additional filters
    if status:
        feeds = [f for f in feeds if f.get("status") == status]
    if category:
        feeds = [f for f in feeds if f.get("category") == category]
    
    return {"feeds": feeds, "total": len(feeds)}


@app.post("/api/v1/feeds", status_code=201)
def create_feed(feed: FeedCreate):
    """Add a new feed."""
    try:
        feed_id = add_feed(
            url=feed.url,
            name=feed.name,
            category=feed.category,
            reliability=feed.reliability
        )
        return get_feed(feed_id)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/v1/feeds/form", status_code=201)
async def create_feed_form(url: str = Form(...), name: str = Form(...), category: str = Form("GENERAL")):
    """Add a new feed via form (for HTML UI)."""
    try:
        feed_id = add_feed(url=url, name=name, category=category, reliability=0.7)
        return {"success": True, "feed": get_feed(feed_id)}
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.patch("/api/v1/feeds/{feed_id}")
def patch_feed(feed_id: int, update: FeedUpdate):
    """Update feed fields."""
    feed = get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    updates = {k: v for k, v in update.dict().items() if v is not None}
    if updates:
        update_feed(feed_id, **updates)
    
    return get_feed(feed_id)


@app.put("/api/v1/feeds/{feed_id}")
def update_feed_endpoint(feed_id: int, update: FeedUpdate):
    """Update feed (alias for patch)."""
    return patch_feed(feed_id, update)


@app.delete("/api/v1/feeds/{feed_id}", status_code=204)
def remove_feed(feed_id: int):
    """Delete a feed."""
    if not delete_feed(feed_id):
        raise HTTPException(status_code=404, detail="Feed not found")


@app.post("/api/v1/feeds/{feed_id}/enable")
def enable_feed(feed_id: int):
    """Enable a disabled feed."""
    update_feed(feed_id, enabled=True)
    return {"success": True, "feed_id": feed_id, "enabled": True}


@app.post("/api/v1/feeds/{feed_id}/disable")
def disable_feed(feed_id: int):
    """Disable a feed."""
    update_feed(feed_id, enabled=False)
    return {"success": True, "feed_id": feed_id, "enabled": False}


# ----- Brief Editor -----

@app.get("/api/v1/briefs/queue")
def get_review_queue(limit: int = 50, category: Optional[str] = None):
    """Get articles needing brief review."""
    articles = list_articles_for_review(limit=limit, category=category)
    with_briefs = sum(1 for a in articles if a.get("brief"))
    
    # Calculate time until next post (8am)
    now = datetime.now()
    next_post = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if next_post < now:
        next_post = next_post.replace(day=next_post.day + 1)
    time_until = next_post - now
    time_remaining = f"{time_until.seconds // 3600}h {(time_until.seconds % 3600) // 60}m"
    
    return {
        "articles": articles,
        "total": len(articles),
        "with_briefs": with_briefs,
        "time_until_post": time_remaining
    }


@app.post("/api/v1/briefs/{article_id}")
def create_brief(article_id: int, brief: BriefCreate):
    """Add or update brief for article."""
    add_brief(article_id, brief.brief)
    return {"success": True, "article_id": article_id, "brief": brief.brief, "saved_at": datetime.now().isoformat()}


@app.post("/api/v1/briefs/{article_id}/form")
async def save_brief_form(article_id: int, brief: str = Form(...)):
    """Save a one-liner brief via form (for HTML UI)."""
    add_brief(article_id, brief)
    return {"success": True, "article_id": article_id, "brief": brief, "saved_at": datetime.now().isoformat()}


@app.delete("/api/v1/briefs/{article_id}", status_code=204)
def remove_brief(article_id: int):
    """Delete brief for article."""
    delete_brief(article_id)


@app.post("/api/v1/briefs/{article_id}/skip")
def skip_article(article_id: int):
    """Mark article to skip in today's digest."""
    # TODO: Implement skip logic
    return {"success": True, "article_id": article_id, "skipped": True}


@app.get("/api/v1/briefs/preview")
def preview_digest():
    """Preview how the Discord message will look with current briefs."""
    from src.scorer import score_and_rank_articles
    from src.poster import format_digest
    
    articles = score_and_rank_articles()
    content = format_digest(articles)
    
    return {
        "category": "tech",
        "date": datetime.now().strftime("%B %d, %Y"),
        "content": content,
        "articles": [{"brief": a.get("brief", a.get("title")), "source": a.get("source_name")} for a in articles[:10]],
        "total": len(articles),
        "feed_count": len(list_feeds(enabled_only=True))
    }


# ----- Settings -----

@app.get("/api/v1/settings")
def get_settings():
    """Get all settings."""
    keys = [
        "post_time", "timezone", "max_article_age", "filter_mode",
        "top_n_limit", "binary_threshold", "dedupe_threshold",
        "enabled_categories", "alert_on_feed_failure",
        "stale_feed_hours", "max_feed_errors"
    ]
    return {k: get_setting(k) for k in keys}


@app.put("/api/v1/settings/{key}")
def update_setting(key: str, update: SettingUpdate):
    """Update a setting."""
    set_setting(key, update.value)
    return {"success": True, "key": key, "value": update.value}


@app.put("/api/v1/settings")
async def update_settings_bulk(settings: dict):
    """Update multiple settings at once."""
    for key, value in settings.items():
        set_setting(key, str(value))
    return {"success": True, "settings": settings}


@app.post("/api/v1/settings/reset")
async def reset_settings():
    """Reset settings to defaults."""
    ensure_default_settings()
    return {"success": True, "settings": get_settings()}


# ----- Stats & Health -----

@app.get("/api/v1/stats")
def get_statistics():
    """Get database statistics."""
    return get_stats()


@app.get("/api/v1/health")
async def health_check():
    """System health status."""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }


# ----- Actions -----

@app.post("/api/v1/actions/fetch")
async def trigger_fetch():
    """Manually trigger feed fetch."""
    from src.fetcher import fetch_all_feeds
    result = await fetch_all_feeds()
    return result


@app.get("/api/v1/actions/preview")
def preview_digest_api():
    """Preview today's digest (API version)."""
    from src.scorer import score_and_rank_articles
    from src.poster import format_digest
    
    articles = score_and_rank_articles()
    content = format_digest(articles)
    
    return {
        "content": content,
        "article_count": len(articles),
        "articles": articles[:10]
    }


# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.headers.get("accept", "").startswith("text/html"):
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return JSONResponse({"detail": "Not found"}, status_code=404)


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
