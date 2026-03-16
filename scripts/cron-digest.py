#!/usr/bin/env python3
"""
Daily News Digest - Cron Entry Point
Triggered by OpenClaw cron at 8:00 AM Asia/Shanghai

Flow:
1. Fetch articles from all feeds (last 24h)
2. Score and rank articles
3. Post top N to Discord #notifications

Exit codes:
0 - Success
1 - Partial failure (some feeds failed but digest posted)
2 - Critical failure (digest not posted)
"""

import sys
import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetcher import FeedFetcher
from scorer import ArticleScorer
from poster import DiscordPoster
from database import Database

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "news_digest.db"

# Logging setup
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("cron-digest")


async def run_digest(dry_run: bool = False, manual: bool = False):
    """
    Run the full digest pipeline.
    
    Args:
        dry_run: Fetch and score but don't post to Discord
        manual: Triggered manually (not via cron) - skip timing checks
    """
    start_time = datetime.now()
    logger.info(f"=== Daily Digest Started at {start_time} ===")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}, DB: {DB_PATH}")
    
    try:
        # Initialize database
        db = Database(DB_PATH)
        await db.init()
        logger.info("Database initialized")
        
        # Initialize components
        fetcher = FeedFetcher(db)
        scorer = ArticleScorer(db)
        poster = DiscordPoster(db) if not dry_run else None
        
        # 1. Fetch articles from all feeds
        logger.info("Fetching articles from feeds...")
        articles = await fetcher.fetch_all()
        logger.info(f"Fetched {len(articles)} articles")
        
        if not articles:
            logger.warning("No articles fetched - will post 'nothing today' message")
            if not dry_run:
                await poster.post_empty_digest()
            return 0
        
        # 2. Score and rank articles
        logger.info("Scoring articles...")
        scored = await scorer.score_articles(articles)
        top_articles = scored[:10]  # Top N = 10 per SPEC
        logger.info(f"Selected top {len(top_articles)} articles")
        
        # 3. Post to Discord
        if dry_run:
            logger.info("[DRY RUN] Would post to Discord:")
            for art in top_articles:
                logger.info(f"  - {art['score']:.3f} | {art['title'][:60]}...")
            return 0
        
        logger.info("Posting to Discord...")
        await poster.post_digest(top_articles)
        logger.info("Digest posted successfully")
        
        # Log completion
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== Digest completed in {elapsed:.1f}s ===")
        return 0
        
    except Exception as e:
        logger.exception("Critical failure in digest pipeline")
        return 2


def main():
    parser = argparse.ArgumentParser(description="Daily News Digest - Cron Entry Point")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and score but don't post")
    parser.add_argument("--manual", action="store_true", help="Manual trigger (skip cron checks)")
    parser.add_argument("--test", action="store_true", help="Test mode - quick sanity check")
    args = parser.parse_args()
    
    if args.test:
        print("✓ cron-digest.py is executable")
        print(f"✓ Data directory: {DATA_DIR}")
        print(f"✓ Log directory: {LOG_DIR}")
        print(f"✓ Database: {DB_PATH}")
        return 0
    
    return asyncio.run(run_digest(dry_run=args.dry_run, manual=args.manual))


if __name__ == "__main__":
    sys.exit(main())
