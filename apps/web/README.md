User-facing frontend for Finnish Bias Tracker. Consumes the Hono API
(`apps/api/`) and renders the article list, filters, article detail page,
source comparison, and methodology explainer.

## Stack

- SvelteKit 2.x with TypeScript
- Tailwind CSS 4.x for styling
- mdsvex for markdown-driven content (methodology page in #71)
- Vitest for unit tests, with optional browser-mode component testing via
  Playwright (Chromium installed via `npx playwright install chromium`)
- Prettier + ESLint for formatting and linting

See `docs/architecture.md` (repo root) for the architectural reasoning.

## Setup

```bash
# From repo root — workspaces install happens here, not from inside apps/web/
cd ~/Desktop/Finnish-Bias-Tracker
npm install

# Browser binaries for Vitest browser-mode tests (one-time, ~150MB)
cd apps/web
npx playwright install chromium

# Local env config
cp .env.example .env
# Edit .env if your local Hono API runs on a port other than 3000
```

## Development

All commands run from `apps/web/`:

```bash
npm run dev          # start dev server on http://localhost:5173
npm run build        # production build
npm run preview      # serve the production build locally
npm run lint         # ESLint + Prettier check
npm run format       # apply Prettier formatting
npm run check        # svelte-check (type checking)
npm run test         # Vitest (server + browser projects)
npm run test:unit    # Vitest in watch mode
```

You can also run these from the repo root using the workspace aliases:

```bash
npm run dev:web      # equivalent to: npm run dev --workspace=apps/web
```

## Environment variables

See `.env.example` for required variables.

- `API_URL` — Hono API base URL. Server-side only; used by `+page.server.ts`
  loaders. Defaults to `http://localhost:3000` for dev.
- `PUBLIC_SITE_URL` — public URL of the deployed frontend, used for
  canonical links and OpenGraph tags. Optional in dev, required in prod.

Note: only `PUBLIC_*` variables are exposed to client-side code. `API_URL`
is server-only and never reaches the browser.

## Project structure

apps/web/
├── src/
│   ├── routes/              # SvelteKit file-based routing
│   │   ├── +layout.svelte   # root layout (imports Tailwind)
│   │   └── +page.svelte     # homepage
│   ├── lib/
│   │   ├── components/      # shared components (defined in #66)
│   │   ├── server/          # server-only helpers (API client)
│   │   └── vitest-examples/ # scaffolder-provided example tests
│   ├── app.css              # Tailwind entry point
│   └── app.html             # HTML shell
├── static/                  # static assets (favicon, robots.txt, etc.)
├── tailwind.config.ts
├── svelte.config.js
├── vite.config.ts
└── package.json

## Talking to the Hono API

The frontend never queries Postgres directly. All data access goes
through the Hono API at `apps/api/`. SvelteKit `+page.server.ts` files
use the `API_URL` env var to call API endpoints:

```ts
// src/routes/+page.server.ts (example, will be built in #67)
import { API_URL } from '$env/static/private';

export async function load({ fetch }) {
  const res = await fetch(`${API_URL}/api/articles?limit=20`);
  return { articles: await res.json() };
}
```

The API contract is documented in `apps/api/` and matches the schema
in `docs/architecture.md`.

## Why SvelteKit (and not React/Next.js)

See `docs/architecture.md` → "Frontend (M5)" section. Short version:
smaller bundle, server-side rendering by default, simpler component
model, single-developer maintenance fits the project's scale.

## Known gotchas

- **Workspace installs**: always run `npm install` from the repo root,
  never from inside `apps/web/`. Running it locally produces a
  half-populated `node_modules` because npm workspaces hoist deps to
  the root level. If you see "Cannot find package 'vite'" errors, you
  ran install from the wrong directory — delete `node_modules/` and
  reinstall from root.
- **Playwright browser binaries**: required for Vitest's browser-mode
  test project. Run `npx playwright install chromium` once after the
  first clone. CI handles this via a separate workflow step.