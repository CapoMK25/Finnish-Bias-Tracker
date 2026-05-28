# Commands

Cheat sheet of commands used across the project. Organized by task.

All commands assume you're at the repo root (`~/Desktop/Finnish-Bias-Tracker` or wherever you cloned). If a command needs a different directory, it's stated explicitly.

---

## First-time setup (new machine)

### Pop!_OS / Ubuntu

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev build-essential libpq-dev curl docker.io docker-compose-v2
sudo usermod -aG docker $USER
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
newgrp docker  # apply docker group without logout
```

### macOS

```bash
brew install python@3.12 node@20 git
brew install --cask docker  # open Docker Desktop once after install to start the daemon
```

### After OS-level install (both platforms)

```bash
git clone git@github.com:CapoMK25/Finnish-Bias-Tracker.git
cd Finnish-Bias-Tracker

# Create .env from template, fill in API keys
cp .env.example .env
nano .env  # add GEMINI_API_KEY at minimum

# Python deps
cd apps/scrapers
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
cd ../..

# Node deps (npm workspaces, run from repo root)
npm install

# Start infra
docker compose -f docker-compose.dev.yml up -d

# DB schema + seed
cd apps/api
npm run db:migrate
npm run db:seed
cd ../..
```

Verify everything works:

```bash
cd apps/api && npm run dev
# In another terminal:
curl http://localhost:3000/api/sources | head
```

---

## Daily development routine

### Start the stack

```bash
cd ~/Desktop/Finnish-Bias-Tracker
docker compose -f docker-compose.dev.yml start
```

### Activate Python venv

```bash
cd apps/scrapers
source .venv/bin/activate
```

Quick shell alias to skip the typing — add to `~/.zshrc` or `~/.bashrc`:

```bash
alias bias='cd ~/Desktop/Finnish-Bias-Tracker/apps/scrapers && source .venv/bin/activate'
```

Then just type `bias`.

### Start the API server

```bash
cd ~/Desktop/Finnish-Bias-Tracker/apps/api
npm run dev
```

Leave running in its own terminal. Auto-reloads on file changes.

### Stop everything

```bash
# In the npm run dev terminal: Ctrl+C
cd ~/Desktop/Finnish-Bias-Tracker
docker compose -f docker-compose.dev.yml stop
```

`stop` preserves data. `down` removes containers (data persists in volumes). `down -v` nukes data too. Use `stop` 99% of the time.

---

## Docker

### Status

```bash
docker ps                                                # running containers
docker compose -f docker-compose.dev.yml ps              # this project only
docker compose -f docker-compose.dev.yml logs postgres   # logs for one service
docker compose -f docker-compose.dev.yml logs -f         # follow all logs
```

### Reset Postgres data (nuclear option)

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
cd apps/api && npm run db:migrate && npm run db:seed
```

### Shell into a container

```bash
docker exec -it bias_tracker_postgres bash
docker exec -it bias_tracker_redis sh
```

---

## Database (Postgres)

### Connect via psql

```bash
docker exec -it bias_tracker_postgres psql -U bias_tracker -d bias_tracker_dev
```

### One-off SQL query

```bash
docker exec -it bias_tracker_postgres psql -U bias_tracker -d bias_tracker_dev -c "SELECT slug, bias_score FROM sources ORDER BY bias_score;"
```

### List tables, inspect schema

```bash
# Inside psql:
\dt              # list tables
\d sources       # describe one table
\q               # quit
```

### Drizzle migrations

Run from `apps/api/`:

```bash
npm run db:generate   # generate new migration from schema changes
npm run db:migrate    # apply pending migrations
npm run db:seed       # insert the 17 Finnish news sources
npm run db:studio     # GUI at https://local.drizzle.studio
```

---

## Redis

Not actively used yet, but to inspect:

```bash
docker exec -it bias_tracker_redis redis-cli
```

Inside redis-cli:

PING               # should return PONG
KEYS *             # list all keys (don't run in prod, slow)
FLUSHDB            # delete all keys in current db

---

## Python (scrapers)

All commands below assume venv is active (`source .venv/bin/activate`) and CWD is `apps/scrapers/`.

### Run the scraper

```bash
python -m src.run
```

### Lint / format

```bash
ruff check src              # report issues
ruff check --fix src        # auto-fix safe issues
ruff check --fix --unsafe-fixes src   # auto-fix everything (use carefully)
ruff format src             # apply formatter
ruff format --check src     # check only, don't modify (CI mode)
```

### Type-check

```bash
mypy src
```

### Test (when tests exist)

```bash
pytest
pytest -k test_name         # run specific test
pytest -v                   # verbose
```

### Cache management

```bash
ls ~/.cache/finnish-bias-tracker/scores/         # see what's cached
ls ~/.cache/finnish-bias-tracker/scores/ | wc -l # count cached scores
rm -rf ~/.cache/finnish-bias-tracker/scores/     # nuke cache
```

### Invalidate cache for a new prompt version

Edit `apps/scrapers/src/prompts/bias_scoring.py`, change `PROMPT_VERSION = "v1.0"` to `"v1.1"`. Cache files keyed under the old version become invisible. Next run re-scores.

---

## TypeScript (API)

All commands below assume CWD is `apps/api/`.

### Dev server (auto-reload)

```bash
npm run dev
```

### Type-check without building

```bash
npx tsc --noEmit -p tsconfig.json
```

### Build

```bash
npm run build
```

### Start built version

```bash
npm run start
```

### Install / update deps

```bash
npm install              # from repo root, installs all workspaces
npm install --workspace=apps/api <package>   # add to one workspace
```

---

## API testing (Bruno)

```bash
# Open the desktop app and load the collection from ./bruno/
# Or with the CLI:
npm install -g @usebruno/cli
cd bruno
bru run . --env local
```

### Quick curl checks

```bash
curl http://localhost:3000/health
curl http://localhost:3000/api/sources | jq
curl http://localhost:3000/api/sources/yle | jq
curl http://localhost:3000/api/stories | jq
```

---

## Git workflow

### Standard PR flow

```bash
git checkout main
git pull
git checkout -b feat/something-descriptive

# ... do work ...

git add .
git status                        # always verify before commit
git commit -m "feat: ..."
git push -u origin feat/something-descriptive

# Open PR via GitHub UI, or:
gh pr create --base main --title "..." --body "Closes #N"
```

### After PR merges

```bash
git checkout main
git pull
git branch -d feat/something-descriptive
```

### Useful inspections

```bash
git status                        # what's changed
git diff                          # see unstaged changes
git diff --staged                 # see staged changes
git log --oneline -10             # recent commits
git log --oneline path/to/file    # commits touching one file
```

### Emergency unstage / unrevert

```bash
git restore --staged <file>       # unstage but keep changes
git restore <file>                # discard local changes (DANGEROUS)
git reset --soft HEAD~1           # undo last commit, keep changes staged
```

---

## CI / GitHub Actions

### Re-run a failed workflow

Either:
- Click "Re-run jobs" in the GitHub Actions UI
- Push an empty commit: `git commit --allow-empty -m "ci: rerun" && git push`

### Check CI status from CLI

```bash
gh run list                       # recent runs
gh run watch                      # watch the latest run live
```

---

## Troubleshooting quickies

### Python: "Import could not be resolved" in VSCode

VSCode is using the wrong Python interpreter.
- `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Linux)
- Type `Python: Select Interpreter`
- Pick `apps/scrapers/.venv/bin/python`

### TypeScript: "Cannot find name 'process' / 'console'"

`@types/node` not configured. Ensure `tsconfig.json` has `"types": ["node"]`.
For files outside `src/` (like `drizzle.config.ts`), add `/// <reference types="node" />` at the top.

### Docker: "permission denied" on Linux

You haven't applied docker group membership yet.
```bash
newgrp docker
# Or log out and back in.
```

### Postgres: "relation does not exist"

Migrations haven't run.
```bash
cd apps/api && npm run db:migrate
```

### Gemini: 429 RESOURCE_EXHAUSTED

You hit the free tier limit. Either:
- Wait (daily resets ~10:00 Helsinki time)
- Switch to Flash-Lite: set `GEMINI_SCORING_MODEL=gemini-2.5-flash-lite` in `.env`
- Enable billing on your Google Cloud project

### "No such file or directory" on heredoc-style commands

Your shell paste mangled the multi-line command (common with middle-click paste). Use `Ctrl+Shift+V` instead, or save commands to a temp file:
```bash
nano /tmp/cmd.sh
bash /tmp/cmd.sh
```

---

## Environment variables (reference)

All loaded from `.env` at repo root. Never commit `.env`.

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | Postgres connection | `postgresql://bias_tracker:dev_password_change_in_prod@localhost:5432/bias_tracker_dev` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379` |
| `LLM_PROVIDER` | Which scorer to use | `gemini` |
| `GEMINI_API_KEY` | Google AI Studio key | (required for scoring) |
| `GEMINI_SCORING_MODEL` | Gemini model variant | `gemini-2.5-flash-lite` |
| `ANTHROPIC_API_KEY` | Anthropic key (fallback) | (empty) |
| `VOYAGE_API_KEY` | Voyage AI for embeddings | (empty, M3+) |
| `API_PORT` | API server port | `3000` |
| `LLM_PROMPT_VERSION` | Cache invalidation key | `v1.0` |