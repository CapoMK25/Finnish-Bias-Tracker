# Roadmap

> Phased development plan. Each milestone is a shippable unit. Don't move to the next milestone until the previous one works end-to-end.

## M0: Foundation (Week 0 — current)

**Goal**: Lock down what we're building before we write code.

- [x] Project scaffold
- [ ] Methodology document (`docs/methodology.md`) v1
- [ ] Source list (`docs/sources.md`) v1
- [ ] Database schema design (`docs/architecture.md`)
- [ ] LLM scoring prompt v1 (`apps/scrapers/src/prompts/bias_scoring.py`)
- [ ] Get feedback from 1-2 Finnish journalists or media researchers

**Tech needed**: None. Just markdown and thinking.

**Exit criteria**: Methodology document reviewed and shippable.

---

## M1: Single source pipeline (Weeks 1-3)

**Goal**: Scrape ONE source (Yle), extract clean text, score it with LLM, store it.

Pick Yle because: stable RSS, no paywall, well-formatted, neutral starting point.

- [ ] Docker Compose dev environment (Postgres + Redis)
- [ ] PostgreSQL schema + Drizzle migrations
- [ ] Python scraper for Yle RSS
- [ ] `trafilatura`-based article extraction
- [ ] Anthropic SDK integration
- [ ] LLM scoring prompt v1 working end-to-end
- [ ] Store: article + bias score + rationale in Postgres
- [ ] Simple CLI to inspect results: `python -m scrapers.inspect --limit 10`

**Tech needed**:
- Python 3.12 + `feedparser`, `trafilatura`, `anthropic`, `psycopg`
- PostgreSQL 16 (via Docker)
- TypeScript types in `packages/shared`

**Files added**:
- `docker-compose.dev.yml`
- `apps/api/src/db/schema.ts` (Drizzle schema)
- `apps/scrapers/src/scrapers/yle.py`
- `apps/scrapers/src/extractors/text_extractor.py`
- `apps/scrapers/src/scoring/llm_scorer.py`
- `apps/scrapers/src/prompts/bias_scoring.py`

**Exit criteria**: You can run one command and see 10 freshly scored articles in your database with full rationales.

---

## M2: All sources + scheduling (Weeks 4-5)

**Goal**: All ~20 sources scraped continuously, scored automatically.

- [ ] Generic RSS scraper handling all sources from `docs/sources.md`
- [ ] BullMQ for job scheduling (every 30 minutes for breaking news, every 4 hours for slower outlets)
- [ ] Dead-letter queue for failed scrapes
- [ ] Rate limiting per source (be a good citizen)
- [ ] Article deduplication (canonical URL + content hash)
- [ ] LLM scoring worker (consumes queue, scores in batches)
- [ ] Basic monitoring: which sources are failing, queue depth, scoring latency

**Tech added**:
- Redis 7 (via Docker)
- BullMQ (TypeScript) running in API process
- Python workers consuming the queue

**Files added**:
- `apps/api/src/queue/queues.ts`
- `apps/api/src/queue/workers/scoring_worker.ts`
- `apps/scrapers/src/scrapers/base.py` (abstract base class)
- `apps/scrapers/src/scrapers/*.py` (one per source)
- `apps/scrapers/src/run.py` (entry point)

**Exit criteria**: ~500 articles per day flowing in and getting scored automatically.

---

## M3: Story clustering (Weeks 6-7)

**Goal**: Group articles covering the same event.

- [ ] Voyage AI embeddings integration (`voyage-3` model)
- [ ] HDBSCAN clustering in 48-hour rolling windows
- [ ] Cluster persistence in Postgres (with cluster membership history)
- [ ] Cluster-level metrics: bias distribution, blindspot detection
- [ ] Cluster merging logic (when a story develops over hours/days)

**Tech added**:
- Voyage AI API
- `hdbscan`, `numpy`, `scikit-learn` (Python)
- pgvector extension on Postgres (for embedding storage and similarity search)

**Files added**:
- `apps/scrapers/src/clustering/embedder.py`
- `apps/scrapers/src/clustering/clusterer.py`
- `apps/scrapers/src/clustering/blindspot.py`

**Exit criteria**: For any given story (e.g., "Marin government austerity vote"), the tracker correctly groups Yle, HS, IL, KU, Verkkouutiset coverage into one cluster with bias distribution visible.

---

## M4: API (Weeks 8)

**Goal**: Hono API serving stories, sources, and clusters.

- [ ] `GET /api/stories` — list recent story clusters with bias distribution
- [ ] `GET /api/stories/:id` — detailed cluster with all member articles
- [ ] `GET /api/sources` — list of sources with metadata
- [ ] `GET /api/sources/:slug` — source profile with recent articles and topic-bias breakdown
- [ ] `GET /api/blindspots` — list of stories with significant blindspots
- [ ] Rate limiting (sliding window)
- [ ] OpenAPI spec auto-generated

**Tech added**:
- Hono on Bun (or Node 20+)
- Zod for input validation
- `@hono/zod-openapi` for OpenAPI generation

**Files added**:
- `apps/api/src/index.ts`
- `apps/api/src/routes/stories.ts`
- `apps/api/src/routes/sources.ts`
- `apps/api/src/routes/blindspots.ts`
- `apps/api/src/middleware/rate_limit.ts`

**Exit criteria**: `curl localhost:3000/api/stories` returns JSON of recent clustered stories.

---

## M5: Frontend (Weeks 9-11)

**Goal**: SvelteKit UI that makes the data legible.

- [ ] Homepage: recent stories with left/center/right ribbon
- [ ] Story detail page: all articles in cluster, bias chart, blindspot indicator
- [ ] Source profile pages
- [ ] Bias methodology page (renders the markdown from `docs/methodology.md`)
- [ ] Dark mode (because it's 2026 and the audience expects it)
- [ ] Finnish + English language toggle (i18n)
- [ ] Mobile-responsive

**Tech added**:
- SvelteKit 2 + Svelte 5
- TailwindCSS
- shadcn-svelte components
- `svelte-i18n` for localization

**Files added**:
- `apps/web/src/routes/+page.svelte`
- `apps/web/src/routes/stories/[id]/+page.svelte`
- `apps/web/src/routes/sources/[slug]/+page.svelte`
- `apps/web/src/lib/components/BiasRibbon.svelte`
- `apps/web/src/lib/components/StoryCard.svelte`

**Exit criteria**: A friend who isn't technical can use the site and understand the bias data.

---

## M6: Production deploy (Week 12)

**Goal**: Live at a real domain.

- [ ] Hetzner VPS provisioned with Terraform
- [ ] Coolify (or plain Docker Compose) for deployment
- [ ] PostgreSQL with automated backups to Hetzner Storage Box
- [ ] Cloudflare in front (DNS, CDN, DDoS protection)
- [ ] Frontend on Cloudflare Pages (auto-deploys from GitHub)
- [ ] GitHub Actions CI/CD: test → build → deploy
- [ ] Sentry for error tracking
- [ ] Plausible Analytics (privacy-friendly, EU-hosted)

**Tech added**:
- Terraform (Hetzner provider)
- Cloudflare (DNS + Pages)
- GitHub Actions
- Sentry (free tier)
- Plausible

**Files added**:
- `infra/terraform/main.tf`
- `infra/terraform/variables.tf`
- `infra/terraform/outputs.tf`
- `.github/workflows/api.yml`
- `.github/workflows/scrapers.yml`
- `.github/workflows/web.yml`

**Exit criteria**: `https://your-domain.fi` works publicly, articles update automatically, you can demo it.

---

## M7: Launch + feedback (Week 13)

- [ ] Post to r/Suomi
- [ ] Post to Hacker News ("Show HN: Open-source media bias tracker for Finnish news")
- [ ] Email 5 Finnish journalism schools and media researchers
- [ ] Open Issues for community methodology feedback
- [ ] Write a launch blog post (single one — this is not the start of an influencer career)

---

## Post-M7 (months 4-12)

These are stretch goals, not commitments:

- **Per-topic bias tracking** (M3 covers source-level; this would add UI)
- **Historical analysis** (how has Source X's bias evolved over time?)
- **Election cycle tools** (special views during election periods)
- **Newsletter** (weekly blindspot report — only if there's demand)
- **Browser extension** (overlay bias on any Finnish news site)
- **API access for researchers** (potentially paid tier for academia)
- **Other Nordic countries** (same architecture, different sources)

## Anti-roadmap (things I am consciously NOT building)

- Mobile apps (PWA is enough)
- User accounts / personalization (privacy + scope creep)
- Comments / community features (moderation burden)
- Real-time push notifications (not the use case)
- A bias tracker that says "this is the truth" (we score consistently, not omnisciently)

## Tech stack progression summary

| Phase | Stack additions | Cumulative complexity |
|-------|-----------------|----------------------|
| M0 | Just markdown | Trivial |
| M1 | Python + Postgres + Anthropic SDK | Low |
| M2 | Redis + BullMQ + multiple scrapers | Medium |
| M3 | Voyage AI + pgvector + HDBSCAN | Medium-high |
| M4 | Hono API | Medium-high |
| M5 | SvelteKit | High |
| M6 | Terraform + Cloudflare + CI/CD | High |

**Resist adding complexity before its phase.** No Kubernetes. No microservices. No Kafka. The whole system fits on one Hetzner VPS until proven otherwise.
