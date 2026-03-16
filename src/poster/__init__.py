"""Discord Poster

Text-only Discord message posting per SPEC §2.2
Posts to #notifications channel via webhook
"""

import os
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Discord channel ID from SPEC §2.1
DEFAULT_CHANNEL_ID = "1475330217215004904"


def get_webhook_url() -> Optional[str]:
    """Get Discord webhook URL from environment."""
    return os.getenv("DISCORD_WEBHOOK_URL")


class DiscordPoster:
    """Poster for text-only Discord messages via webhook."""
    
    def __init__(self, webhook_url: Optional[str] = None, channel_id: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.channel_id = channel_id or os.getenv(
            "DISCORD_CHANNEL_ID", 
            DEFAULT_CHANNEL_ID
        )
    
    def format_message(self, category: str, articles: list[dict], date: Optional[datetime] = None) -> str:
        """Format articles into Discord message per SPEC §2.2.
        
        Format:
        ```
        📰 Tech News — March 14, 2026

        • {one-liner brief} — Source Name
        • {one-liner brief} — Source Name

        _Total: N articles from {feed_count} sources_
        ```
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%B %d, %Y")
        
        # Header
        lines = [f"📰 {category} — {date_str}", ""]
        
        if not articles:
            # Empty day handling per SPEC §3.3
            lines.append("No articles matched your interests today.")
        else:
            # Article entries
            for article in articles:
                brief = self._get_brief(article)
                source = article.get("source_name", "Unknown")
                lines.append(f"• {brief} — {source}")
        
        # Footer
        lines.append("")
        feed_count = len(set(a.get("source_name") for a in articles)) if articles else 0
        lines.append(f"_Total: {len(articles)} articles from {feed_count} sources_")
        
        return "\n".join(lines)
    
    def _get_brief(self, article: dict) -> str:
        """Get one-liner brief for article.
        
        Priority:
        1. Curated brief from database
        2. Original title (if no brief)
        """
        # Check for curated brief
        brief = article.get("brief")
        if brief:
            return brief
        
        # Fall back to title
        title = article.get("title", "Untitled")
        return title
    
    async def post_message(self, content: str) -> dict:
        """Post message to Discord via webhook.
        
        Returns result dict with status.
        """
        if not self.webhook_url:
            return {
                "success": False,
                "error": "DISCORD_WEBHOOK_URL not configured"
            }
        
        payload = {
            "content": content,
            "allowed_mentions": {"parse": []}  # Don't allow mentions
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "channel_id": self.channel_id
                }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}",
                "response": e.response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def format_and_prepare(self, category: str, articles: list[dict]) -> dict:
        """Format and prepare message for posting."""
        content = self.format_message(category, articles)
        return {
            "channel_id": self.channel_id,
            "content": content,
            "webhook_url": self.webhook_url,
            "article_count": len(articles),
            "article_ids": [a["id"] for a in articles]
        }
    
    async def post_digest(self, category: str, articles: list[dict]) -> dict:
        """Format and post digest to Discord."""
        prepared = self.format_and_prepare(category, articles)
        result = await self.post_message(prepared["content"])
        return {**prepared, **result}


async def post_digest(articles: list[dict], category: str = "Tech News") -> dict:
    """Post a digest to Discord.
    
    Args:
        articles: List of article dicts with brief, title, source_name
        category: Category name for header
    
    Returns:
        Result dict with posting info
    """
    poster = DiscordPoster()
    return await poster.post_digest(category, articles)


async def post_empty_day(category: str = "Tech News") -> dict:
    """Post empty day message."""
    poster = DiscordPoster()
    return await poster.post_digest(category, [])


# For testing
if __name__ == "__main__":
    import asyncio
    
    poster = DiscordPoster()
    
    # Test formatting
    test_articles = [
        {"id": 1, "title": "OpenAI launches GPT-5", "source_name": "TechCrunch", "brief": "OpenAI launches GPT-5 with multimodal reasoning"},
        {"id": 2, "title": "Rust 1.85 released", "source_name": "Rust Blog", "brief": "Rust 1.85 adds async traits natively"},
    ]
    
    print("Formatted message:")
    print(poster.format_message("Tech News", test_articles))
    print("\n" + "="*50 + "\n")
    print("Empty day:")
    print(poster.format_message("Tech News", []))
    
    # Test webhook if configured
    if poster.webhook_url:
        print("\n" + "="*50 + "\n")
        print("Testing webhook post...")
        result = asyncio.run(poster.post_digest("Tech News", test_articles))
        print(f"Result: {result}")
