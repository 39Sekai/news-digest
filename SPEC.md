# Daily News Digest v2 — OpenSpec

**Version:** 1.0.0  
**Status:** DRAFT (Pending Client Approval)  
**Date:** 2026-03-13  
**Owner:** krisspy39  
**PM:** Daedalus  

---

## 1. Overview

Personalized daily news digest system that posts categorized news summaries to Discord. Built with zero hallucination tolerance and a user-friendly management interface.

---

## 2. Core Requirements

### 2.1 Daily Delivery
| Attribute | Specification |
|-----------|---------------|
| **Frequency** | Once daily |
| **Time** | 8:00 AM Asia/Shanghai |
| **Channel** | `#notifications` (1475330217215004904) |
| **Format** | Text-only Discord messages |
| **Structure** | One message per category |

### 2.2 Content Format (Per Message)

**Message Structure:**
```
📰 Tech News — March 14, 2026

• {one-liner brief} — Source Name
• {one-liner brief} — Source Name
• {one-liner brief} — Source Name

_Total: N articles from {feed_count} sources_
```

**Article Entry Requirements:**
- **Title**: One-liner brief (manually curated, NOT original article title)
- **Source**: Publication/site name only
- **No URLs in message** (keep it clean, just source attribution)
- **No summaries/descriptions** (title only)
- **No images/embeds** (text-only)

**One-Liner Brief Workflow:**
- System fetches original article
- You write/edit the one-liner brief via management interface
- Stored in database linked to article
- Posted to Discord using your curated brief
- If no brief exists, falls back to original title (marked for your review)

**Example:**
```
📰 Tech News — March 14, 2026

• OpenAI launches GPT-5 with multimodal reasoning — TechCrunch
• Rust 1.85 adds async traits natively — Rust Blog
• Kubernetes deprecates Docker shim in v1.32 — Kubernetes.io
• CVE-2026-1234: Critical OpenSSL vulnerability disclosed — Security Week

_Total: 4 articles from 156 sources_
```

### 2.3 Categories (Phase 1)

**Initial Category:** Tech only
- AI/Machine Learning
- Programming/Dev Tools
- Infrastructure/DevOps
- Security
- General Tech News

**Future Categories:** ACGN (Anime, Comics, Games, Novels)

### 2.4 Filtering Strategy

**Default Mode: Top N**
- Score all articles using interest weights
- Sort by score (highest first)
- Take top N articles (configurable, default 10)
- Consistent, predictable daily volume

**Optional Mode: Binary (Threshold)**
- Include any article scoring ≥ threshold
- Variable daily count (could be 0, could be 50)
- For users who want "everything relevant"

**Client Decision:** ✅ Top N default, Binary optional

---

## 3. Data Pipeline

### 3.1 Feed Sources
- **Total:** 413 RSS feeds (from `feeds.json`)
- **Format:** RSS/Atom
- **Categories:** Pre-tagged (AI/, GENERAL/, EVENTS/, ALERT/, etc.)

### 3.2 Deduplication
| Scenario | Behavior |
|----------|----------|
| Same story on multiple feeds | Use first appearance (by publish time) |
| Similar titles (fuzzy match) | Treat as duplicate if >85% similar |
| URL-based dedupe | Primary key is normalized URL |

### 3.3 Empty Day Handling
- Post: `📰 Tech News — March 14, 2026\n\nNo articles matched your interests today.`
- Do NOT skip posting (user expects daily signal)

---

## 4. Anti-Hallucination Requirements

**CRITICAL: Zero Tolerance Policy**

| Risk | Mitigation |
|------|------------|
| Fake news sources | Whitelist-only feed sources (no auto-discovery) |
| AI-generated content | NO LLM summarization of articles |
| Outdated articles | Filter: max age 48 hours |
| Incorrect attribution | Direct source name from feed, never guessed |
| Title rewriting | Human-written briefs OR original titles only |

**Allowed Data Transformations:**
- ✅ Original article title
- ✅ Human-curated one-liner (if manually added)
- ❌ LLM-generated summaries
- ❌ Paraphrased content
- ❌ Guessed/inferred information

---

## 5. Management Interface

### 5.1 Feed Management (CRUD)

**Required Operations:**
- Add new feed (URL + name + category)
- Remove/disable feed
- List all feeds with status
- Update feed metadata

**Interface: Web UI**
- Browser-based management
- Real-time updates
- Mobile-friendly
- No terminal knowledge required

**Key Requirement:** Changes apply immediately (no restart)

### 5.2 Feed Health Monitoring

**A feed is considered BROKEN when:**
| Condition | Detection Method | Action |
|-----------|------------------|--------|
| HTTP error | Status code 4xx/5xx on fetch | Log error, increment error counter |
| Timeout | No response after 30s | Treat as error |
| Parse error | Invalid RSS/Atom XML | Log specific error |
| SSL/TLS failure | Certificate issues | Log error |

**A feed is considered STALE when:**
| Condition | Detection Method | Action |
|-----------|------------------|--------|
| No new articles | Last article > 168 hours ago (1 week) | Flag for review |
| Feed unchanged | HTTP 304 (not modified) is OK | Normal behavior |
| Empty feed | Valid RSS but zero entries | Log warning |

**Note:** Stale time is configurable via `stale_feed_hours` setting.

**Automatic Actions:**
- Feed disabled after 5 consecutive fetch errors
- Stale feeds get marked "⚠️ Review needed" in UI
- Feed status tracked in admin UI only (NOT in Discord message)

### 5.3 Settings Management

**Configurable Parameters:**
| Setting | Default | Description |
|---------|---------|-------------|
| `post_time` | 08:00 Asia/Shanghai | Daily post time |
| `max_article_age` | 48 hours | Skip articles older than this |
| `filter_mode` | top_n | "binary" or "top_n" |
| `top_n_limit` | 10 | Max articles if filter_mode=top_n (default: 10) |
| `binary_threshold` | 0.6 | Min score for binary mode |
| `dedupe_threshold` | 0.85 | Similarity score for duplicates |
| `enabled_categories` | ["tech"] | Active categories |
| `alert_on_feed_failure` | true | Notify when feeds break |
| `stale_feed_hours` | 168 | Feed considered stale if no new posts (1 week, adjustable) |
| `max_feed_errors` | 5 | Disable feed after N consecutive errors |

**Interface:** Web UI (FastAPI + HTML)

---

## 6. Technical Architecture

### 6.1 Stack Recommendation

| Layer | Recommendation | Rationale |
|-------|----------------|-----------|
| **Language** | Python 3.11+ | Better RSS ecosystem, easier text processing |
| **Database** | SQLite | Single-file, zero-config, sufficient for 413 feeds |
| **RSS Parsing** | `feedparser` + `httpx` | Robust, async-capable |
| **Scheduling** | OpenClaw cron | Already configured, reliable |
| **Interface** | FastAPI + simple HTML | Lightweight, real-time updates |
| **Deployment** | Local (Legion-knight) | Data stays on your machine |

### 6.2 Data Schema

**articles table:**
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_feed_id INTEGER,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category TEXT,
    is_posted BOOLEAN DEFAULT 0,
    is_duplicate BOOLEAN DEFAULT 0,
    duplicate_of INTEGER
);
```

**feeds table:**
```sql
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    reliability REAL DEFAULT 0.7,
    enabled BOOLEAN DEFAULT 1,
    last_fetch TIMESTAMP,
    last_error TEXT,
    error_count INTEGER DEFAULT 0
);
```

**settings table:**
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.3 Pipeline Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Cron      │────▶│   Fetcher    │────▶│  Parser     │
│  (8am daily)│     │(413 feeds)   │     │ (RSS/Atom)  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       ▼
                ┌──────────────┐
                │  Deduplicate │── URL match
                │   + Filter   │── Age filter (48h)
                │              │── Category match
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │   Sort/Rank  │── (if top_n mode)
                │   (optional) │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │   Format     │── Build Discord message
                │   (Discord)  │── Text-only, no URLs
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │    Post      │── #notifications
                │   Discord    │── Mark posted in DB
                └──────────────┘
```

---

## 7. Error Handling

| Error | Behavior |
|-------|----------|
| Feed fetch fails | Log error, skip feed, continue others |
| All feeds fail | Post "Unable to fetch news today" |
| Database locked | Retry with exponential backoff |
| Discord post fails | Retry 3x, then alert admin |
| Parse error | Log article URL, skip individual article |

---

## 8. Success Criteria (Acceptance Checklist)

### 8.1 Functional
- [ ] Posts daily at 8am Asia/Shanghai (±5 min tolerance)
- [ ] Text-only format matches spec exactly
- [ ] One-liner briefs (not original titles)
- [ ] Source attribution only (no URLs in message)
- [ ] Deduplication working (same story = one entry)
- [ ] Empty days post "nothing today" message
- [ ] All 413 feeds import successfully

### 8.2 Quality
- [ ] Zero hallucinated content
- [ ] No articles older than 48 hours
- [ ] Accurate source attribution
- [ ] Proper categorization

### 8.3 Management
- [ ] Web/TUI interface for feed CRUD
- [ ] Settings changes apply without restart
- [ ] Real-time feed status visible
- [ ] Error logs accessible

### 8.4 Reliability
- [ ] Handles 1 feed failure gracefully
- [ ] Handles 50% feed failure gracefully
- [ ] Recovers from restart mid-pipeline
- [ ] Database backups (daily)

---

## 9. Open Questions (Answered)

1. ✅ **Filtering mode:** Top N default, Binary optional
2. ✅ **Management interface:** Web UI (not TUI)
3. ✅ **Title briefs:** Manually curate one-liners via interface
4. ✅ **Feed failure alerts:** Yes, with automatic detection

### 5.4 One-Liner Brief Workflow

**Timing:** Daily before post (articles fetched, queued for review same day)

**Process:**
1. **7:30 AM** — Pipeline fetches articles from all feeds (last 24 hours only)
2. **7:30-7:55 AM** — Articles appear in web UI "Review Queue"
3. **You review** — Write one-liner briefs for top articles (or mark to skip)
4. **7:55 AM** — System scores and ranks articles
5. **8:00 AM** — Top N articles with curated briefs posted to Discord

**If brief not written:** Falls back to original title (flagged for review)

**UI Features:**
- Quick-edit inline (click title → type brief → save)
- Bulk actions (select multiple → write briefs)
- Preview Discord formatting
- Time remaining until post

---

## 10. Scoring Algorithm (Locked)

### Main Formula
```
final_score = (w1 * semantic_score) + (w2 * recency_score) + (w3 * source_score) + (w4 * novelty_score)
```

**Weights:**
| Factor | Weight | Description |
|--------|--------|-------------|
| `w1` semantic | **0.6** | Content relevance to interests |
| `w2` recency | **0.2** | Freshness (decay over time) |
| `w3` source | **0.1** | Source trustworthiness |
| `w4` novelty | **0.1** | Diversity (penalize duplicates) |

### Scoring Factors

**1. Semantic Score (Relevance)**
- Method: Cosine similarity between article embedding and user interest vector
- Range: 0 to 1
- Formula: `dot(a, b) / (norm(a) * norm(b))`

**2. Recency Score (Freshness)**
- Method: Exponential decay
- Half-life: **24 hours**
- Formula: `exp(-0.693 * age_hours / 24)`
- New articles = 1.0, 24h old = 0.5, 48h old = 0.25

**3. Source Trust Score**
- Method: Lookup table
- Example scores:
  - Reuters/BBC: 1.0
  - TechCrunch: 0.9
  - Medium: 0.6
  - Unknown: 0.4

**4. Novelty Score (Diversity)**
- Method: Maximal Marginal Relevance (MMR)
- Threshold: **0.85** similarity
- Formula: `1.0 - max(0, (max_sim - 0.85) / 0.15)`
- Prevents similar articles in same digest

### Final Ranking Rules
1. Sort by `final_score` (descending)
2. Keep only items with `final_score > 0.4`
3. Return top **10** items

---

## 12. Project Setup

### Repository
- **Name:** `news-digest`
- **Location:** `/home/krisspy/.openclaw-daedalus/workspace/news-digest/`
- **Type:** Standalone Python project (not in shared-repo)
- **Structure:**
  ```
  news-digest/
  ├── src/              # Core pipeline
  ├── web/              # FastAPI + HTML frontend
  ├── config/           # Feeds, settings
  ├── data/             # SQLite database
  ├── tests/            # Test suite
  ├── scripts/          # Cron scripts
  └── docs/             # Documentation
  ```

### Tech Stack
| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Database | SQLite |
| Web Framework | FastAPI |
| Frontend | HTML + vanilla JS |
| RSS Parsing | feedparser + httpx |
| Embeddings | sentence-transformers |
| Scheduler | OpenClaw cron |

### Daily Schedule
| Time | Action |
|------|--------|
| 7:30 AM | Fetch articles (last 24h) |
| 7:30-7:55 AM | Review queue open for briefs |
| 7:55 AM | Score and rank articles |
| 8:00 AM | Post to #notifications |

---

## 13. Final Approval Checklist

| Item | Status |
|------|--------|
| Top N = 10 | ✅ |
| Stale feeds = 168h (1 week) | ✅ |
| Feed status in admin UI only | ✅ |
| Brief workflow: Daily before post | ✅ |
| Scoring algorithm (4-factor weighted) | ✅ |
| Repo location & structure defined | ✅ |
| **Ready to build?** | ❓ Waiting approval |

---

## 14. Out of Scope (Future Versions)

- LLM-generated summaries
- Image/previews in Discord
- Multi-channel posting
- User-specific digests (multi-tenant)
- Mobile app
- Email delivery
- Real-time alerts (breaking news)

---

*Ready for client review. No code will be written until this spec is approved.*
