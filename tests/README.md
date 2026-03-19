# QA Test Suite for News Digest v2

## Test Coverage

| Module | Test File | Coverage |
|--------|-----------|----------|
| Scorer | `test_scorer.py` | 4-factor scoring, threshold logic, edge cases |
| Fetcher | `test_fetcher.py` | RSS parsing, error handling, deduplication |
| Database | `test_database.py` | CRUD operations, schema validation |
| Discord | `test_discord.py` | Message formatting, posting logic |

## Running Tests

```bash
# Run all tests
cd news-digest
python -m pytest tests/ -v

# Or use the test runner
python tests/run_tests.py

# Run specific module
python tests/run_tests.py --module scorer
python tests/run_tests.py --module fetcher
python tests/run_tests.py --module database
python tests/run_tests.py --module discord
```

## Fixtures

Located in `tests/fixtures/`:

- `articles.json` — 8 test articles with expected scores
- `boundary_cases.json` — Threshold boundary and edge cases
- `feeds.json` — Mock feed sources including error cases
- `settings.json` — Configuration settings
- `sources.json` — Source trust scores

## Production Feeds

Full feed list in `config/feeds.json`:
- **321 RSS feeds** converted from Inoreader OPML export
- Categories: AI, TECH, CS, ROBOTICS, SECURITY, GENERAL, EVENTS, ALERTS, SPACE, UNIVERSITIES, SOCIETY
- Successfully tested: 235 feeds processed, 3129 articles fetched in 44.9s

## Test Categories

### Scorer Tests
- Weight validation (0.6/0.2/0.1/0.1)
- Threshold boundary (0.40)
- Recency formula (exponential decay)
- Source trust lookups
- Novelty scoring (MMR)
- Top N selection

### Fetcher Tests
- RSS/Atom parsing
- HTTP error handling (4xx/5xx)
- Timeout handling (>30s)
- Deduplication (URL + fuzzy 85%)
- Age filtering (48h max)
- Feed health monitoring

### Database Tests
- Schema validation
- Article CRUD
- Feed CRUD
- Settings CRUD
- Briefs storage
- Transaction safety

### Discord Tests
- Message formatting (text-only)
- One-liner brief handling
- Empty day messages
- Character limits (2000)
- Channel targeting

## SPEC References

- §2.2 — Content format, one-liner briefs
- §2.4 — Top N vs Binary filtering
- §3.2 — Deduplication (85% similarity)
- §5.2 — Feed health monitoring
- §5.4 — Brief workflow
- §6.2 — Database schema
- §10 — Scoring algorithm

## Notes

Tests are currently **interface definitions** — they document expected behavior
and will pass once implementation matches the SPEC. Run tests after each
module is implemented to validate correctness.

## TODO

- [ ] Add integration tests for full pipeline
- [ ] Add load tests (413 feeds simulation)
- [ ] Add property-based tests for scoring
- [ ] Add fuzzing for RSS parsing
