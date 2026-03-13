"""News Digest Pipeline

Main entry point for daily news digest.
Coordinates: fetch → dedupe → score → post
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from .database import init_db, ensure_default_settings, mark_article_posted, get_stats
from .fetcher import fetch_all_feeds, import_feeds_from_json
from .scorer import score_and_rank_articles
from .poster import post_digest, post_empty_day


async def run_pipeline(
    fetch: bool = True,
    score: bool = True,
    post: bool = True,
    dry_run: bool = False
) -> dict:
    """Run the full news digest pipeline.
    
    Args:
        fetch: Fetch new articles from RSS feeds
        score: Score and rank articles
        post: Post digest to Discord
        dry_run: Don't actually post, just preview
    
    Returns:
        Pipeline result statistics
    """
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fetch": {},
        "score": {},
        "post": {},
        "dry_run": dry_run
    }
    
    # Initialize database
    init_db()
    ensure_default_settings()
    
    # Step 1: Fetch
    if fetch:
        print("📡 Fetching feeds...")
        fetch_stats = await fetch_all_feeds()
        results["fetch"] = fetch_stats
        print(f"   Fetched: {fetch_stats['success']}/{fetch_stats['total']} feeds, {fetch_stats['articles']} articles")
    
    # Step 2: Score and rank
    top_articles = []
    if score:
        print("🎯 Scoring articles...")
        top_articles = score_and_rank_articles()
        results["score"] = {
            "selected": len(top_articles),
            "top_score": top_articles[0]["final"] if top_articles else 0
        }
        print(f"   Selected: {len(top_articles)} articles")
        if top_articles:
            print(f"   Top score: {top_articles[0]['final']:.3f}")
    
    # Step 3: Post
    if post:
        print("📬 Preparing digest...")
        
        if top_articles:
            digest = post_digest(top_articles, category="Tech News")
        else:
            digest = post_empty_day(category="Tech News")
        
        results["post"] = {
            "article_count": digest["article_count"],
            "channel_id": digest["channel_id"]
        }
        
        if dry_run:
            print("   [DRY RUN] Would post:")
            print("   " + "\n   ".join(digest["content"].split("\n")))
        else:
            print(f"   Posting {digest['article_count']} articles to Discord...")
            # Mark articles as posted
            for article_id in digest["article_ids"]:
                mark_article_posted(article_id)
            
            # Store digest for actual posting
            results["post"]["content"] = digest["content"]
        
        print("   Done!")
    
    # Final stats
    results["stats"] = get_stats()
    
    return results


def load_feeds_from_config() -> int:
    """Load feeds from config/feeds.json into database."""
    config_path = Path(__file__).parent.parent / "config" / "feeds.json"
    
    if not config_path.exists():
        print(f"⚠️ Feed config not found: {config_path}")
        return 0
    
    try:
        with open(config_path) as f:
            data = json.load(f)
        
        feeds = data.get("feeds", [])
        imported = import_feeds_from_json(feeds)
        print(f"📥 Imported {imported} feeds from config")
        return imported
    except Exception as e:
        print(f"❌ Error loading feeds: {e}")
        return 0


async def main():
    """CLI entry point."""
    import sys
    
    dry_run = "--dry-run" in sys.argv
    skip_fetch = "--skip-fetch" in sys.argv
    
    # Initialize
    init_db()
    ensure_default_settings()
    
    # Load feeds from config if database is empty
    stats = get_stats()
    if stats["total_feeds"] == 0:
        load_feeds_from_config()
    
    # Run pipeline
    results = await run_pipeline(
        fetch=not skip_fetch,
        score=True,
        post=True,
        dry_run=dry_run
    )
    
    print(f"\n📊 Stats: {results['stats']}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
