# Architecture

## System overview

```
                                ┌─────────────────────┐
                                │   News sources      │
                                │   (RSS, sitemaps)   │
                                └──────────┬──────────┘
                                           │
                                           ▼
                            ┌──────────────────────────┐
                            │  Python scrapers         │
                            │  (feedparser, trafilatura)│
                            └──────────┬───────────────┘
                                       │
                                       ▼
                            ┌──────────────────────────┐
                            │  Redis queue (BullMQ)    │
                            └──────────┬───────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                ▼                      ▼                      ▼
      ┌─────────────────┐  ┌───────────────────┐  ┌─────────────────┐
      │ Scoring worker  │  │ Embedding worker  │  │ Cluster worker  │
      │ (Claude Haiku)  │  │ (Voyage AI)       │  │ (HDBSCAN)       │
      └────────┬────────┘  └─────────┬─────────┘  └────────┬────────┘
               │                     │                     │
               └─────────────────────┼─────────────────────┘
                                     ▼
                          ┌──────────────────────┐
                          │  PostgreSQL          │
                          │  + pgvector          │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  Hono API            │
                          │  (TypeScript)        │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  SvelteKit frontend  │
                          └──────────────────────┘
```

## Database schema (v1)

### `sources`
Static-ish table of news outlets we track.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| slug | text unique | e.g. `helsingin-sanomat` |
| name | text | Display name |
| url | text | Homepage |
| rss_url | text | Where we scrape |
| bias_score | int | -3 to +3 (source-level) |
| source_type | text | enum: party_organ, mainstream, tabloid, business, public, alternative, wire |
| ownership | text | Free-form description |
| flagged | boolean | If true, never aggregate |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `articles`
One row per scraped article.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| source_id | uuid | FK → sources.id |
| url | text unique | Canonical URL |
| title | text | |
| body | text | Extracted clean text |
| published_at | timestamptz | From RSS or page |
| scraped_at | timestamptz | |
| content_hash | text | sha256 of body, for dedupe |
| language | text | "fi" / "sv" / "en" |
| article_type | text | enum: news, opinion, analysis, blog |
| embedding | vector(1024) | pgvector |
| cluster_id | uuid nullable | FK → clusters.id |

### `article_scores`
Bias scoring results (can have multiple per article: different runs, different models).

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| article_id | uuid | FK → articles.id |
| bias_score | int | -3 to +3 |
| confidence | numeric(3,2) | 0.00 to 1.00 |
| rationale | text | LLM explanation |
| examples | jsonb | Array of loaded-language examples |
| topic | text | classification |
| summary | text | One-sentence summary |
| model | text | e.g. "claude-haiku-4-5-20251001" |
| prompt_version | text | e.g. "v1.0" |
| scored_at | timestamptz | |

### `clusters`
Groups of articles covering the same story.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| title | text | Auto-generated story title |
| first_seen_at | timestamptz | |
| last_seen_at | timestamptz | |
| article_count | int | Denormalized |
| bias_distribution | jsonb | `{"left": 0.2, "center": 0.5, "right": 0.3}` |
| entropy | numeric(4,3) | Shannon entropy |
| blindspot_label | text nullable | enum: left_blindspot, right_blindspot, balanced |

### `human_reviews`
For methodology calibration.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| article_id | uuid | FK |
| reviewer | text | Anonymized identifier |
| human_score | int | |
| llm_score | int | What the LLM said |
| notes | text | |
| reviewed_at | timestamptz | |

## Data flow

1. **Scraper** polls RSS for source X
2. New URLs go into the `scraping_queue`
3. **Extraction worker** fetches each URL, runs trafilatura, stores raw article in `articles` (without score, without embedding, without cluster)
4. Insertion triggers two queue jobs: `score_article` and `embed_article`
5. **Scoring worker** calls Claude Haiku, writes to `article_scores`
6. **Embedding worker** calls Voyage AI, writes to `articles.embedding`
7. Every 30 minutes, **clustering worker** runs HDBSCAN on the rolling 48h window, updates `clusters` and `articles.cluster_id`
8. Cluster metrics (bias distribution, entropy, blindspot) computed on cluster update

## Why these choices

**Why PostgreSQL over MongoDB?**
Relational data. Articles belong to sources, articles belong to clusters, articles have many scores. Joins everywhere. Mongo would be worse.

**Why Hono over NestJS / Express?**
Modern TypeScript, no decorators, runs on Bun/Node, ergonomic without enterprise-Java vibes. Better DX than Express, less magic than NestJS.

**Why Python for scrapers when TS could do it?**
`trafilatura` is the best HTML→text library, full stop. `feedparser` is the best RSS library. The Python ML/NLP ecosystem is unbeatable for the scoring/embedding layer. Don't fight the stack.

**Why Claude Haiku over GPT?**
Strong Finnish support, transparent pricing, structured outputs that work. Sonnet 4.5 for spot-checks and prompt iteration; Haiku 4.5 for production scoring volume.

**Why Voyage AI for embeddings?**
Multilingual, better than OpenAI on non-English content per recent MTEB benchmarks. Reasonable pricing.

**Why HDBSCAN over k-means?**
Stories cluster at variable density. K-means forces fixed cluster count; HDBSCAN finds natural groupings and labels outliers as noise (which is correct behavior — not every article belongs to a story cluster).

**Why Hetzner over AWS?**
Cost. A €10/month Hetzner box does what €100/month of AWS would. Move to AWS only if scale demands it. This whole system fits on one VPS comfortably until traffic exceeds ~10k DAU.

**Why AGPL over MIT?**
Prevents proprietary forks from taking the methodology private. Anyone using the code commercially must publish their modifications. This protects the public-good nature of the project.

## Scaling considerations (when relevant)

The current design works comfortably to:
- ~50 sources
- ~5,000 articles per day
- ~10,000 daily active users on the API
- One VPS with 4GB RAM

Beyond that:
- Move Postgres to managed service (Hetzner managed Postgres, AWS RDS)
- Split scrapers, scoring, and API into separate hosts
- Add read replicas for Postgres
- CDN-cache cluster/story endpoints aggressively (they don't change second-to-second)

But: **don't pre-optimize.** Get to M7 first. Worry about scale when it's a problem.
