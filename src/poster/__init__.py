"""Discord Poster

Text-only Discord message posting per SPEC §2.2
Posts to #notifications channel
"""

import os
from datetime import datetime
from typing import Optional

# Discord channel ID from SPEC §2.1
DEFAULT_CHANNEL_ID = "1475330217215004904"


class DiscordPoster:
    """Poster for text-only Discord messages."""
    
    def __init__(self, channel_id: Optional[str] = None):
        self.channel_id = channel_id or os.getenv(
            "DISCORD_NOTIFICATIONS_CHANNEL", 
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
        """Post message to Discord channel.
        
        Uses message tool for delivery.
        Returns result dict with status.
        """
        # This will be called from the main pipeline
        # The actual posting happens via OpenClaw message tool
        return {
            "channel_id": self.channel_id,
            "content": content,
            "status": "ready"
        }
    
    def format_and_prepare(self, category: str, articles: list[dict]) -> dict:
        """Format and prepare message for posting."""
        content = self.format_message(category, articles)
        return {
            "channel_id": self.channel_id,
            "content": content,
            "article_count": len(articles),
            "article_ids": [a["id"] for a in articles]
        }


def post_digest(articles: list[dict], category: str = "Tech News") -> dict:
    """Post a digest to Discord.
    
    Args:
        articles: List of article dicts with brief, title, source_name
        category: Category name for header
    
    Returns:
        Result dict with posting info
    """
    poster = DiscordPoster()
    return poster.format_and_prepare(category, articles)


def post_empty_day(category: str = "Tech News") -> dict:
    """Post empty day message."""
    poster = DiscordPoster()
    return poster.format_and_prepare(category, [])


# For testing
if __name__ == "__main__":
    poster = DiscordPoster()
    
    # Test formatting
    test_articles = [
        {"title": "OpenAI launches GPT-5", "source_name": "TechCrunch", "brief": "OpenAI launches GPT-5 with multimodal reasoning"},
        {"title": "Rust 1.85 released", "source_name": "Rust Blog", "brief": "Rust 1.85 adds async traits natively"},
    ]
    
    print(poster.format_message("Tech News", test_articles))
    print("\n" + "="*50 + "\n")
    print(poster.format_message("Tech News", []))
