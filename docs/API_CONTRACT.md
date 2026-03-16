# Backend API Contract for Web UI

**Atlas → Iris Handoff Document**

FastAPI endpoints provided by backend for web frontend consumption.

---

## Base URL

```
http://localhost:8000/api/v1
```

---

## Feed Management

### List Feeds
```
GET /feeds
```

**Response:**
```json
{
  "feeds": [
    {
      "id": 1,
      "url": "https://techcrunch.com/feed/",
      "name": "TechCrunch",
      "category": "GENERAL",
      "reliability": 0.9,
      "enabled": true,
      "last_fetch": "2026-03-13T12:00:00Z",
      "last_error": null,
      "error_count": 0,
      "last_article_at": "2026-03-13T10:00:00Z"
    }
  ]
}
```

### Add Feed
```
POST /feeds
```

**Body:**
```json
{
  "url": "https://example.com/rss",
  "name": "Example Blog",
  "category": "GENERAL",
  "reliability": 0.7
}
```

**Response:** `201 Created`
```json
{
  "id": 2,
  "url": "https://example.com/rss",
  "name": "Example Blog",
  "category": "GENERAL",
  "reliability": 0.7,
  "enabled": true
}
```

### Update Feed
```
PATCH /feeds/{feed_id}
```

**Body:** (any subset of fields)
```json
{
  "name": "New Name",
  "enabled": false
}
```

**Response:** `200 OK`

### Delete Feed
```
DELETE /feeds/{feed_id}
```

**Response:** `204 No Content`

---

## Brief Editor (Review Queue)

### Get Articles for Review
```
GET /briefs/queue
```

Returns articles fetched in last 24h needing brief curation.

**Response:**
```json
{
  "articles": [
    {
      "id": 101,
      "title": "OpenAI launches GPT-5 with multimodal reasoning",
      "source_name": "TechCrunch",
      "published_at": "2026-03-13T10:00:00Z",
      "brief": null,
      "category": "AI"
    }
  ],
  "total": 42,
  "with_briefs": 5
}
```

### Add/Update Brief
```
POST /briefs/{article_id}
```

**Body:**
```json
{
  "brief": "OpenAI launches GPT-5 with multimodal reasoning capabilities"
}
```

**Response:** `200 OK`

### Delete Brief
```
DELETE /briefs/{article_id}
```

**Response:** `204 No Content`

---

## Settings

### Get All Settings
```
GET /settings
```

**Response:**
```json
{
  "post_time": "08:00",
  "timezone": "Asia/Shanghai",
  "max_article_age": "48",
  "filter_mode": "top_n",
  "top_n_limit": "10",
  "binary_threshold": "0.6",
  "dedupe_threshold": "0.85",
  "enabled_categories": ["tech"],
  "alert_on_feed_failure": true,
  "stale_feed_hours": "168",
  "max_feed_errors": "5"
}
```

### Update Setting
```
PUT /settings/{key}
```

**Body:**
```json
{
  "value": "09:00"
}
```

**Response:** `200 OK`

---

## Statistics & Health

### Get Stats
```
GET /stats
```

**Response:**
```json
{
  "total_articles": 1523,
  "unposted_articles": 47,
  "total_feeds": 413,
  "enabled_feeds": 398,
  "broken_feeds": 3,
  "stale_feeds": 12
}
```

### Trigger Manual Fetch
```
POST /actions/fetch
```

**Response:**
```json
{
  "success": 398,
  "failed": 3,
  "articles": 23
}
```

### Preview Digest
```
GET /actions/preview
```

**Response:**
```json
{
  "content": "📰 Tech News — March 14, 2026\n\n• OpenAI launches GPT-5...",
  "article_count": 10,
  "articles": [...]
}
```

---

## WebSocket (Real-time Updates)

```
WS /ws
```

Events:
- `feed_updated` — Feed status changed
- `new_articles` — New articles fetched
- `brief_saved` — Brief was updated
- `settings_changed` — Settings updated

---

## Error Responses

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human readable description"
}
```

**Common codes:**
- `400` — Bad Request
- `404` — Not Found
- `409` — Conflict (duplicate URL, etc.)
- `500` — Internal Server Error

---

## Notes for Iris

1. **Feed Health:** Use `error_count` and `last_fetch` to show broken/stale status per SPEC §5.2
2. **Brief Queue:** Poll `/briefs/queue` every 30s during 7:30-7:55 AM window
3. **Preview:** Use `/actions/preview` to show user how digest will look
4. **Real-time:** Connect to WebSocket for live feed status updates

**Changes apply immediately** — no restart required per SPEC §5.1
