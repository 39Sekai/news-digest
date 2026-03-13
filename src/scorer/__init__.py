"""Article Scoring Engine

4-factor weighted scoring per SPEC §10:
- Semantic (relevance): 0.6
- Recency: 0.2  
- Source trust: 0.1
- Novelty (diversity): 0.1
"""

import math
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from ..database import (
    list_unposted_articles, save_score, get_top_articles,
    get_setting, mark_article_duplicate
)


# Weights per SPEC §10
WEIGHTS = {
    "semantic": 0.6,
    "recency": 0.2,
    "source": 0.1,
    "novelty": 0.1
}

# Recency half-life: 24 hours per SPEC §10
RECENCY_HALF_LIFE_HOURS = 24

# Novelty threshold per SPEC §10
NOVELTY_THRESHOLD = 0.85

# Minimum final score to include
MIN_SCORE = 0.4


class ArticleScorer:
    """4-factor article scorer."""
    
    def __init__(self):
        self.source_scores: dict[str, float] = {}
        self._load_source_scores()
    
    def _load_source_scores(self):
        """Load source trust scores."""
        # Default source scores per SPEC §10
        self.source_scores = {
            "reuters": 1.0,
            "bbc": 1.0,
            "associated press": 1.0,
            "ap news": 1.0,
            "techcrunch": 0.9,
            "the verge": 0.9,
            "arstechnica": 0.9,
            "ars technica": 0.9,
            "hackernews": 0.85,
            "hacker news": 0.85,
            "github": 0.9,
            "rust blog": 0.9,
            "kubernetes.io": 0.9,
            "medium": 0.6,
            "dev.to": 0.7,
        }
    
    def calculate_recency_score(self, published_at: Optional[datetime]) -> float:
        """Calculate recency score with exponential decay.
        
        Formula: exp(-0.693 * age_hours / 24)
        New articles = 1.0, 24h old = 0.5, 48h old = 0.25
        """
        if not published_at:
            return 0.5  # Neutral if no date
        
        # Ensure timezone-aware
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        age_hours = (now - published_at).total_seconds() / 3600
        
        if age_hours < 0:
            return 1.0  # Future-dated, treat as fresh
        
        # Exponential decay: exp(-0.693 * age / half_life)
        score = math.exp(-0.693 * age_hours / RECENCY_HALF_LIFE_HOURS)
        return max(0.0, min(1.0, score))
    
    def calculate_source_score(self, source_name: str, reliability: float = 0.7) -> float:
        """Calculate source trust score."""
        source_lower = source_name.lower()
        
        # Check known sources
        for known, score in self.source_scores.items():
            if known in source_lower:
                return score
        
        # Fall back to feed reliability
        return max(0.4, min(1.0, reliability))
    
    def calculate_novelty_score(self, article: dict, selected_articles: list[dict]) -> float:
        """Calculate novelty score using MMR approach.
        
        Penalize similarity to already selected articles.
        """
        if not selected_articles:
            return 1.0
        
        # Simple title-based similarity
        title = article.get("title", "").lower()
        max_sim = 0.0
        
        for selected in selected_articles:
            selected_title = selected.get("title", "").lower()
            sim = self._title_similarity(title, selected_title)
            max_sim = max(max_sim, sim)
        
        # Formula: 1.0 - max(0, (max_sim - 0.85) / 0.15)
        if max_sim <= NOVELTY_THRESHOLD:
            return 1.0
        
        novelty = 1.0 - (max_sim - NOVELTY_THRESHOLD) / (1.0 - NOVELTY_THRESHOLD)
        return max(0.0, min(1.0, novelty))
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple title similarity."""
        # Token-based Jaccard similarity
        tokens1 = set(title1.split())
        tokens2 = set(title2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_semantic_score(self, article: dict) -> float:
        """Calculate semantic relevance score.
        
        Placeholder for embedding-based similarity.
        For now, uses simple keyword matching against interests.
        """
        # TODO: Implement with sentence-transformers
        # For now, return neutral score
        return 0.7
    
    def score_article(self, article: dict, selected_articles: list[dict] = None) -> dict:
        """Calculate all scores for an article."""
        if selected_articles is None:
            selected_articles = []
        
        # Calculate individual scores
        semantic = self.calculate_semantic_score(article)
        
        published_at = article.get("published_at")
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except:
                published_at = None
        recency = self.calculate_recency_score(published_at)
        
        source = self.calculate_source_score(
            article.get("source_name", ""),
            article.get("reliability", 0.7)
        )
        
        novelty = self.calculate_novelty_score(article, selected_articles)
        
        # Calculate final weighted score
        final = (
            WEIGHTS["semantic"] * semantic +
            WEIGHTS["recency"] * recency +
            WEIGHTS["source"] * source +
            WEIGHTS["novelty"] * novelty
        )
        
        return {
            "article_id": article["id"],
            "semantic": round(semantic, 4),
            "recency": round(recency, 4),
            "source": round(source, 4),
            "novelty": round(novelty, 4),
            "final": round(final, 4)
        }
    
    def score_and_rank(self, max_age_hours: int = 48) -> list[dict]:
        """Score all unposted articles and return top N.
        
        Per SPEC §10:
        1. Sort by final_score descending
        2. Keep only items with final_score > 0.4
        3. Return top 10
        """
        articles = list_unposted_articles(max_age_hours=max_age_hours)
        
        if not articles:
            return []
        
        # Score all articles
        scored = []
        for article in articles:
            scores = self.score_article(article)
            
            # Save to database
            save_score(
                article["id"],
                scores["semantic"],
                scores["recency"],
                scores["source"],
                scores["novelty"],
                scores["final"]
            )
            
            scored.append({**article, **scores})
        
        # Sort by final score descending
        scored.sort(key=lambda x: x["final"], reverse=True)
        
        # Apply MMR for diversity in top selection
        selected = []
        for article in scored:
            if article["final"] < MIN_SCORE:
                continue
            
            # Recalculate novelty against selected
            if selected:
                novelty = self.calculate_novelty_score(article, selected)
                article["novelty"] = round(novelty, 4)
                # Recalculate final
                article["final"] = round(
                    WEIGHTS["semantic"] * article["semantic"] +
                    WEIGHTS["recency"] * article["recency"] +
                    WEIGHTS["source"] * article["source"] +
                    WEIGHTS["novelty"] * article["novelty"],
                    4
                )
                
                if article["final"] < MIN_SCORE:
                    continue
            
            selected.append(article)
        
        # Get limit from settings
        filter_mode = get_setting("filter_mode") or "top_n"
        if filter_mode == "top_n":
            limit = int(get_setting("top_n_limit") or 10)
        else:
            threshold = float(get_setting("binary_threshold") or 0.6)
            selected = [s for s in selected if s["final"] >= threshold]
            limit = len(selected)
        
        return selected[:limit]
    
    def deduplicate(self, articles: list[dict]) -> list[dict]:
        """Mark duplicates based on title similarity."""
        threshold = float(get_setting("dedupe_threshold") or 0.85)
        
        unique = []
        for article in articles:
            is_dup = False
            for existing in unique:
                sim = self._title_similarity(
                    article.get("title", ""),
                    existing.get("title", "")
                )
                if sim >= threshold:
                    is_dup = True
                    mark_article_duplicate(article["id"], existing["id"])
                    break
            
            if not is_dup:
                unique.append(article)
        
        return unique


def score_and_rank_articles() -> list[dict]:
    """Convenience function: score and rank all unposted articles."""
    scorer = ArticleScorer()
    return scorer.score_and_rank()


def get_final_selection() -> list[dict]:
    """Get final article selection for posting."""
    return get_top_articles()


# For testing
if __name__ == "__main__":
    scorer = ArticleScorer()
    
    # Test recency scoring
    print("Recency tests:")
    print(f"  Fresh (now): {scorer.calculate_recency_score(datetime.now(timezone.utc)):.3f}")
    print(f"  24h old: {scorer.calculate_recency_score(datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour-24)):.3f}")
    
    # Test source scoring
    print("\nSource tests:")
    print(f"  TechCrunch: {scorer.calculate_source_score('TechCrunch'):.3f}")
    print(f"  Unknown: {scorer.calculate_source_score('Random Blog'):.3f}")
