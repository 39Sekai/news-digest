"""FastAPI Web Application

Backend API for web UI per API_CONTRACT.md
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
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
    title="News Digest API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/feeds")
def get_feeds(enabled_only: bool = False):
    """List all feeds."""
    return {"feeds": list_feeds(enabled_only=enabled_only)}


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


@app.delete("/api/v1/feeds/{feed_id}", status_code=204)
def remove_feed(feed_id: int):
    """Delete a feed."""
    if not delete_feed(feed_id):
        raise HTTPException(status_code=404, detail="Feed not found")


@app.get("/api/v1/briefs/queue")
def get_review_queue():
    """Get articles needing brief review."""
    articles = list_articles_for_review()
    with_briefs = sum(1 for a in articles if a.get("brief"))
    
    return {
        "articles": articles,
        "total": len(articles),
        "with_briefs": with_briefs
    }


@app.post("/api/v1/briefs/{article_id}")
def create_brief(article_id: int, brief: BriefCreate):
    """Add or update brief for article."""
    add_brief(article_id, brief.brief)
    return {"article_id": article_id, "brief": brief.brief}


@app.delete("/api/v1/briefs/{article_id}", status_code=204)
def remove_brief(article_id: int):
    """Delete brief for article."""
    delete_brief(article_id)


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
    return {"key": key, "value": update.value}


@app.get("/api/v1/stats")
def get_statistics():
    """Get database statistics."""
    return get_stats()


@app.post("/api/v1/actions/fetch")
async def trigger_fetch():
    """Manually trigger feed fetch."""
    from src.fetcher import fetch_all_feeds
    result = await fetch_all_feeds()
    return result


@app.get("/api/v1/actions/preview")
def preview_digest():
    """Preview today's digest."""
    from src.scorer import score_and_rank_articles
    from src.poster import post_digest
    
    articles = score_and_rank_articles()
    digest = post_digest(articles)
    
    return {
        "content": digest["content"],
        "article_count": digest["article_count"],
        "articles": articles
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
