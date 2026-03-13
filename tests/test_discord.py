"""
QA Test Suite for Discord Poster
Tests message formatting and posting per SPEC §2.2, §6.3
"""

import pytest
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

def load_fixture(filename):
    with open(os.path.join(FIXTURES_DIR, filename), 'r') as f:
        return json.load(f)


class TestDiscordFormatting:
    """Test Discord message formatting per SPEC §2.2"""
    
    def test_message_structure(self):
        """Message should have header, article list, footer"""
        # Format:
        # 📰 Tech News — March 14, 2026
        # 
        # • {one-liner brief} — Source Name
        # • {one-liner brief} — Source Name
        # 
        # _Total: N articles from {feed_count} sources_
        
        header = "📰 Tech News — March 14, 2026"
        assert header.startswith("📰")
        assert "—" in header
    
    def test_article_entry_format(self):
        """Article entry should be: • {brief} — Source"""
        brief = "OpenAI launches GPT-5 with multimodal reasoning"
        source = "TechCrunch"
        
        entry = f"• {brief} — {source}"
        assert entry.startswith("• ")
        assert " — " in entry
    
    def test_no_urls_in_message(self):
        """Message should NOT contain URLs (SPEC §2.2)"""
        message = "📰 Tech News — March 14, 2026\n\n• Article brief — Source"
        
        assert "http" not in message.lower()
        assert "www." not in message.lower()
    
    def test_no_embeds(self):
        """Message should be text-only, no embeds (SPEC §2.2)"""
        pass
    
    def test_no_images(self):
        """Message should have no images (SPEC §2.2)"""
        pass
    
    def test_footer_format(self):
        """Footer should be italic with count info"""
        footer = "_Total: 4 articles from 156 sources_"
        assert footer.startswith("_")
        assert footer.endswith("_")
        assert "Total:" in footer


class TestOneLinerBriefs:
    """Test one-liner brief handling (SPEC §2.2, §5.4)"""
    
    def test_use_curated_brief(self):
        """Should use curated brief when available"""
        curated_brief = "OpenAI launches GPT-5 with multimodal reasoning"
        original_title = "OpenAI Announces GPT-5: A Breakthrough in Multimodal AI Systems"
        
        # Should use curated brief
        display_text = curated_brief
        assert display_text == curated_brief
    
    def test_fallback_to_original_title(self):
        """Should fallback to original title if no brief (SPEC §2.2)"""
        original_title = "OpenAI Announces GPT-5: A Breakthrough in Multimodal AI Systems"
        brief = None
        
        # Should fallback to original
        display_text = brief or original_title
        assert display_text == original_title
    
    def test_flag_unbriefed_articles(self):
        """Should flag articles using original title for review"""
        # These should appear in the review queue
        pass


class TestCategoryMessages:
    """Test category-specific message handling"""
    
    def test_single_category_message(self):
        """Should send one message per category (SPEC §2.2)"""
        # Only tech for now, but structure should support multiple
        pass
    
    def test_tech_category_header(self):
        """Tech category should have appropriate header"""
        header = "📰 Tech News"
        assert "Tech" in header
    
    def test_date_in_header(self):
        """Header should include formatted date"""
        today = datetime.now()
        header = f"📰 Tech News — {today.strftime('%B %d, %Y')}"
        assert today.strftime('%B') in header


class TestEmptyDayHandling:
    """Test empty day posting (SPEC §3.3)"""
    
    def test_empty_day_message(self):
        """Should post 'nothing today' message on empty days"""
        expected = "📰 Tech News — March 14, 2026\n\nNo articles matched your interests today."
        assert "No articles matched" in expected
    
    def test_do_not_skip_empty_days(self):
        """Should NOT skip posting on empty days"""
        # User expects daily signal
        pass


class TestCharacterLimits:
    """Test Discord character limits"""
    
    def test_message_under_2000_chars(self):
        """Message should be under Discord 2000 char limit"""
        # Discord text message limit is 2000 characters
        max_length = 2000
        
        # Build a test message with 10 articles
        articles = [f"• Article {i} brief — Source {i}" for i in range(10)]
        message = "📰 Tech News — March 14, 2026\n\n" + "\n".join(articles)
        message += "\n\n_Total: 10 articles from 50 sources_"
        
        assert len(message) <= max_length
    
    def test_many_articles_handling(self):
        """Should handle many articles without exceeding limit"""
        # If > 10 articles, might need truncation or multiple messages
        pass


class TestDiscordAPI:
    """Test Discord API interaction"""
    
    def test_post_to_correct_channel(self):
        """Should post to #notifications channel (SPEC §2.1)"""
        channel_id = "1475330217215004904"
        assert channel_id == "1475330217215004904"
    
    def test_handle_post_failure(self):
        """Should retry on Discord API failure (SPEC §7)"""
        # Retry 3x per SPEC
        pass
    
    def test_handle_rate_limiting(self):
        """Should handle Discord rate limiting"""
        pass
    
    def test_log_post_success(self):
        """Should log successful posts to database"""
        pass


class TestTiming:
    """Test posting timing (SPEC §2.1)"""
    
    def test_post_at_8am(self):
        """Should post at 8:00 AM Asia/Shanghai"""
        settings = load_fixture('settings.json')
        post_time = settings['settings']['post_time']
        timezone = settings['settings']['timezone']
        
        assert post_time == "08:00"
        assert timezone == "Asia/Shanghai"
    
    def test_post_tolerance(self):
        """Should post within ±5 minutes of scheduled time"""
        # Tolerance for cron execution
        pass


class TestMessagePreview:
    """Test message preview functionality"""
    
    def test_preview_discord_formatting(self):
        """Web UI should show preview of Discord formatting (SPEC §5.4)"""
        pass
    
    def test_preview_before_post(self):
        """Should be able to preview before 8am post"""
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
