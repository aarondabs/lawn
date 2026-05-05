# Lawn Architecture Decisions

This document captures the active architectural decisions for the Lawn application repository.

## Scope

- Repository scope: application code only.
- Infrastructure-specific details remain in the homelab repository.
- Phase 1 is LAN-only and does not include AI features.

## Application Stack

- Backend: Python 3.12+, FastAPI.
- Dependency management: uv (backend), pnpm (frontend).
- Frontend: Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui.
- Database: PostgreSQL 16 with TimescaleDB extension.
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
