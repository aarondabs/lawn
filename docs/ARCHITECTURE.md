# Lawn Architecture Decisions

This document captures the active architectural decisions for the Lawn application repository.

## Scope

- Repository scope: application code only.
- Infrastructure-specific details remain in the homelab repository.
- Phase 1 is LAN-only and does not include AI features.

## Application Stack

- Backend: Python 3.12+, FastAPI.
- Dependency management: **pip** with `pyproject.toml` (backend, `pip install -e ".[dev]"`);
  **npm** with `package-lock.json` (frontend). (There is no uv lockfile and no pnpm — an earlier
  draft of this doc claimed both; it was never true.)
- Frontend: Next.js 15 App Router, React 19, TypeScript (strict), Tailwind CSS v4 (CSS-based config
  in `src/app/globals.css`, no `tailwind.config.ts`), shadcn/ui on `@base-ui/react` (style
  `base-nova`).
- Database: PostgreSQL 16 with TimescaleDB extension, plus `pgcrypto`.
- Lint/typecheck: ruff (config in `api/pyproject.toml`), ESLint 9 flat config
  (`web/eslint.config.mjs`), `tsc --noEmit`. One entry point: `./ops/lint.sh`.
- ORM and migrations: SQLAlchemy 2.x, Alembic.

## Runtime Model

- Services run on the NUC via Docker Compose.
- Reverse proxy is provided by Caddy in homelab.
- Expected LAN app hostname should be configured via environment or local DNS (example: lawn.example.internal).

## Networking

- App web and api containers should join the external homelab network for proxy service discovery.
- Database should remain on a private internal app network.

## Security and Secrets

- Real secrets remain in local server files that are gitignored.
- .env.example documents required variables with placeholders only.
- No credentials or internal host/IP details are committed to this repository.

## Future AI Work

- AI capabilities are explicitly deferred until after the Phase 1 logbook/dashboard baseline is complete.
