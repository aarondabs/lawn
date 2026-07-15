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

`docs/ARCHITECTURE.md` claims "uv (backend), pnpm (frontend)". **That is false** — it's pip and
npm. Several docs have drifted; see "Known doc drift" below.

## Commands

Everything goes through Docker. Don't run `pytest`/`alembic` against the host Python.

```bash
./ops/deploy.sh [service...]      # prod: build -> up -d -> alembic upgrade head -> ps
./ops/init-test-db.sh             # first run, and after any schema change
./ops/test.sh [-k pattern] [-x]   # pytest in the api-test container
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

No `asyncio_mode` is configured — async tests need an explicit `@pytest.mark.asyncio` and
`@pytest_asyncio.fixture`, or they silently misbehave.

## Lint / typecheck — mostly absent

- **API**: ruff is a dev dep but has **no config section and no documented command**. Effective:
  `cd api && ./.venv/bin/ruff check .`. No mypy/pyright, no pre-commit, no CI.
- **Web**: `npm run lint` → `next lint`, configured via **legacy `.eslintrc.json` under ESLint 9**
  (no flat config). `next lint` is deprecated in Next 15.5 and gone in 16 — this breaks on the next
  major. **No typecheck script**; type errors only surface via `next build`. No formatter.

Match surrounding style rather than introducing a formatter unasked.

## Secrets

Real values only in gitignored files: `.env`, `.env.*` (except `.env.example`), `secrets/`,
`ops/private/`, `docker-compose.override.yml`, certs/keys. `.env.example` is the contract for
required vars. Review `git status` and `git diff --staged` before any push.

Note: `api/.env` is currently byte-identical to the root `.env`, and `config.py` loads `.env`
relative to CWD — so which one wins depends on where you run from. Silent divergence hazard.

## Commits

Stage the change and propose the commit message; commit and push only once it's approved.
Conventional style (`feat:`, `fix:`, `docs:`).

**No Claude attribution** — no `Co-Authored-By: Claude ...` trailers, no "Generated with Claude"
lines, no attribution comments in code, docs, or PR bodies. Deliberate override of the default;
don't reintroduce it.

## Known doc drift

Verify against code before trusting `docs/`. Confirmed wrong today:

- `ARCHITECTURE.md` — "uv / pnpm" (it's pip / npm).
- `README.md` — points test guards at `api/tests/test_health_placeholder.py`, which doesn't exist
  (they're in `test_api.py` + `conftest.py`); and suggests running pytest on the host, which
  `OPERATIONS.md` explicitly forbids.
- `DATA_MODEL.md` — cites `docs/agent-handoffs/TASK_4_SCHEMA_DECISIONS.md` and
  `PHASE_1_5_TANK_MIXES_AND_PRODUCTS.md` as unqualified paths, so they read as lawn-relative and
  resolve to nothing. Those files are real but live in the **homelab** repo, which is private —
  meaning every schema decision's cited source is unreachable to anyone outside it. Either
  re-qualify the references as cross-repo or port the decisions into this repo.
- `ROADMAP.md` — still marks Phase 1 "Current"; Phase 1.5 shipped.
- `BACKLOG.md` — calls the Phase 3 AI assistant "already planned". It is **named, not designed**:
  the entire spec is three bullets in `ROADMAP.md` (recommendations from recorded history,
  explainable reasoning over weather/irrigation/treatment data, human approval required for any
  recommended action). No model, provider, prompt, tool, or schema decisions exist yet.
- `OPERATIONS.md` and `web/next.config.mjs` still contain an internal domain, contradicting this
  repo's own no-internal-details rule.
- `web/components.json` references `tailwind.config.ts`, which doesn't exist (Tailwind v4).
- `ntfy` is a hard dependency — `api/src/lawn_api/services/notifications.py` hardcodes a service
  URL — but it's absent from `docs/PLATFORM_DEPS.md` and isn't configurable by env.
