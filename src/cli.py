#!/usr/bin/env python3
"""News Digest CLI

Core CLI commands for managing the daily news digest.

Usage:
    python -m src.cli fetch          # Fetch all feeds
    python -m src.cli score          # Score and rank articles
    python -m src.cli post           # Post digest to Discord
    python -m src.cli pipeline       # Run full pipeline
    python -m src.cli feeds list     # List all feeds
    python -m src.cli feeds add      # Add a new feed
    python -m src.cli briefs queue   # Show articles needing briefs
    python -m src.cli briefs set     # Set brief for article
    python -m src.cli status         # Show system status
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from .database import (
    init_db, ensure_default_settings, get_stats, list_feeds, add_feed,
    update_feed, delete_feed, get_feed, list_articles_for_review,
    add_brief, delete_brief, get_brief
)
from .fetcher import fetch_all_feeds, import_feeds_from_json
from .scorer import score_and_rank_articles
from .poster import DiscordPoster


def cmd_fetch(args):
    """Fetch articles from all enabled feeds."""
    init_db()
    ensure_default_settings()
    
    print("📡 Fetching feeds...")
    result = asyncio.run(fetch_all_feeds())
    
    print(f"\n✅ Success: {result['success']}/{result['total']} feeds")
    print(f"📰 Articles fetched: {result['articles']}")
    
    if result['failed'] > 0:
        print(f"❌ Failed: {result['failed']} feeds")
        return 1
    return 0


def cmd_score(args):
    """Score and rank unposted articles."""
    init_db()
    ensure_default_settings()
    
    print("🎯 Scoring articles...")
    articles = score_and_rank_articles()
    
    print(f"\n✅ Scored {len(articles)} articles for posting")
    
    if args.verbose:
        print("\nTop articles:")
        for i, article in enumerate(articles[:10], 1):
            title = article.get('title', 'N/A')[:60]
            score = article.get('final', 0)
            source = article.get('source_name', 'Unknown')
            print(f"  {i}. {title}... ({score:.3f}) — {source}")
    
    return 0


def cmd_post(args):
    """Post digest to Discord."""
    init_db()
    ensure_default_settings()
    
    print("📬 Preparing digest...")
    articles = score_and_rank_articles()
    
    if not articles:
        print("⚠️  No articles to post")
        return 0
    
    poster = DiscordPoster()
    
    if args.dry_run:
        prepared = poster.format_and_prepare("Tech News", articles)
        print("\n📋 DRY RUN - Would post:\n")
        print(prepared['content'])
        print(f"\n📊 Articles: {prepared['article_count']}")
        return 0
    
    print(f"📤 Posting {len(articles)} articles to Discord...")
    result = asyncio.run(poster.post_digest("Tech News", articles))
    
    if result['success']:
        print("✅ Posted successfully!")
        return 0
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        return 1


def cmd_pipeline(args):
    """Run full pipeline: fetch → score → post."""
    init_db()
    ensure_default_settings()
    
    print("=" * 50)
    print("🚀 Running Full Pipeline")
    print("=" * 50)
    
    # Fetch
    if not args.skip_fetch:
        print("\n📡 Phase 1: Fetching...")
        result = asyncio.run(fetch_all_feeds())
        print(f"   Fetched: {result['success']}/{result['total']} feeds, {result['articles']} articles")
    
    # Score
    print("\n🎯 Phase 2: Scoring...")
    articles = score_and_rank_articles()
    print(f"   Selected: {len(articles)} articles")
    
    # Post
    if not args.dry_run:
        print("\n📤 Phase 3: Posting...")
        poster = DiscordPoster()
        result = asyncio.run(poster.post_digest("Tech News", articles))
        if result['success']:
            print("   ✅ Posted to Discord")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
            return 1
    else:
        print("\n📋 Phase 3: DRY RUN (not posting)")
        poster = DiscordPoster()
        prepared = poster.format_and_prepare("Tech News", articles)
        print(f"   Would post {prepared['article_count']} articles")
        if args.verbose:
            print("\n   Preview:")
            for line in prepared['content'].split('\n')[:15]:
                print(f"   {line}")
    
    print("\n" + "=" * 50)
    print("✅ Pipeline complete")
    print("=" * 50)
    
    return 0


def cmd_feeds_list(args):
    """List all feeds."""
    init_db()
    
    feeds = list_feeds(enabled_only=args.enabled)
    
    print(f"\n📚 {'Enabled ' if args.enabled else ''}Feeds ({len(feeds)} total)\n")
    print(f"{'ID':<4} {'Name':<25} {'Category':<12} {'Rel':<5} {'Status':<10}")
    print("-" * 70)
    
    for feed in feeds:
        status = "✅" if feed['enabled'] else "❌"
        if feed.get('error_count', 0) > 0:
            status = f"⚠️  ({feed['error_count']})"
        
        print(f"{feed['id']:<4} {feed['name'][:24]:<25} {feed.get('category', 'N/A'):<12} "
              f"{feed.get('reliability', 0.7):<5.2f} {status:<10}")
    
    return 0


def cmd_feeds_add(args):
    """Add a new feed."""
    init_db()
    
    feed_id = add_feed(
        url=args.url,
        name=args.name,
        category=args.category,
        reliability=args.reliability
    )
    
    print(f"✅ Added feed: {args.name} (ID: {feed_id})")
    return 0


def cmd_feeds_remove(args):
    """Remove a feed."""
    init_db()
    
    feed = get_feed(args.id)
    if not feed:
        print(f"❌ Feed {args.id} not found")
        return 1
    
    if delete_feed(args.id):
        print(f"✅ Deleted feed: {feed['name']}")
        return 0
    else:
        print(f"❌ Failed to delete feed {args.id}")
        return 1


def cmd_feeds_disable(args):
    """Disable a feed."""
    init_db()
    
    feed = get_feed(args.id)
    if not feed:
        print(f"❌ Feed {args.id} not found")
        return 1
    
    update_feed(args.id, enabled=False)
    print(f"✅ Disabled feed: {feed['name']}")
    return 0


def cmd_feeds_enable(args):
    """Enable a feed."""
    init_db()
    
    feed = get_feed(args.id)
    if not feed:
        print(f"❌ Feed {args.id} not found")
        return 1
    
    update_feed(args.id, enabled=True)
    print(f"✅ Enabled feed: {feed['name']}")
    return 0


def cmd_feeds_import(args):
    """Import feeds from JSON file."""
    init_db()
    
    path = Path(args.file)
    if not path.exists():
        print(f"❌ File not found: {args.file}")
        return 1
    
    with open(path) as f:
        data = json.load(f)
    
    feeds = data.get('feeds', [])
    imported = import_feeds_from_json(feeds)
    
    print(f"✅ Imported {imported} feeds from {args.file}")
    return 0


def cmd_briefs_queue(args):
    """Show articles needing brief review."""
    init_db()
    
    articles = list_articles_for_review()
    
    if not articles:
        print("\n✅ No articles waiting for review")
        return 0
    
    print(f"\n📝 Articles Needing Briefs ({len(articles)} total)\n")
    print(f"{'ID':<6} {'Status':<10} {'Source':<20} {'Title':<45}")
    print("-" * 85)
    
    for article in articles[:20]:  # Show first 20
        has_brief = "✅ Has brief" if article.get('brief') else "⏳ Needs brief"
        title = article.get('title', 'N/A')[:40]
        source = article.get('source_name', 'Unknown')[:18]
        print(f"{article['id']:<6} {has_brief:<10} {source:<20} {title}...")
    
    if len(articles) > 20:
        print(f"\n... and {len(articles) - 20} more")
    
    return 0


def cmd_briefs_set(args):
    """Set brief for an article."""
    init_db()
    
    # Read brief text - if not provided as argument, use stdin or prompt
    brief_text = args.text
    if not brief_text:
        print(f"Enter brief for article {args.id} (Ctrl+D to finish):")
        brief_text = sys.stdin.read().strip()
    
    if not brief_text:
        print("❌ Brief text cannot be empty")
        return 1
    
    add_brief(args.id, brief_text)
    print(f"✅ Brief set for article {args.id}")
    return 0


def cmd_briefs_get(args):
    """Get brief for an article."""
    init_db()
    
    brief = get_brief(args.id)
    
    if brief:
        print(f"\n📝 Brief for article {args.id}:")
        print(f"  {brief}\n")
    else:
        print(f"⚠️  No brief found for article {args.id}")
    
    return 0


def cmd_briefs_clear(args):
    """Clear brief for an article."""
    init_db()
    
    if delete_brief(args.id):
        print(f"✅ Brief cleared for article {args.id}")
        return 0
    else:
        print(f"⚠️  No brief to clear for article {args.id}")
        return 0


def cmd_status(args):
    """Show system status."""
    init_db()
    ensure_default_settings()
    
    stats = get_stats()
    
    print("\n📊 News Digest Status\n")
    print(f"  Total articles:      {stats['total_articles']}")
    print(f"  Unposted articles:   {stats['unposted_articles']}")
    print(f"  Total feeds:         {stats['total_feeds']}")
    print(f"  Enabled feeds:       {stats['enabled_feeds']}")
    print(f"  Broken feeds:        {stats['broken_feeds']}")
    print(f"  Stale feeds:         {stats['stale_feeds']}")
    print()
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog='news-digest',
        description='Daily News Digest CLI'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch articles from feeds')
    fetch_parser.set_defaults(func=cmd_fetch)
    
    # Score command
    score_parser = subparsers.add_parser('score', help='Score and rank articles')
    score_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output')
    score_parser.set_defaults(func=cmd_score)
    
    # Post command
    post_parser = subparsers.add_parser('post', help='Post digest to Discord')
    post_parser.add_argument('-n', '--dry-run', action='store_true', help='Preview without posting')
    post_parser.set_defaults(func=cmd_post)
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run full pipeline')
    pipeline_parser.add_argument('-n', '--dry-run', action='store_true', help='Preview without posting')
    pipeline_parser.add_argument('--skip-fetch', action='store_true', help='Skip fetch phase')
    pipeline_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output')
    pipeline_parser.set_defaults(func=cmd_pipeline)
    
    # Feeds subcommand
    feeds_parser = subparsers.add_parser('feeds', help='Manage feeds')
    feeds_subparsers = feeds_parser.add_subparsers(dest='feeds_command', help='Feed commands')
    
    # feeds list
    feeds_list_parser = feeds_subparsers.add_parser('list', help='List all feeds')
    feeds_list_parser.add_argument('-e', '--enabled', action='store_true', help='Show only enabled feeds')
    feeds_list_parser.set_defaults(func=cmd_feeds_list)
    
    # feeds add
    feeds_add_parser = feeds_subparsers.add_parser('add', help='Add a new feed')
    feeds_add_parser.add_argument('url', help='Feed URL')
    feeds_add_parser.add_argument('name', help='Feed name')
    feeds_add_parser.add_argument('-c', '--category', default='GENERAL', help='Category')
    feeds_add_parser.add_argument('-r', '--reliability', type=float, default=0.7, help='Reliability score (0-1)')
    feeds_add_parser.set_defaults(func=cmd_feeds_add)
    
    # feeds remove
    feeds_remove_parser = feeds_subparsers.add_parser('remove', help='Remove a feed')
    feeds_remove_parser.add_argument('id', type=int, help='Feed ID')
    feeds_remove_parser.set_defaults(func=cmd_feeds_remove)
    
    # feeds disable
    feeds_disable_parser = feeds_subparsers.add_parser('disable', help='Disable a feed')
    feeds_disable_parser.add_argument('id', type=int, help='Feed ID')
    feeds_disable_parser.set_defaults(func=cmd_feeds_disable)
    
    # feeds enable
    feeds_enable_parser = feeds_subparsers.add_parser('enable', help='Enable a feed')
    feeds_enable_parser.add_argument('id', type=int, help='Feed ID')
    feeds_enable_parser.set_defaults(func=cmd_feeds_enable)
    
    # feeds import
    feeds_import_parser = feeds_subparsers.add_parser('import', help='Import feeds from JSON')
    feeds_import_parser.add_argument('file', help='JSON file path')
    feeds_import_parser.set_defaults(func=cmd_feeds_import)
    
    # Briefs subcommand
    briefs_parser = subparsers.add_parser('briefs', help='Manage article briefs')
    briefs_subparsers = briefs_parser.add_subparsers(dest='briefs_command', help='Brief commands')
    
    # briefs queue
    briefs_queue_parser = briefs_subparsers.add_parser('queue', help='Show articles needing briefs')
    briefs_queue_parser.set_defaults(func=cmd_briefs_queue)
    
    # briefs set
    briefs_set_parser = briefs_subparsers.add_parser('set', help='Set brief for article')
    briefs_set_parser.add_argument('id', type=int, help='Article ID')
    briefs_set_parser.add_argument('text', nargs='?', help='Brief text (or read from stdin)')
    briefs_set_parser.set_defaults(func=cmd_briefs_set)
    
    # briefs get
    briefs_get_parser = briefs_subparsers.add_parser('get', help='Get brief for article')
    briefs_get_parser.add_argument('id', type=int, help='Article ID')
    briefs_get_parser.set_defaults(func=cmd_briefs_get)
    
    # briefs clear
    briefs_clear_parser = briefs_subparsers.add_parser('clear', help='Clear brief for article')
    briefs_clear_parser.add_argument('id', type=int, help='Article ID')
    briefs_clear_parser.set_defaults(func=cmd_briefs_clear)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    status_parser.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'feeds' and not args.feeds_command:
        feeds_parser.print_help()
        return 1
    
    if args.command == 'briefs' and not args.briefs_command:
        briefs_parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
