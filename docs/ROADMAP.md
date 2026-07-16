# Lawn Roadmap

## Phase 0: Platform Prep (Complete)

- Prepare code-server for dual-repo workflow.
- Configure reverse proxy route for the Lawn web service hostname.
- Verify existing homelab services remain healthy.

## Phase 1: Logbook and Dashboard (Shipped — v0.1.0)

- Scaffold backend and frontend applications. ✅
- Implement core entities for treatments, products, equipment, and zones. ✅
- Add weather and irrigation observation ingestion. ✅
- Build mobile-first quick logging flow. ✅

### Phase 1.5: Tank mixes (Shipped)

- Multi-product tank-mix logging in the Quick Log flow.

**Now:** a two-week real-use period before Phase 2 is scoped. Candidate work is parked in
`BACKLOG.md` (a parking lot, not commitments).

## Phase 2: Reliability and Integrations

- Harden background jobs and observability.
- Expand integration coverage and idempotency guarantees.
- Improve operational runbooks and backup/restore paths.

## Phase 3: Assistant Features (Future)

- Introduce recommendation workflows based on recorded history.
- Add explainable reasoning over weather, irrigation, and treatment data.
- Keep human approval as the default for any recommended action.
