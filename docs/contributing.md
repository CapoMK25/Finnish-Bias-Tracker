# Contributing

Finnish Bias Tracker is open source under AGPL-3.0. This document describes how the project is built, the conventions in use, and the workflow for proposing changes.

The project is currently maintained by one person ([@CapoMK25](https://github.com/CapoMK25)). External contributions are welcome but rare. This document exists to keep that consistent as the project grows.

## What this project is

A monitoring tool for political bias in Finnish news. It scrapes almost 20 sources, scores each article using an LLM, and surfaces patterns of coverage and blindspots across the political spectrum. The methodology is documented in `docs/methodology.md` and is the reference for editorial decisions.

The project is split into three workspaces under `apps/`:

- **`apps/api/`** — TypeScript backend (Hono on Node 20+, Drizzle ORM, BullMQ scheduler)
- **`apps/scrapers/`** — Python 3.12 scrapers + Gemini scoring + BullMQ worker
- **`apps/web/`** — SvelteKit 2 frontend (Svelte 5 runes, TailwindCSS, shadcn-svelte)

Shared infrastructure: PostgreSQL 16 (with pgvector for M3), Redis 7.

## Before you contribute

Please read these in order:

1. **`README.md`** — project overview, local setup
2. **`docs/methodology.md`** — how bias scoring works, why decisions were made
3. **`docs/sources.md`** — the source list with bias classifications and reasoning
4. **`docs/roadmap.md`** — phased plan, current milestone, what's intentionally out of scope

If a contribution conflicts with the methodology document, the contribution is wrong by default — propose a methodology change first, then implement.

## Local development setup

The full setup steps are in `README.md`. Quick reference:

```bash
# Postgres + Redis via Docker
docker compose -f docker-compose.dev.yml up -d

# API (Node 20+, npm 10+)
cd apps/api
npm install
npm run db:migrate
npm run db:seed
npm run dev

# Scrapers (Python 3.12+)
cd apps/scrapers
python -m venv .venv
source .venv/bin/activate    # bash/zsh; .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m src.run --source yle --limit 10

# Frontend
cd apps/web
npm install
npm run dev
```

You'll need a Google Cloud project with Vertex AI enabled for LLM scoring. See `docs/architecture.md` for auth setup.

## Code conventions

### TypeScript (apps/api, apps/web)

- **Strict mode is non-negotiable** — `tsconfig.json` has `"strict": true`. Don't disable it locally.
- **ESM imports require explicit `.js` extensions** even when importing `.ts` files. Drizzle/Hono/Node ESM resolution doesn't infer extensions.
- **No barrel files (`index.ts` re-exports).** Import from the actual source file. Barrels slow type-checking and obscure dependency graphs.
- **No `any`.** If you genuinely need an escape hatch, use `unknown` and narrow with a type guard.
- **Database access goes through Drizzle.** Raw SQL via `db.execute(sql\`...\`)` is acceptable for monitoring queries and complex aggregations where Drizzle's query builder would be more code than the SQL. Document why if you do this.

### Python (apps/scrapers)

- **Python 3.12+ only.** PEP 604 syntax (`X | None`), `match` statements, dataclasses.
- **Type hints required on public functions.** Internal helpers can be untyped where it would be noise.
- **Ruff is the formatter and linter.** Run `ruff format src && ruff check src` before committing.
- **No `print()` in production code paths.** Use `structlog` (already wired). `print()` is fine in CLI entry points like `inspect.py` where the output is intentional human-facing.
- **Scrapers extend `BaseScraper`** and override the minimum necessary. The base class handles fetch, throttle, extract, and dedup. New scrapers should be 20-40 lines.

### Svelte (apps/web)

- **Svelte 5 runes mode** (`$state`, `$derived`, `$props`, `$effect`). No `$:` reactive statements, no `export let`.
- **Components are kebab-case files** (`bias-ribbon.svelte`) with PascalCase named exports (`BiasRibbon`).
- **Use shadcn-svelte components** where possible. Don't reinvent buttons, dialogs, etc.
- **TailwindCSS for styling.** No CSS-in-JS, no separate stylesheets except global resets.

### SQL / database

- **Drizzle migrations are the source of truth** for the schema. Edit the schema in `apps/api/src/db/schema.ts`, then `npm run db:generate` to produce the migration, then commit both.
- **Column names use `snake_case`.** Drizzle's TypeScript types automatically camelCase them in code; the wire format stays snake.
- **Timestamps are explicit about meaning.** `scraped_at` (when the scraper saw the article), `scored_at` (when the LLM finished), `created_at` (when the row landed in DB). Don't conflate them.

## Git workflow

### Branches
main                              # always deployable
feat/<short-description>          # new features
fix/<short-description>           # bug fixes
docs/<short-description>          # documentation only
chore/<short-description>         # tooling, dependencies, CI
<issue-number>-<short-description>  # tied to a specific GitHub issue

### Commits

The project uses [Conventional Commits](https://www.conventionalcommits.org/). Examples from the existing history:
feat(scrapers): per-source HTTP rate limiting
fix(scoring): validate GCP_PROJECT_ID, not GEMINI_API_KEY
docs: add CONTRIBUTING.md
chore: bump redis to 6.4.0 to satisfy bullmq dependency

Use the imperative mood ("add", not "added"). Keep the subject under 72 characters. Wrap the body at ~80 characters.

Most commit messages should explain **why**, not what. The diff already shows what. The body should explain the decision: what was tried, what alternatives were rejected, what trade-offs were accepted.

### Pull requests

Open one PR per logical change. Each PR should:

1. Reference the issue it closes (`Closes #N`)
2. Describe what changed and why in the PR body — not just the commit message
3. Pass CI (lint, format, type-check, smoke tests)
4. Include any necessary docs updates in the same PR

A good PR description follows this structure:

```markdown
## What changed
Brief summary of the change.

## Why
The motivation. What problem does this solve? What alternatives were considered?

## What this PR does NOT include
Out-of-scope items explicitly deferred. Helps reviewers understand boundaries.

## Architectural notes
Decisions worth flagging for future readers.

## Testing
How the change was verified.
```

Examples of well-written PRs in this repo: #12 (persistence), #21 (BullMQ queue), #22 (worker). Read them to match the tone.

### CI

GitHub Actions runs on every push and PR:

- **TypeScript checks** — `tsc --noEmit`, lint via `eslint`, format check via `prettier --check`
- **Python checks** — `ruff check`, `ruff format --check`, `mypy` (non-blocking)
- **Integration smoke test** — Docker stack up, migrate, seed, hit a few endpoints

All checks must pass before merge.

## Adding a new source

Adding a Finnish news source is one of the most common contribution types. Steps:

1. **Edit `docs/sources.md`** to document the source, its bias classification, and the reasoning. This is the most important step — the methodology decision should be made and documented before any code.
2. **Add the source row to the seed** at `apps/api/src/db/seed.ts`.
3. **Create the scraper** at `apps/scrapers/src/scrapers/<slug>.py`, extending `BaseScraper`.
4. **Register it in the worker dispatch** at `apps/scrapers/src/worker/dispatch.py` and in `apps/scrapers/src/run.py`'s `SCRAPERS` dict.
5. **Test locally** with `python -m src.run --source <slug> --limit 5`.
6. **Verify in the DB** that articles persist with the right `source_id`.
7. **Adjust the rate limit** if the source has small infrastructure — override `min_request_interval_seconds` on the scraper class.

A scraper PR should be one cohesive change including methodology doc, seed, scraper, dispatch, and a test run summary in the PR description.

## Challenging a bias classification

If you disagree with how a source is classified in `docs/sources.md`, open an issue tagged `source-review` with:

1. The source and its current classification
2. Your proposed reclassification
3. Specific evidence — articles, ownership facts, editorial statements, JSN rulings

Bias classification changes are editorial decisions, not engineering ones. The methodology document is the rulebook. If you think the rulebook is wrong, propose a methodology change first.

## Reporting bugs

Open an issue with:

1. What you did
2. What you expected
3. What actually happened
4. Your environment (OS, Node version, Python version)
5. Relevant logs

Bugs in scraping are common — Finnish news sites change their RSS structure regularly. Include the URL of the failing source if possible.

## Security issues

Don't open public issues for security vulnerabilities. Email [capomk@protonmail.com] directly. The project doesn't yet have a formal security policy; that's coming up in a future issue.

## Questions and discussion

GitHub Discussions is enabled on the repo for general questions. For methodology questions specifically, comment on `docs/methodology.md`'s associated issue thread, or open a new discussion in the "Methodology" category.

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0, the same license as the project. The AGPL ensures that derivatives — including hosted services using this code — must also be open source. This is intentional. The bias tracker's credibility depends on its transparency; a proprietary fork would undermine that.

If you're contributing on behalf of an organization, ensure you have authority to do so under your employment agreement. AGPL is incompatible with many corporate IP assignment policies.