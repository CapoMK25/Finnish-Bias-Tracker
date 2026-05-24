# Finnish Media Bias Tracker

> A transparent, open-source tool that aggregates Finnish news across the political spectrum, scores articles for bias, and reveals coverage blindspots. Inspired by [Ground News](https://ground.news), but built specifically for the Finnish media landscape right now in 2026.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange.svg)]()

## Why this exists

Finnish media has unique characteristics that international bias trackers don't capture:

- **Party-organ press is still openly active** — Kansan Uutiset (Left Alliance), Demokraatti (SDP), Verkkouutiset (Kokoomus), Suomen Uutiset (Perussuomalaiset), Suomenmaa (Keskusta).
- **Yle's role as state broadcaster** creates a distinct trust/bias dynamic absent from US-style analysis.
- **Swedish-language media** (HBL, Svenska Yle) often diverges politically from Finnish-language coverage of the same events.
- **Topic-specific bias** matters more than source-level labels — an outlet might be centrist on EU policy but right-leaning on immigration.

This project aims to make all of that visible.

## What it does

- **Aggregates articles** from major Finnish news sources in real time
- **Clusters articles** by story (multiple outlets covering the same event)
- **Scores each article** for political bias using a transparent, documented methodology
- **Surfaces blindspots** — stories that only one side covers
- **Tracks framing differences** — how the same event is reported across the spectrum
- **Distinguishes source-level bias** (ownership, party affiliation) from **article-level bias** (per-piece language, framing, source diversity)

## Methodology

Full methodology documented in [`docs/methodology.md`](docs/methodology.md). Highlights:

- **Hard labels** (immutable, factual): party-organ status, ownership structure
- **Soft labels** (analytical, per-article): bias direction, confidence score, loaded language examples
- **Transparency**: all prompts, scoring rubrics, and source classifications are public
- **Auditability**: full LLM scoring rationale stored with every article

## Source classifications (initial)

See [`docs/sources.md`](docs/sources.md) for the complete annotated source list with reasoning.

| Bias bucket | Representative sources |
|-------------|------------------------|
| Left | Kansan Uutiset, Demokraatti, Long Play |
| Center-Left | Yle, Helsingin Sanomat, Suomen Kuvalehti |
| Center | STT, MTV Uutiset, Suomenmaa, Kauppalehti |
| Center-Right | Iltalehti, Ilta-Sanomat, Talouselämä, Verkkouutiset |
| Right | Suomen Uutiset |
| Flagged (not aggregated) | MV-lehti, Magneettimedia |

## Tech stack

- **Backend**: TypeScript + [Hono](https://hono.dev) (no NestJS)
- **Database**: PostgreSQL + [Drizzle ORM](https://orm.drizzle.team)
- **Cache/Queue**: Redis + [BullMQ](https://docs.bullmq.io)
- **Scrapers**: Python (`feedparser`, `trafilatura`)
- **LLM scoring**: Anthropic Claude API (Haiku for scale, Sonnet for spot-checks)
- **Clustering**: Voyage AI embeddings + HDBSCAN
- **Frontend**: SvelteKit + TailwindCSS + shadcn-svelte
- **Infrastructure**: Docker Compose (dev) → Hetzner VPS (prod) → AWS/Akash/UpCloud (if/when scale demands)
- **IaC**: Terraform

## Project status

**Pre-alpha.** Methodology and architecture are being finalized. No production data yet.

### Current milestone: M0 — Foundation
- [x] Project scaffold
- [ ] Methodology document (v1)
- [ ] Source list with bias classifications (v1)
- [ ] Database schema design
- [ ] LLM prompt v1 + evaluation rubric

See [`docs/roadmap.md`](docs/roadmap.md) for the full roadmap.

## Getting started

### Prerequisites

- Node.js 20+ (or [Bun](https://bun.sh) 1.1+)
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Docker + Docker Compose
- An [Anthropic API key](https://console.anthropic.com)

### Local development

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/finnish-bias-tracker.git
cd finnish-bias-tracker

# Copy environment template
cp .env.example .env
# Edit .env with your API keys and local config

# Start Postgres + Redis via Docker
docker compose -f docker-compose.dev.yml up -d

# Install dependencies (TypeScript workspaces)
npm install

# Set up Python scraper environment
cd apps/scrapers
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ../..

# Run database migrations
npm run db:migrate

# Start the API
npm run dev:api

# In another terminal, start the frontend
npm run dev:web

# In another terminal, run scrapers
cd apps/scrapers && python -m scrapers.run
```

Visit `http://localhost:5173` for the frontend, `http://localhost:3000` for the API.

## Project structure

```
finnish-bias-tracker/
├── apps/
│   ├── api/            # Hono backend (TypeScript)
│   ├── web/            # SvelteKit frontend
│   └── scrapers/       # Python scrapers + LLM scoring workers
├── packages/
│   └── shared/         # Shared TypeScript types (used by api + web)
├── docs/
│   ├── methodology.md  # How bias is determined
│   ├── sources.md      # Annotated source list
│   ├── roadmap.md      # Development phases
│   └── architecture.md # System architecture
├── infra/
│   └── terraform/      # Production infrastructure as code
├── docker-compose.dev.yml
└── .github/workflows/  # CI/CD
```

## Contributing

Pre-alpha. Not accepting code contributions yet, but **feedback on methodology is highly welcome** — open an issue.

Especially valuable contributions:
- Finnish journalists or media researchers willing to review source classifications
- Native Finnish speakers willing to audit LLM bias scoring outputs
- Anyone with relevant academic background in media studies

## License

[AGPL-3.0](LICENSE). Forks must remain open source. The methodology and prompts are intentionally fully public to allow auditability.

## Disclaimer

This tool provides analytical perspectives on news coverage. Bias scores are **not absolute truth claims** — they reflect a documented methodology applied consistently. Users are encouraged to read the methodology, inspect the data, and form their own conclusions. AI-generated bias scores are clearly labeled as such, per EU AI Act transparency requirements.

## Contact

Issues and discussions: GitHub Issues
