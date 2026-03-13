"""RSS Feed Fetcher

Async RSS fetching for 413 feeds using feedparser + httpx.
Per SPEC §3.1, §5.2
"""

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import feedparser

from ..database import (
    get_feed, list_feeds, add_article, record_feed_error,
    record_feed_success, update_feed_last_article, get_feed_by_url
)


# HTTP client settings
HTTP_TIMEOUT = 30.0  # seconds per SPEC §5.2
MAX_CONCURRENT = 20  # Max concurrent fetches


class FeedFetcher:
    """Async RSS feed fetcher."""
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "NewsDigestBot/2.0 (Personal News Aggregator)"
            }
        )
        return self
    
    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()
    
    async def fetch_all(self) -> dict:
        """Fetch all enabled feeds. Returns stats."""
        feeds = list_feeds(enabled_only=True)
        stats = {"total": len(feeds), "success": 0, "failed": 0, "articles": 0}
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        async def fetch_with_limit(feed: dict) -> dict:
            async with semaphore:
                return await self.fetch_single(feed)
        
        results = await asyncio.gather(
            *[fetch_with_limit(feed) for feed in feeds],
            return_exceptions=True
        )
        
        for feed, result in zip(feeds, results):
            if isinstance(result, Exception):
                stats["failed"] += 1
                record_feed_error(feed["id"], str(result))
            elif result.get("error"):
                stats["failed"] += 1
                record_feed_error(feed["id"], result["error"])
            else:
                stats["success"] += 1
                stats["articles"] += result.get("article_count", 0)
                record_feed_success(feed["id"])
        
        return stats
    
    async def fetch_single(self, feed: dict) -> dict:
        """Fetch a single feed. Returns result dict."""
        feed_id = feed["id"]
        url = feed["url"]
        
        try:
            # Fetch feed content
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Parse feed
            content = response.content
            parsed = feedparser.parse(content)
            
            if parsed.bozo and parsed.bozo_exception:
                # Parse error but might still have entries
                if not parsed.entries:
                    return {"error": f"Parse error: {parsed.bozo_exception}"}
            
            # Extract source name from feed if not already set
            source_name = feed.get("name") or self._extract_feed_name(parsed, url)
            
            # Process entries
            article_count = 0
            latest_article_time = None
            
            for entry in parsed.entries:
                article = self._parse_entry(entry, feed_id, source_name, feed.get("category"))
                if article:
                    article_id = add_article(**article)
                    if article_id:
                        article_count += 1
                        
                        # Track latest article time
                        if article.get("published_at"):
                            pub_time = article["published_at"]
                            if latest_article_time is None or pub_time > latest_article_time:
                                latest_article_time = pub_time
            
            # Update feed's last article time
            if latest_article_time:
                update_feed_last_article(feed_id, latest_article_time)
            
            return {
                "article_count": article_count,
                "feed_title": parsed.feed.get("title", source_name)
            }
            
        except httpx.TimeoutException:
            return {"error": f"Timeout after {HTTP_TIMEOUT}s"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_feed_name(self, parsed: feedparser.FeedParserDict, url: str) -> str:
        """Extract feed name from parsed feed or URL."""
        # Try feed title
        if hasattr(parsed, "feed") and parsed.feed.get("title"):
            return parsed.feed.title
        
        # Try to extract from URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "")
        return domain.split(".")[0].capitalize()
    
    def _parse_entry(self, entry: feedparser.FeedParserDict, feed_id: int,
                     source_name: str, category: Optional[str]) -> Optional[dict]:
        """Parse a feed entry into article dict."""
        # Get URL
        url = None
        if hasattr(entry, "link"):
            url = entry.link
        elif hasattr(entry, "id") and entry.id.startswith("http"):
            url = entry.id
        
        if not url:
            return None
        
        # Normalize URL
        url = url.strip()
        
        # Get title
        title = entry.get("title", "").strip()
        if not title:
            title = "Untitled"
        
        # Parse published date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime.fromtimestamp(
                    datetime(*entry.published_parsed[:6]).timestamp(),
                    tz=timezone.utc
                )
            except (ValueError, TypeError):
                pass
        
        if not published_at and hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                published_at = datetime.fromtimestamp(
                    datetime(*entry.updated_parsed[:6]).timestamp(),
                    tz=timezone.utc
                )
            except (ValueError, TypeError):
                pass
        
        return {
            "url": url,
            "title": title,
            "source_name": source_name,
            "source_feed_id": feed_id,
            "published_at": published_at,
            "category": category
        }


async def fetch_all_feeds() -> dict:
    """Convenience function: fetch all enabled feeds."""
    async with FeedFetcher() as fetcher:
        return await fetcher.fetch_all()


def import_feeds_from_json(feeds_data: list[dict]) -> int:
    """Import feeds from JSON configuration.
    
    Args:
        feeds_data: List of feed dicts with url, name, category, reliability
    
    Returns:
        Number of feeds imported
    """
    from ..database import add_feed
    
    imported = 0
    for feed in feeds_data:
        url = feed.get("url")
        if not url:
            continue
        
        # Check if already exists
        existing = get_feed_by_url(url)
        if existing:
            continue
        
        try:
            add_feed(
                url=url,
                name=feed.get("name", ""),
                category=feed.get("category", "GENERAL"),
                reliability=float(feed.get("reliability", 0.7))
            )
            imported += 1
        except Exception:
            pass  # Skip duplicates or errors
    
    return imported


# For testing
if __name__ == "__main__":
    # Test fetch
    result = asyncio.run(fetch_all_feeds())
    print(f"Fetch result: {result}")
