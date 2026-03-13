"""
News Digest Web UI - FastAPI Application
Feed management, brief editor, and settings interface.
"""
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from typing import List, Optional
import json
import os
import sys

# Add src to path for database access
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

app = FastAPI(title="News Digest Manager", version="2.0.0")

# Static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'news_digest.db')

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ============================================
# PAGES (HTML Routes)
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
# API ENDPOINTS (JSON Routes)
# ============================================

# ----- Feed Management -----

@app.get("/api/feeds")
async def list_feeds(status: Optional[str] = None, category: Optional[str] = None):
    """
    List all feeds with optional filtering.
    Query params: status (enabled/disabled/broken/stale), category
    """
    # TODO: Integrate with Atlas's database module
    # For now, return mock data structure
    feeds = [
        {
            "id": 1,
            "url": "https://techcrunch.com/feed/",
            "name": "TechCrunch",
            "category": "tech",
            "enabled": True,
            "reliability": 0.9,
            "last_fetch": "2026-03-13T20:30:00",
            "status": "healthy",  # healthy, broken, stale
            "error_count": 0,
            "article_count": 156
        },
        {
            "id": 2,
            "url": "https://example.com/broken-feed",
            "name": "Broken Feed Example",
            "category": "tech", 
            "enabled": True,
            "reliability": 0.4,
            "last_fetch": None,
            "status": "broken",
            "error_count": 5,
            "article_count": 0
        }
    ]
    
    if status:
        feeds = [f for f in feeds if f["status"] == status]
    if category:
        feeds = [f for f in feeds if f["category"] == category]
    
    return {"feeds": feeds, "total": len(feeds)}

@app.post("/api/feeds")
async def add_feed(url: str = Form(...), name: str = Form(...), category: str = Form("tech")):
    """Add a new RSS feed."""
    # TODO: Validate URL, check for duplicates, insert to DB
    return {
        "success": True,
        "feed": {
            "id": 999,
            "url": url,
            "name": name,
            "category": category,
            "enabled": True,
            "status": "healthy"
        }
    }

@app.put("/api/feeds/{feed_id}")
async def update_feed(feed_id: int, name: Optional[str] = None, 
                     category: Optional[str] = None, enabled: Optional[bool] = None):
    """Update feed metadata."""
    return {"success": True, "feed_id": feed_id}

@app.delete("/api/feeds/{feed_id}")
async def delete_feed(feed_id: int):
    """Delete a feed (or disable if articles exist)."""
    return {"success": True, "feed_id": feed_id, "action": "deleted"}

@app.post("/api/feeds/{feed_id}/enable")
async def enable_feed(feed_id: int):
    """Enable a disabled feed."""
    return {"success": True, "feed_id": feed_id, "enabled": True}

@app.post("/api/feeds/{feed_id}/disable")
async def disable_feed(feed_id: int):
    """Disable a feed."""
    return {"success": True, "feed_id": feed_id, "enabled": False}

# ----- Brief Editor -----

@app.get("/api/briefs/queue")
async def get_brief_queue(limit: int = 50, category: Optional[str] = None):
    """
    Get articles needing brief curation.
    This is the 7:30-7:55 AM review queue.
    """
    # TODO: Fetch from database - articles from last 24h without briefs
    queue = [
        {
            "id": 101,
            "url": "https://example.com/article1",
            "original_title": "OpenAI Announces GPT-5 With Revolutionary Multimodal Capabilities",
            "brief": None,  # Null means needs curation
            "source_name": "TechCrunch",
            "category": "tech",
            "published_at": "2026-03-13T18:00:00",
            "score": 0.92,
            "time_remaining": "24m"  # Until 8am post
        },
        {
            "id": 102,
            "url": "https://example.com/article2", 
            "original_title": "Rust Foundation Releases New Security Guidelines for 2026",
            "brief": "Rust Foundation publishes comprehensive security guidelines",
            "source_name": "Rust Blog",
            "category": "tech",
            "published_at": "2026-03-13T16:30:00",
            "score": 0.78,
            "time_remaining": "24m"
        }
    ]
    return {"articles": queue, "total": len(queue), "time_until_post": "24m"}

@app.post("/api/briefs/{article_id}")
async def save_brief(article_id: int, brief: str = Form(...)):
    """Save a one-liner brief for an article."""
    # TODO: Validate brief (not empty, reasonable length), save to DB
    return {
        "success": True,
        "article_id": article_id,
        "brief": brief,
        "saved_at": datetime.now().isoformat()
    }

@app.post("/api/briefs/{article_id}/skip")
async def skip_article(article_id: int):
    """Mark article to skip in today's digest."""
    return {"success": True, "article_id": article_id, "skipped": True}

@app.get("/api/briefs/preview")
async def preview_digest():
    """Preview how the Discord message will look with current briefs."""
    return {
        "category": "tech",
        "date": datetime.now().strftime("%B %d, %Y"),
        "articles": [
            {"brief": "OpenAI launches GPT-5 with multimodal reasoning", "source": "TechCrunch"},
            {"brief": "Rust Foundation publishes security guidelines", "source": "Rust Blog"}
        ],
        "total": 2,
        "feed_count": 156
    }

# ----- Settings -----

DEFAULT_SETTINGS = {
    "post_time": "08:00",
    "timezone": "Asia/Shanghai",
    "max_article_age": 48,  # hours
    "filter_mode": "top_n",  # or "binary"
    "top_n_limit": 10,
    "binary_threshold": 0.6,
    "dedupe_threshold": 0.85,
    "enabled_categories": ["tech"],
    "alert_on_feed_failure": True,
    "stale_feed_hours": 168,  # 1 week
    "max_feed_errors": 5
}

@app.get("/api/settings")
async def get_settings():
    """Get all current settings."""
    # TODO: Load from database
    return DEFAULT_SETTINGS

@app.put("/api/settings")
async def update_settings(settings: dict):
    """Update settings (apply immediately, no restart needed)."""
    # TODO: Validate and save to DB
    return {"success": True, "settings": settings}

@app.post("/api/settings/reset")
async def reset_settings():
    """Reset settings to defaults."""
    return {"success": True, "settings": DEFAULT_SETTINGS}

# ----- Dashboard Stats -----

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    return {
        "feeds": {
            "total": 413,
            "enabled": 410,
            "disabled": 3,
            "broken": 2,
            "stale": 5
        },
        "articles": {
            "today": 47,
            "pending_briefs": 12,
            "curated": 35,
            "skipped": 0
        },
        "last_post": "2026-03-12T08:00:00",
        "next_post": "2026-03-13T08:00:00",
        "time_until_post": "24m"
    }

@app.get("/api/health")
async def health_check():
    """System health status."""
    return {
        "status": "healthy",
        "database": "connected",
        "feeds_checked": "5m ago",
        "last_fetch": "2026-03-13T20:30:00"
    }

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
