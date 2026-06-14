# Architecture | Finnish Bias Tracker

## System overview
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
  │    (Gemini)             (Voyage AI)            (HDBSCAN)       
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

## Frontend (M5)

The frontend is a SvelteKit application that consumes the Hono API and renders the user-facing views of the bias tracker. This section documents the architectural decisions made before any frontend code was written, following the same decision-documentation pattern established by #20 (RSSScraper base class refactor). Decisions are recorded here.

### Framework: SvelteKit 2.x with TypeScript

SvelteKit ships smaller bundles than React-based alternatives because the Svelte compiler eliminates the framework runtime at build time — components compile to direct DOM operations rather than virtual-DOM diffing. For a methodology-focused content site where time-to-interactive matters more than ecosystem breadth, this is the right tradeoff. SvelteKit also defaults to server-side rendering with progressive enhancement, which means article pages and the methodology explainer are crawlable, fast on first paint, and degrade gracefully without JavaScript.

TypeScript is non-negotiable: it matches the existing Hono API's stack, lets API response types be shared between API and frontend via a common `packages/shared-types` workspace (planned), and keeps the language count at two (TypeScript + Python) rather than three. Single-language stacks on the server side reduce mental context-switching and let the same person own changes from the frontend through the API.

### Styling: Tailwind CSS 4.x

Tailwind is installed via the official SvelteKit integration (`svelte-add tailwindcss`), which configures Vite, PostCSS, and the dev-mode HMR pipeline correctly without manual setup. Utility-first styling keeps component files self-contained; a `BiasIndicator.svelte` has its styles colocated rather than referencing a separate CSS file that drifts. This matters for a small team (one developer) maintaining a project across long timescales: separation of CSS from component logic produces cross-file coupling that's painful to evolve.

Tailwind 4.x specifically (not 3.x) for the modern engine, improved CSS variables, and the new `@theme` directive for design tokens. The bias-spectrum color palette defined in #66 is implemented as Tailwind theme variables, not arbitrary hex codes scattered across components.

### Component library: hand-built Tailwind components, Shadcn-Svelte fallback

The frontend ships a small set of hand-built components defined in `apps/web/src/lib/components/` — components like `BiasIndicator`, `SourceBadge`, `LanguageTag` are specific to this project's visual language and don't benefit from a generic library. Building them in-house keeps the component count small and aligned with the design system documented in #66.

For complex interactive primitives where reimplementing keyboard navigation, ARIA roles, and focus management would be wasteful — date pickers, comboboxes, dialogs — Shadcn-Svelte is the fallback. Shadcn-Svelte's pattern is copy-paste-and-own: components are pulled into the codebase rather than imported as runtime dependencies, which keeps the bundle lean and the component fully editable. No commitment is made to Shadcn-Svelte upfront; it's an option taken only when a specific primitive needs it.

### Data flow: SvelteKit → Hono API → Postgres

SvelteKit `+page.server.ts` files call the Hono API over HTTP. They do not import Drizzle, do not query Postgres directly, and do not duplicate database connection logic. The Hono API remains the single source of truth for data access across all consumers (frontend, scrapers' admin tooling, future mobile apps, eventual third-party integrations).

This separation matters for three reasons. First, the Hono API already exists, is tested, and has the right database access patterns — duplicating those in the SvelteKit layer would be two implementations to maintain. Second, the API layer is where caching, rate limiting, and authentication will eventually live; bypassing it from the frontend would ridicule those features. Third, this separation makes a clean deployment story: the API can be scaled, cached, or geographically distributed independently of the frontend, which is harder if the two layers share a database client.

`+page.server.ts` is the right SvelteKit primitive for this because it runs only on the server, never ships its code to the browser, and produces type-safe `data` props for the corresponding `+page.svelte`. API base URL is read from `$env/static/private` so it's bundled at build time and never leaks to the client.

### Deployment target (dev): local + Cloudflare Pages or Vercel preview

Local development uses `npm run dev` against the local Hono API (also `npm run dev`) and local Postgres (Docker Compose). This produces fast feedback loops with no external dependencies once the initial setup is done.

For preview deployments; sharing the work with non-developers, getting design feedback, or sending a URL to a potential employer — the SvelteKit app deploys to Cloudflare Pages or Vercel via GitHub integration. Either platform deploys SvelteKit with a single command, provides automatic preview URLs per branch, and offers HTTPS without configuration. The choice between them is deferred to #74 and depends on whether the Hono API also needs to be hosted (Cloudflare Workers and Vercel Edge Functions are both viable). The preview deployment is explicitly not for production — it exists exclusively for sharing, not for serving real traffic.

### Deployment target (prod): GCP via Terraform (M6)

Production deployment is part of M6 (#36) and will run on GCP or Akash Network or UpCloud alongside the API and Postgres. The whole stack — frontend, API, workers, Postgres, Redis — fits on minimalist resources comfortably until traffic justifies splitting it. These options are chosen for the same reason as the rest of the stack: cost. The project needs general infrastructure only that is available everywhere. Moving to AWS is reserved for the day scale demands it. Alternatively Akash Network and/or UpCloud are to be evaluated for this project. 

The frontend is deployed as a Node.js process behind a reverse proxy (Caddy or nginx), with the SvelteKit `node` adapter producing a standalone server. This is operationally simpler than serverless deployment for a single-VPS architecture and keeps the deployment story uniform with the API.

### Workspace location: `apps/web/`

The frontend lives at `apps/web/` in the monorepo, parallel to `apps/api/` (Hono API) and `apps/scrapers/` (Python scrapers). This naming follows the convention already established by the other workspaces and keeps the repo navigable: a new contributor sees three directories under `apps/`, can guess what each one does, and can drill into whichever is relevant.

A single monorepo with all three workspaces (rather than separate repos per layer) makes cross-workspace refactors atomic — a database schema change in scrapers can be paired with a corresponding API endpoint update and a frontend type change in one PR, rather than three coordinated PRs across three repos. The downside is a slightly larger checkout for contributors who only touch one layer, which is acceptable at the project's current scale.

### Alternatives considered

**React + Next.js**: the obvious default. Rejected for bundle size, runtime overhead, and the React ecosystem's tendency toward complexity creep (server components, suspense boundaries, RSC payloads). Next.js is excellent for teams that already know React deeply, but for a single-developer project where the goal is shipping a methodology-focused site rather than mastering a framework, SvelteKit produces equivalent results with less ceremony. React's mindshare advantage is real but didn't outweigh the operational cost for this use case.

**Astro**: strong contender for content-first sites and would have been a reasonable choice. Rejected because the project has meaningful interactivity (filter panels, score breakdowns, comparison views) that Astro handles via islands but where SvelteKit's component model is more natural. Astro's strength is "mostly-static-with-some-interactivity"; this project is "mostly-interactive-with-some-static-content," which inverts the fit.

**Remix**: another modern full-stack framework with strong SSR primitives. Rejected because Remix's data-loading model is more opinionated than SvelteKit's `+page.server.ts` pattern, and the React runtime brings the same bundle-size concerns as Next.js. Remix's nested-routing strengths don't materially help this project's relatively flat URL structure.

**SolidJS + SolidStart**: technically attractive (fine-grained reactivity, smaller bundles than React). Rejected because the ecosystem is significantly smaller than SvelteKit's, documentation is thinner, and the marginal performance gain over SvelteKit doesn't justify the reduced library availability for primitives like form handling or routing.

The rejected options aren't bad choices — they're choices that match different project shapes. The SvelteKit selection reflects the specific shape of this project (single developer, methodology-focused, modest interactivity, long maintenance horizon) rather than a claim about framework quality in general.

## Why these choices

**Why PostgreSQL over MongoDB?**
Relational data. Articles belong to sources, articles belong to clusters, articles have many scores. Joins everywhere. Mongo would be worse.

**Why Hono over NestJS / Express?**
Modern TypeScript, no decorators, runs on Bun/Node, ergonomic without enterprise-Java vibes. Better DX than Express, less magic than NestJS.

**Why Python for scrapers when TS could do it?**
`trafilatura` is the best HTML→text library, full stop. `feedparser` is the best RSS library. The Python ML/NLP ecosystem is unbeatable for the scoring/embedding layer. Don't fight the stack.

**Why Claude Haiku or Gemini over GPT?**
Strong Finnish support, transparent pricing, structured outputs that work. Sonnet 4.5 for spot-checks and prompt iteration; Haiku 4.5 for production scoring volume.

**Why Voyage AI for embeddings?**
Multilingual, better than OpenAI on non-English content per recent MTEB benchmarks. Reasonable pricing.

**Why HDBSCAN over k-means?**
Stories cluster at variable density. K-means forces fixed cluster count; HDBSCAN finds natural groupings and labels outliers as noise (which is correct behavior — not every article belongs to a story cluster).

**Why GCP over AWS?**
I have the free tier active on GCP and it has generous limits until September 2026. After 9/2026 it should be examined if GCP is still the way to go, or if another provider like Hetzner, AWS or Akash can do the job better.

**Why SvelteKit over React/Next.js for the frontend?**
Smaller bundles, simpler mental model, server-side rendering by default. The methodology-explainer pages benefit from fast first-paint and SEO crawlability; the interactive views (filters, comparison) don't need React's ecosystem breadth. Single-developer maintenance favors frameworks that minimize ceremony. The full reasoning and rejected alternatives are documented in the "Frontend (M5)" section above.

**Why AGPL over MIT?**
Prevents proprietary forks from taking the methodology private. Anyone using the code commercially must publish their modifications. This protects the public-good nature of the project.

## Scaling considerations (when relevant)

The current design works comfortably to:
- ~50 sources
- ~5,000 articles per day
- ~10,000 daily active users on the API
- One GCP VM with some RAM

Beyond that:
- Move Postgres to managed service (Hetzner managed Postgres, AWS RDS)
- Split scrapers, scoring, and API into separate hosts
- Add read replicas for Postgres
- CDN-cache cluster/story endpoints aggressively (they don't change second-to-second)

But: **don't pre-optimize.** Get to M7 first. Worry about scale when it's a problem.

## Rate limiting

Per-domain HTTP rate limiting is implemented in
`apps/scrapers/src/scrapers/rate_limit.py` as an in-process throttle
using `threading.Lock` and a domain → last-request-time dict.

Each scraper class declares `min_request_interval_seconds`. Defaults
to 2.0 seconds (30 req/min). Smaller-infrastructure sources (party
organs: Demokraatti, Kansan Uutiset, Suomenmaa, Verkkouutiset,
Suomen Uutiset) override to 5.0 seconds (12 req/min).

This is per-process state. Multiple worker processes would each have
their own throttle, doubling the effective rate.