# Lawn Command Center

Lawn care logbook + dashboard for a TTTF lawn in Topeka, KS. FastAPI + Postgres/TimescaleDB API,
Next.js web. Self-hosted on a LAN behind a reverse proxy.

**This repo is meant to be publishable.** Keep infrastructure specifics — host names, IPs, internal
domains, reverse-proxy config — *out* of it. Deployment/DNS/proxy changes belong in the homelab
repo. If you're working in the local workspace, environment and Docker context live in the
workspace `CLAUDE.md` above this repo; don't copy that content here.

## Stack (as built — verify before trusting docs)

- **API** `api/` — Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, `psycopg` v3,
  pydantic-settings, apscheduler. Installed with **`pip install -e .`** (`api/Dockerfile`).
- **Web** `web/` — Next.js 15 App Router, React 19, TypeScript strict, Tailwind v4
  (CSS config in `src/app/globals.css`, **no `tailwind.config.ts`**), shadcn style `base-nova` on
  **`@base-ui/react`**. Installed with **`npm install`**; `package-lock.json` is the lockfile.
- **DB** — `timescale/timescaledb:latest-pg16`, plus `pgcrypto`.

## Commands

Everything goes through Docker. Don't run `pytest`/`ruff`/`alembic` against the host Python — the
containers own the environment.

```bash
./ops/deploy.sh [service...]      # prod: build -> up -d -> alembic upgrade head -> ps
./ops/init-test-db.sh             # first run, and after any schema change
./ops/test.sh [-k pattern] [-x]   # pytest in the api-test container
./ops/lint.sh [--fix] [api|web]   # ruff (API) + eslint + tsc (web)
./ops/reload-env.sh [all|svc...]  # .env changes need --force-recreate, NOT docker restart
./ops/backup-db.sh                # take before any manual schema work
```

Dev stack: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`
→ web `:3001`, API `:8000`, DB `:5433`. Prod publishes no host ports (proxy reaches it over the
shared network).

Never `docker compose up` with the prod file alone by hand — use `ops/deploy.sh`.

## Conventions that bite

- **base-ui, not Radix.** Use `render={<Button />}`, never `asChild` (Button shims `asChild` →
  `render`). Pass `nativeButton={false}` when rendering a non-button. `Select` is controlled only —
  it has no `defaultValue`.
- **Copy files out of containers with `docker cp` only.** `docker exec ... cat > file` truncates
  the destination before the redirect runs. Adding a shadcn component:
  ```bash
  docker exec -it lawn-web sh -c "npx shadcn@latest add <name> --overwrite --yes"
  docker cp lawn-web:/app/src/components/ui/<name>.tsx web/src/components/ui/<name>.tsx
  ```
- `web/postcss.config.js` must stay CommonJS (`module.exports`). Don't "modernize" it to ESM.
- The dev overlay **must** set `NODE_ENV: development` or every route 500s.
- The dev overlay bind-mounts **absolute host paths**. If the daemon can't resolve them, you get
  silently-empty mounts rather than an error.
- **Config files that hold tool config must be mounted to take effect in dev.** `api/pyproject.toml`
  (ruff + pytest config) is bind-mounted into `api`/`api-test` for exactly this reason — otherwise a
  config change is invisible until the image is rebuilt, and e.g. `asyncio_mode` silently reverts to
  strict. If you add tool config to a file not already mounted, mount it too.

## Data model rules

- UUID PKs via `gen_random_uuid()` — **except hypertables**, which need a composite PK including
  the partition column (Timescale requirement).
- Enum-like columns are TEXT + CHECK, with values sourced from
  `api/src/lawn_api/models/constants.py`.
- All timestamps `timestamptz`, UTC.
- Derived values (e.g. `total_amount`) are computed at serialization, never stored.
- **Ask before running `alembic upgrade` on a non-empty database**, and take `./ops/backup-db.sh`
  first. Note the tension: `ops/deploy.sh` and `api/docker-entrypoint.sh` both run
  `alembic upgrade head` unconditionally, so migrations *do* auto-apply on deploy and container
  start. Treat writing the migration as the decision point.

## Tests

`ops/test.sh` runs against a dedicated `lawn_test` DB. Guards in `api/tests/test_api.py` refuse to
run unless `APP_ENV=test` (or `LAWN_ALLOW_DESTRUCTIVE_TESTS=1`) and refuse to TRUNCATE a DB named
`lawn` or `postgres`. `api/tests/conftest.py` rewrites `DATABASE_URL` → `*_test`.

`asyncio_mode = "auto"` is set in `api/pyproject.toml`, so async tests run without a per-test
marker. (Verify with `mode=Mode.AUTO` in the pytest header — if it says STRICT, the pyproject mount
is missing and a markerless async test would silently skip.)

## Lint / typecheck

- **One entry point:** `./ops/lint.sh` (add `--fix` to autofix, or `api`/`web` to scope).
- **API**: ruff, config in `[tool.ruff]` of `api/pyproject.toml` (line-length 120, rules
  `E,F,I,UP,B,ASYNC`, `B008` ignored for FastAPI's `Depends()`). No mypy/pyright yet.
- **Web**: ESLint 9 **flat config** (`web/eslint.config.mjs`, via `FlatCompat` wrapping
  `next/core-web-vitals` + `next/typescript`); `npm run lint` is `eslint .`, not the deprecated
  `next lint`. `npm run typecheck` is `tsc --noEmit`. No Prettier — match surrounding style rather
  than introducing a formatter unasked.
- No CI yet; `ops/lint.sh` + `ops/test.sh` are the gates, run them before committing.

## Secrets

Real values only in gitignored files: `.env`, `.env.*` (except `.env.example`), `secrets/`,
`ops/private/`, `docker-compose.override.yml`, certs/keys. `.env.example` is the contract for
required vars. Review `git status` and `git diff --staged` before any push.

`config.py` loads `.env` relative to CWD; the single root `.env` is the one the ops scripts and
compose use. (There used to be a duplicate `api/.env` — a divergence hazard — now removed; the
container never read it anyway.)

## Commits

Stage the change and propose the commit message; commit and push only once it's approved.
Conventional style (`feat:`, `fix:`, `docs:`).

**No Claude attribution** — no `Co-Authored-By: Claude ...` trailers, no "Generated with Claude"
lines, no attribution comments in code, docs, or PR bodies. Deliberate override of the default;
don't reintroduce it.

## Phase 3 (AI assistant) — named, not designed

This is the stated end goal of the project, and it's the most likely next body of work — so know
where it actually stands. The entire spec is three bullets in `docs/ROADMAP.md`: recommendations
from recorded history; explainable reasoning over weather/irrigation/treatment data; human approval
required for any recommended action. There is **no** model, provider, prompt, tool, RAG, or schema
decision yet. `.env.example` reserves an unused `ANTHROPIC_API_KEY`. Starting it is a design task
from near-zero. When building against Claude, read the `claude-api` skill first for current model
IDs and patterns.

## Remaining known gaps

Verify against code before trusting `docs/`. Most 2026-07-15 drift was fixed; what's left:

- `docs/DATA_MODEL.md` cites `docs/agent-handoffs/TASK_4_SCHEMA_DECISIONS.md` and
  `PHASE_1_5_TANK_MIXES_AND_PRODUCTS.md` as unqualified paths. Those files are real but live in the
  **private homelab** repo, so the citations resolve to nothing from here and are unreachable to
  anyone outside it. Decide: port the schema-decision history into this repo (making it
  self-contained and publishable), or re-qualify the references as deliberately private.
- `ntfy` push is hardcoded (`api/src/lawn_api/services/notifications.py` → `http://ntfy/lawn-alerts`),
  not env-configurable. Documented in `PLATFORM_DEPS.md`; making it an env var is a backlog item.
