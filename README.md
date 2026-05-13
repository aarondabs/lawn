# Lawn Command Center

Personal lawn care logbook and dashboard for a TTTF lawn in Topeka, KS. Tracks treatments, cultural practices, irrigation, weather, soil tests, and reminders. Served on the LAN at `lawn.home.daber.co`.

## Decision docs

- Architecture decisions for this repo: `docs/ARCHITECTURE.md`
- Homelab integration requirements: `docs/PLATFORM_DEPS.md`
- Planned delivery phases: `docs/ROADMAP.md`

The original cross-repo handoff remains in the homelab repository as platform history. This repo keeps an app-focused summary so contributors do not need access to private infrastructure docs.

## Security-first workflow

- Keep real secrets only in local files on the server.
- Commit only example/template values.
- Use `.env.example` as the contract for required variables.
- Keep homelab-specific deployment details out of this repo.

## Local files that must stay out of git

- `.env` and `.env.*` (except `.env.example`)
- `secrets/`
- `ops/private/`
- `docker-compose.override.yml`
- certificate and key files

## First-time setup

1. Copy `.env.example` to `.env`.
2. Set real values in `.env`.
3. Build the app and run locally.
4. Commit only non-sensitive source and docs.

## Compose foundation

- `docker-compose.yml` is the main runtime file.
- `docker-compose.dev.yml` is the development overlay.
- Main compose does not publish Lawn web on host port 3000.
- Dev overlay publishes web on host 3001 to avoid host port conflicts.

### Bring up dev stack

1. `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`
2. API health: `http://localhost:8000/health`
3. Web app: `http://localhost:3001`

### Bring down

1. `docker compose -f docker-compose.yml -f docker-compose.dev.yml down`

### Reload env changes

When you update `.env`, a plain container restart is not enough. Recreate the container so new environment values are injected.

1. `./ops/reload-env.sh`
2. Optional full stack recreate: `./ops/reload-env.sh all`
3. Optional specific services: `./ops/reload-env.sh api web`

## Safe testing workflow

Tests are configured to run against a dedicated test database, not the live app database.

1. Initialize or migrate the test DB:
	`./ops/init-test-db.sh`
2. Run tests:
	`cd api && ./.venv/bin/pytest -q`

If you run tests from the host shell, set `TEST_DATABASE_URL` to the host-exposed DB port, for example:

`TEST_DATABASE_URL=postgresql+psycopg://lawn:<password>@localhost:5433/lawn_test ./.venv/bin/pytest -q`

Test safety guards are enforced in `api/tests/test_health_placeholder.py`:

- Destructive fixture logic refuses to run unless `APP_ENV=test` or an explicit override is set.
- It also refuses to truncate `lawn` or `postgres` DB names unless explicitly overridden.

## Database backups

Nightly backup and restore scripts:

1. Create backup now:
	`./ops/backup-db.sh`
2. Install nightly cron job (default: `03:30`):
	`./ops/install-db-backup-cron.sh`
3. Restore from backup:
	`./ops/restore-db.sh /path/to/backup.sql.gz`

Backups are written to `ops/private/db-backups` and rotated with 14-day retention by default.

## Publishing this repository

1. Create a new public repo on GitHub.
2. Add that remote URL to this local repo.
3. Push after reviewing `git status` and `git diff --staged` for secrets.
