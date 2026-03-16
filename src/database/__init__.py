"""Database operations for news digest.

SQLite schema per SPEC §6.2:
- articles: fetched articles
- feeds: RSS feed sources  
- settings: application settings
- briefs: curated one-liner briefs
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

DATABASE_PATH = Path(__file__).parent.parent.parent / "data" / "news_digest.db"


@contextmanager
def get_db():
    """Get database connection with row factory."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database with schema."""
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


SCHEMA = """
-- Articles table
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_feed_id INTEGER,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category TEXT,
    is_posted BOOLEAN DEFAULT 0,
    is_duplicate BOOLEAN DEFAULT 0,
    duplicate_of INTEGER,
    FOREIGN KEY (source_feed_id) REFERENCES feeds(id)
);

CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_posted ON articles(is_posted);
CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at);

-- Feeds table
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    reliability REAL DEFAULT 0.7,
    enabled BOOLEAN DEFAULT 1,
    last_fetch TIMESTAMP,
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    last_article_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feeds_enabled ON feeds(enabled);
CREATE INDEX IF NOT EXISTS idx_feeds_category ON feeds(category);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Briefs table (one-liner curated briefs)
CREATE TABLE IF NOT EXISTS briefs (
    id INTEGER PRIMARY KEY,
    article_id INTEGER UNIQUE NOT NULL,
    brief TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_briefs_article ON briefs(article_id);

-- Article scores table (for caching scoring results)
CREATE TABLE IF NOT EXISTS article_scores (
    article_id INTEGER PRIMARY KEY,
    semantic_score REAL,
    recency_score REAL,
    source_score REAL,
    novelty_score REAL,
    final_score REAL,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scores_final ON article_scores(final_score);
"""


# Default settings per SPEC §5.3
DEFAULT_SETTINGS = {
    "post_time": "08:00",
    "timezone": "Asia/Shanghai",
    "max_article_age": "48",  # hours
    "filter_mode": "top_n",  # or "binary"
    "top_n_limit": "10",
    "binary_threshold": "0.6",
    "dedupe_threshold": "0.85",
    "enabled_categories": json.dumps(["tech"]),
    "alert_on_feed_failure": "true",
    "stale_feed_hours": "168",  # 1 week
    "max_feed_errors": "5",
}


def ensure_default_settings():
    """Ensure default settings exist."""
    with get_db() as conn:
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                """INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)""",
                (key, value)
            )
        conn.commit()


def get_setting(key: str) -> Optional[str]:
    """Get a setting value."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else DEFAULT_SETTINGS.get(key)


def set_setting(key: str, value: str):
    """Set a setting value."""
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO settings (key, value, updated_at) 
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (key, value)
        )
        conn.commit()


# Feed operations

def add_feed(url: str, name: str, category: str = "GENERAL", reliability: float = 0.7) -> int:
    """Add a new feed. Returns feed ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO feeds (url, name, category, reliability) 
               VALUES (?, ?, ?, ?)""",
            (url, name, category, reliability)
        )
        conn.commit()
        return cursor.lastrowid


def get_feed(feed_id: int) -> Optional[dict]:
    """Get feed by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM feeds WHERE id = ?", (feed_id,)
        ).fetchone()
        return dict(row) if row else None


def get_feed_by_url(url: str) -> Optional[dict]:
    """Get feed by URL."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM feeds WHERE url = ?", (url,)
        ).fetchone()
        return dict(row) if row else None


def list_feeds(enabled_only: bool = False) -> list[dict]:
    """List all feeds."""
    with get_db() as conn:
        if enabled_only:
            rows = conn.execute(
                "SELECT * FROM feeds WHERE enabled = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM feeds ORDER BY name").fetchall()
        return [dict(row) for row in rows]


def update_feed(feed_id: int, **kwargs) -> bool:
    """Update feed fields."""
    allowed = {"name", "category", "reliability", "enabled", "url"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    
    with get_db() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [feed_id]
        conn.execute(f"UPDATE feeds SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True


def delete_feed(feed_id: int) -> bool:
    """Delete a feed."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
        conn.commit()
        return cursor.rowcount > 0


def record_feed_error(feed_id: int, error: str):
    """Record a fetch error for a feed."""
    with get_db() as conn:
        conn.execute(
            """UPDATE feeds 
               SET error_count = error_count + 1, 
                   last_error = ?,
                   enabled = CASE WHEN error_count >= ? THEN 0 ELSE enabled END
               WHERE id = ?""",
            (error, int(get_setting("max_feed_errors") or 5), feed_id)
        )
        conn.commit()


def record_feed_success(feed_id: int):
    """Record successful feed fetch."""
    with get_db() as conn:
        conn.execute(
            """UPDATE feeds 
               SET last_fetch = CURRENT_TIMESTAMP,
                   error_count = 0,
                   last_error = NULL
               WHERE id = ?""",
            (feed_id,)
        )
        conn.commit()


def update_feed_last_article(feed_id: int, article_time: datetime):
    """Update when feed last had an article."""
    with get_db() as conn:
        conn.execute(
            """UPDATE feeds SET last_article_at = ? WHERE id = ?""",
            (article_time.isoformat(), feed_id)
        )
        conn.commit()


# Article operations

def add_article(url: str, title: str, source_name: str, source_feed_id: int,
                published_at: Optional[datetime] = None, category: Optional[str] = None) -> int:
    """Add a new article. Returns article ID."""
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """INSERT INTO articles (url, title, source_name, source_feed_id, 
                                        published_at, category)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (url, title, source_name, source_feed_id,
                 published_at.isoformat() if published_at else None, category)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # URL already exists
            row = conn.execute(
                "SELECT id FROM articles WHERE url = ?", (url,)
            ).fetchone()
            return row["id"] if row else 0


def get_article(article_id: int) -> Optional[dict]:
    """Get article by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return dict(row) if row else None


def get_article_by_url(url: str) -> Optional[dict]:
    """Get article by URL."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE url = ?", (url,)
        ).fetchone()
        return dict(row) if row else None


def list_unposted_articles(max_age_hours: int = 48) -> list[dict]:
    """List unposted articles within age limit."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM articles 
               WHERE is_posted = 0 
               AND is_duplicate = 0
               AND (published_at > datetime('now', ?) OR published_at IS NULL)
               ORDER BY published_at DESC""",
            (f"-{max_age_hours} hours",)
        ).fetchall()
        return [dict(row) for row in rows]


def list_articles_for_review(limit: int = 50, category: Optional[str] = None) -> list[dict]:
    """List articles needing brief review (last 24h, unposted)."""
    with get_db() as conn:
        query = """SELECT a.*, b.brief FROM articles a
                   LEFT JOIN briefs b ON a.id = b.article_id
                   WHERE a.is_posted = 0 
                   AND a.is_duplicate = 0
                   AND (a.published_at > datetime('now', '-24 hours') OR a.published_at IS NULL)"""
        params = []
        
        if category:
            query += " AND a.category = ?"
            params.append(category)
        
        query += " ORDER BY a.published_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def mark_article_posted(article_id: int):
    """Mark article as posted."""
    with get_db() as conn:
        conn.execute(
            "UPDATE articles SET is_posted = 1 WHERE id = ?",
            (article_id,)
        )
        conn.commit()


def mark_article_duplicate(article_id: int, duplicate_of: int):
    """Mark article as duplicate."""
    with get_db() as conn:
        conn.execute(
            "UPDATE articles SET is_duplicate = 1, duplicate_of = ? WHERE id = ?",
            (duplicate_of, article_id)
        )
        conn.commit()


# Brief operations

def add_brief(article_id: int, brief: str) -> int:
    """Add or update a brief for an article."""
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO briefs (article_id, brief, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (article_id, brief)
        )
        conn.commit()
        cursor = conn.execute(
            "SELECT id FROM briefs WHERE article_id = ?", (article_id,)
        )
        return cursor.fetchone()["id"]


def get_brief(article_id: int) -> Optional[str]:
    """Get brief for an article."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT brief FROM briefs WHERE article_id = ?", (article_id,)
        ).fetchone()
        return row["brief"] if row else None


def delete_brief(article_id: int) -> bool:
    """Delete a brief."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM briefs WHERE article_id = ?", (article_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


# Score operations

def save_score(article_id: int, semantic: float, recency: float, 
               source: float, novelty: float, final_score: float):
    """Save calculated scores for an article."""
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO article_scores 
               (article_id, semantic_score, recency_score, source_score, 
                novelty_score, final_score, scored_at)
               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (article_id, semantic, recency, source, novelty, final_score)
        )
        conn.commit()


def get_top_articles(limit: int = 10, min_score: float = 0.4) -> list[dict]:
    """Get top-scored articles."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.*, s.final_score, b.brief 
               FROM articles a
               JOIN article_scores s ON a.id = s.article_id
               LEFT JOIN briefs b ON a.id = b.article_id
               WHERE a.is_posted = 0 
               AND a.is_duplicate = 0
               AND s.final_score >= ?
               ORDER BY s.final_score DESC
               LIMIT ?""",
            (min_score, limit)
        ).fetchall()
        return [dict(row) for row in rows]


# Statistics

def get_stats() -> dict:
    """Get database statistics."""
    with get_db() as conn:
        stats = {}
        
        # Total articles
        row = conn.execute("SELECT COUNT(*) as count FROM articles").fetchone()
        stats["total_articles"] = row["count"]
        
        # Unposted articles
        row = conn.execute(
            "SELECT COUNT(*) as count FROM articles WHERE is_posted = 0"
        ).fetchone()
        stats["unposted_articles"] = row["count"]
        
        # Total feeds
        row = conn.execute("SELECT COUNT(*) as count FROM feeds").fetchone()
        stats["total_feeds"] = row["count"]
        
        # Enabled feeds
        row = conn.execute(
            "SELECT COUNT(*) as count FROM feeds WHERE enabled = 1"
        ).fetchone()
        stats["enabled_feeds"] = row["count"]
        
        # Broken feeds (error_count > 0)
        row = conn.execute(
            "SELECT COUNT(*) as count FROM feeds WHERE error_count > 0"
        ).fetchone()
        stats["broken_feeds"] = row["count"]
        
        # Stale feeds (no articles in stale_feed_hours)
        stale_hours = int(get_setting("stale_feed_hours") or 168)
        row = conn.execute(
            """SELECT COUNT(*) as count FROM feeds 
               WHERE last_article_at < datetime('now', ?) 
               OR last_article_at IS NULL""",
            (f"-{stale_hours} hours",)
        ).fetchone()
        stats["stale_feeds"] = row["count"]
        
        return stats


# Initialize on import
if __name__ == "__main__":
    init_db()
    ensure_default_settings()
    print("Database initialized successfully")
