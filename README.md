# Daily News Digest v2

Personalized daily news digest system with zero hallucination tolerance.

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run web UI
python -m web.app

# Run pipeline manually
python -m src.pipeline
```

## Structure

```
news-digest/
├── src/              # Core pipeline
│   ├── fetcher/      # RSS feed fetching
│   ├── scorer/       # Article scoring
│   ├── poster/       # Discord posting
│   └── database/     # SQLite operations
├── web/              # FastAPI + HTML frontend
├── config/           # Feeds, settings
├── data/             # SQLite database
├── tests/            # Test suite
├── scripts/          # Cron scripts
└── docs/             # Documentation
```

## Spec

See [SPEC.md](SPEC.md) for full requirements.

## License

MIT
