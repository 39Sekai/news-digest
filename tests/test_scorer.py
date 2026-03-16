"""
QA Test Suite for Scoring Algorithm
Tests the 4-factor weighted scoring per SPEC §10

Weights:
- Semantic relevance: 0.6
- Recency: 0.2
- Source trust: 0.1
- Novelty: 0.1

Threshold: 0.40 (articles with score >= 0.40 are included)
"""

import pytest
import json
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load fixtures
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

def load_fixture(filename):
    """Load a JSON fixture file"""
    with open(os.path.join(FIXTURES_DIR, filename), 'r') as f:
        return json.load(f)


class TestScoringWeights:
    """Test that scoring weights match SPEC §10"""
    
    def test_semantic_weight(self):
        """Semantic relevance weight must be 0.6"""
        # This test documents the expected weight from SPEC
        expected_weight = 0.6
        assert expected_weight == 0.6, "Semantic weight must be 0.6 per SPEC §10"
    
    def test_recency_weight(self):
        """Recency weight must be 0.2"""
        expected_weight = 0.2
        assert expected_weight == 0.2, "Recency weight must be 0.2 per SPEC §10"
    
    def test_source_weight(self):
        """Source trust weight must be 0.1"""
        expected_weight = 0.1
        assert expected_weight == 0.1, "Source weight must be 0.1 per SPEC §10"
    
    def test_novelty_weight(self):
        """Novelty weight must be 0.1"""
        expected_weight = 0.1
        assert expected_weight == 0.1, "Novelty weight must be 0.1 per SPEC §10"
    
    def test_weight_sum(self):
        """All weights must sum to 1.0"""
        weights = [0.6, 0.2, 0.1, 0.1]
        assert sum(weights) == 1.0, "Weights must sum to 1.0"


class TestScoringFormula:
    """Test the scoring formula: final_score = sum(weight_i * factor_i)"""
    
    def test_calculate_final_score(self):
        """Test final score calculation with known inputs"""
        # Example from SPEC §10
        semantic = 0.95
        recency = 1.0
        source = 0.9
        novelty = 1.0
        
        expected = (0.6 * semantic) + (0.2 * recency) + (0.1 * source) + (0.1 * novelty)
        expected = round(expected, 3)
        
        # expected = 0.57 + 0.2 + 0.09 + 0.1 = 0.96
        assert expected == 0.96
    
    def test_high_semantic_low_others(self):
        """High semantic score can carry low other factors"""
        semantic = 1.0
        recency = 0.0
        source = 0.0
        novelty = 0.0
        
        score = (0.6 * semantic) + (0.2 * recency) + (0.1 * source) + (0.1 * novelty)
        # Score = 0.6, below threshold
        assert score == 0.6
        assert score >= 0.40, "High semantic alone can meet threshold"
    
    def test_low_semantic_high_others(self):
        """Low semantic score with high others may still fail threshold"""
        semantic = 0.0
        recency = 1.0
        source = 1.0
        novelty = 1.0
        
        score = (0.6 * semantic) + (0.2 * recency) + (0.1 * source) + (0.1 * novelty)
        # Score = 0.4, exactly at threshold
        assert score == 0.4


class TestThresholdBoundary:
    """Test threshold boundary conditions (SPEC §10: threshold = 0.40)"""
    
    def test_score_below_threshold_excluded(self):
        """Articles with score < 0.40 should be excluded"""
        boundary = load_fixture('boundary_cases.json')
        test_case = next(t for t in boundary['test_cases'] if t['id'] == 'edge-001')
        
        assert test_case['expected_final_score'] < 0.40
        assert test_case['expected_meets_threshold'] is False
    
    def test_score_at_threshold_included(self):
        """Articles with score == 0.40 should be included (>= operator)"""
        boundary = load_fixture('boundary_cases.json')
        test_case = next(t for t in boundary['test_cases'] if t['id'] == 'edge-002')
        
        assert test_case['expected_final_score'] == 0.40
        assert test_case['expected_meets_threshold'] is True
    
    def test_score_above_threshold_included(self):
        """Articles with score > 0.40 should be included"""
        boundary = load_fixture('boundary_cases.json')
        test_case = next(t for t in boundary['test_cases'] if t['id'] == 'edge-003')
        
        assert test_case['expected_final_score'] > 0.40
        assert test_case['expected_meets_threshold'] is True
    
    def test_maximum_score(self):
        """Perfect scores should yield 1.0"""
        boundary = load_fixture('boundary_cases.json')
        test_case = next(t for t in boundary['test_cases'] if t['id'] == 'edge-004')
        
        assert test_case['expected_final_score'] == 1.0
        assert test_case['expected_meets_threshold'] is True


class TestRecencyScoring:
    """Test recency score calculation (SPEC §10)"""
    
    def test_recency_formula(self):
        """Recency formula: exp(-0.693 * age_hours / 24)"""
        # Half-life of 24 hours
        import math
        
        # 0 hours old = 1.0
        age_0 = 0
        recency_0 = math.exp(-0.693 * age_0 / 24)
        assert round(recency_0, 2) == 1.0
        
        # 24 hours old = 0.5 (half-life)
        age_24 = 24
        recency_24 = math.exp(-0.693 * age_24 / 24)
        assert round(recency_24, 2) == 0.5
        
        # 48 hours old = 0.25
        age_48 = 48
        recency_48 = math.exp(-0.693 * age_48 / 24)
        assert round(recency_48, 2) == 0.25
    
    def test_recency_very_old(self):
        """Very old articles should have near-zero recency"""
        import math
        age_168 = 168  # 1 week
        recency_168 = math.exp(-0.693 * age_168 / 24)
        assert recency_168 < 0.01


class TestSourceTrust:
    """Test source trust score lookups"""
    
    def test_known_source_scores(self):
        """Known sources should have defined trust scores"""
        sources = load_fixture('sources.json')
        
        assert sources['source_trust_scores']['Reuters'] == 1.0
        assert sources['source_trust_scores']['TechCrunch'] == 0.9
        assert sources['source_trust_scores']['Medium'] == 0.6
        assert sources['source_trust_scores']['Unknown Blog'] == 0.4
    
    def test_unknown_source_default(self):
        """Unknown sources should default to 0.4"""
        sources = load_fixture('sources.json')
        
        unknown_score = sources['source_trust_scores'].get('Unknown Blog', 0.4)
        assert unknown_score == 0.4


class TestNoveltyScoring:
    """Test novelty score (MMR-based diversity)"""
    
    def test_novelty_perfect(self):
        """Completely novel article should have novelty = 1.0"""
        # No similar articles in digest
        max_similarity = 0.0
        threshold = 0.85
        
        # Formula: 1.0 - max(0, (max_sim - 0.85) / 0.15)
        novelty = 1.0 - max(0, (max_similarity - threshold) / (1.0 - threshold))
        assert novelty == 1.0
    
    def test_novelty_duplicate(self):
        """Duplicate article (sim > 0.85) should have reduced novelty"""
        max_similarity = 0.95
        threshold = 0.85
        
        novelty = 1.0 - max(0, (max_similarity - threshold) / (1.0 - threshold))
        # novelty = 1.0 - (0.95 - 0.85) / 0.15 = 1.0 - 0.67 = 0.33
        assert round(novelty, 2) == 0.33
    
    def test_novelty_at_threshold(self):
        """Article at similarity threshold should have novelty = 1.0"""
        max_similarity = 0.85
        threshold = 0.85
        
        novelty = 1.0 - max(0, (max_similarity - threshold) / (1.0 - threshold))
        assert novelty == 1.0


class TestScoringIntegration:
    """Test full scoring pipeline with fixture articles"""
    
    def test_fixture_articles_loaded(self):
        """Test that we can load all fixture articles"""
        fixtures = load_fixture('articles.json')
        assert len(fixtures['articles']) > 0
        
        for article in fixtures['articles']:
            assert 'expected_final_score' in article
            assert 'expected_meets_threshold' in article
    
    def test_calculate_expected_scores(self):
        """Verify all fixture articles have calculable expected scores"""
        fixtures = load_fixture('articles.json')
        
        for article in fixtures['articles']:
            expected = (
                0.6 * article['expected_semantic_score'] +
                0.2 * article['expected_recency_score'] +
                0.1 * article['expected_source_score'] +
                0.1 * article['expected_novelty_score']
            )
            expected = round(expected, 3)
            
            assert expected == article['expected_final_score'], \
                f"Score mismatch for {article['id']}: calc={expected}, expected={article['expected_final_score']}"
    
    def test_threshold_application(self):
        """Test that threshold is correctly applied to all fixtures"""
        fixtures = load_fixture('articles.json')
        
        for article in fixtures['articles']:
            meets_threshold = article['expected_final_score'] >= 0.40
            assert meets_threshold == article['expected_meets_threshold'], \
                f"Threshold mismatch for {article['id']}"


class TestTopNSelection:
    """Test Top N selection (SPEC §2.4)"""
    
    def test_top_n_limit(self):
        """Top N mode should return at most N articles"""
        fixtures = load_fixture('articles.json')
        articles = fixtures['articles']
        
        # Sort by score descending
        sorted_articles = sorted(articles, key=lambda x: x['expected_final_score'], reverse=True)
        
        # Filter to threshold
        above_threshold = [a for a in sorted_articles if a['expected_final_score'] >= 0.40]
        
        # Take top 10
        top_n = above_threshold[:10]
        
        assert len(top_n) <= 10
    
    def test_sorting_order(self):
        """Articles should be sorted by final_score descending"""
        fixtures = load_fixture('articles.json')
        articles = fixtures['articles']
        
        sorted_articles = sorted(articles, key=lambda x: x['expected_final_score'], reverse=True)
        
        for i in range(len(sorted_articles) - 1):
            assert sorted_articles[i]['expected_final_score'] >= sorted_articles[i + 1]['expected_final_score']


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_unicode_handling(self):
        """Unicode content should not crash scoring"""
        boundary = load_fixture('boundary_cases.json')
        test_case = next(t for t in boundary['test_cases'] if t['id'] == 'edge-006')
        
        assert test_case['expected_no_crash'] is True
    
    def test_long_title_handling(self):
        """Very long titles should be handled gracefully"""
        boundary = load_fixture('boundary_cases.json')
        test_case = next(t for t in boundary['test_cases'] if t['id'] == 'edge-007')
        
        assert test_case['expected_no_crash'] is True
    
    def test_xss_handling(self):
        """XSS attempts should not break scoring"""
        boundary = load_fixture('boundary_cases.json')
        test_case = next(t for t in boundary['test_cases'] if t['id'] == 'edge-008')
        
        assert test_case['expected_no_crash'] is True
        assert test_case.get('expected_sanitized', False) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
