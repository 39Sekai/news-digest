# Daily News Digest v2 - Deployment Guide

**Target:** Legion-knight (LG) - Ubuntu 24.04 LTS  
**Runtime:** Python 3.11+ with SQLite  
**Schedule:** Daily 8:00 AM Asia/Shanghai via OpenClaw cron

---

## Quick Start

```bash
# 1. Clone repo
cd ~/.openclaw-argus/workspace/
git clone https://github.com/39Sekai/news-digest.git
cd news-digest

# 2. Run setup
python scripts/setup.py

# 3. Test the pipeline
python scripts/cron-digest.py --test
python scripts/cron-digest.py --dry-run
```

---

## Directory Structure

```
news-digest/
├── data/               # SQLite DB + logs (gitignored)
│   ├── news_digest.db
│   └── logs/
│       └── digest_YYYYMMDD_HHMMSS.log
├── scripts/            # Automation scripts
│   ├── cron-digest.py  # Main entry point
│   └── setup.py        # Bootstrap script
├── src/                # Core pipeline (Atlas)
├── web/                # FastAPI UI (Iris)
├── config/             # feeds.json, settings
└── docs/               # Documentation
```

---

## OpenClaw Cron Configuration

Create this cron job for 8:00 AM daily (Asia/Shanghai):

```json
{
  "name": "news-digest-daily",
  "schedule": {
    "kind": "cron",
    "expr": "0 8 * * *",
    "tz": "Asia/Shanghai"
  },
  "payload": {
    "kind": "systemEvent",
    "text": "Run daily news digest: cd ~/.openclaw-argus/workspace/news-digest && python scripts/cron-digest.py"
  },
  "sessionTarget": "main",
  "enabled": true
}
```

---

## Environment Variables

Create `~/.openclaw-argus/workspace/news-digest/.env`:

```bash
# Discord (required)
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=1475330217215004904

# Optional overrides
DATABASE_PATH=/custom/path/news_digest.db
LOG_LEVEL=INFO
```

---

## Log Rotation

Logs auto-rotate daily. Manual cleanup:

```bash
# Keep last 30 days of logs
find data/logs -name "digest_*.log" -mtime +30 -delete

# Archive old logs
tar czf data/logs/archive_$(date +%Y%m).tar.gz data/logs/digest_*.log -mtime +7
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Database locked | Check if another process is running; wait 30s and retry |
| Discord post fails | Verify DISCORD_TOKEN and channel permissions |
| Feed fetch errors | Check feed health in web UI; feeds auto-disable after 5 errors |
| Empty digest posted | Normal if no articles match criteria in last 48h |

---

## Maintenance

**Daily (automated):**
- Cron triggers at 8:00 AM
- Logs written to `data/logs/`

**Weekly (manual):**
- Review feed health in web UI
- Clean old logs (>30 days)
- Check database size: `ls -lh data/news_digest.db`

**Monthly:**
- Backup database: `cp data/news_digest.db data/backups/`
- Review and update feed list

---

## Rollback

If deployment breaks:

```bash
cd ~/.openclaw-argus/workspace/news-digest
git stash  # Save current work
git checkout main  # Return to known-good state
python scripts/setup.py  # Re-run setup if needed
```
