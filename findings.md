# News Digest v2 — Findings & Decisions Log

## 2026-03-13: Requirements Session

### Decisions Made
| Topic | Decision | Notes |
|-------|----------|-------|
| Channel | `#notifications` | One message per category |
| Format | Text-only | No embeds, no images |
| Content | One-liner brief + source | NOT original titles |
| Deduplication | First appearance wins | Same story → one entry |
| Empty days | Post "nothing today" | Don't skip |
| Categories | Tech first, ACGN later | Phase 1 = tech only |
| Hallucination | Zero tolerance | Whitelist sources, no LLM |
| **Filtering** | **Top N default (10), Binary optional** | Score and sort, max 10 articles |
| **Interface** | **Web UI** | FastAPI + HTML |
| **Title source** | **One-liner brief** | Manually curated via interface |
| **Stale feeds** | **1 week (168h), adjustable** | Not 72h as originally proposed |
| **Feed status** | **Admin UI only** | NOT in Discord message |
| **Brief timing** | **Daily before post** | Fresh news (within 24h) |

### One-Liner Brief Workflow
**Schedule:**
- 7:30 AM: Fetch articles (last 24h)
- 7:30-7:55 AM: Review queue in web UI
- You write briefs for top articles
- 7:55 AM: Scoring/ranking
- 8:00 AM: Post to Discord

**Fallback:** Original title if no brief written (flagged for review)

### Feed Health Detection
**Broken feed =**
- HTTP 4xx/5xx errors
- Timeout (>30s)
- Parse error (invalid XML)
- SSL failure
→ Disabled after 5 consecutive errors

**Stale feed =**
- No new articles in 168 hours (1 week)
→ Flagged in UI, NOT in Discord message

### Technical Stack Confirmed
| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11 | Better RSS libs |
| Database | SQLite | Single-file |
| Interface | FastAPI + HTML | Web UI |
| Scheduler | OpenClaw cron | Already working |

### Open Questions
- [ ] **Scoring algorithm** — awaiting Krisspy's research
- [ ] **Build approval** — waiting for go-ahead

