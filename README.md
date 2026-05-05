# Lawn

Initial scaffold for a public app repository with local-only server secrets.

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

## Publishing this repository

1. Create a new public repo on GitHub.
2. Add that remote URL to this local repo.
3. Push after reviewing `git status` and `git diff --staged` for secrets.
