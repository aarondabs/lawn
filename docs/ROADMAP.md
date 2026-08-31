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

## Phase 3: AI Assistant (In Progress)

- Read-only assistant: full-context Q&A chat and a scheduled briefing whose centerpiece is an
  irrigation recommendation.
- Recommendations are **agronomic reasoning applied to precisely-computed current state** (GDD,
  water balance, soil temperature, guardrail findings) plus product labels. Recorded history is
  constraint and corroboration — "have I done this, how recently, am I near a cap?" — not a
  training set; one partial season is not history to learn from.
- Deterministic services stay authoritative: the assistant reads guardrail findings, water
  balance, and coverage math from the API and never recomputes them. `cannot_evaluate` findings
  are surfaced as-is, never smoothed over.
- Human approval stays the default: the assistant recommends in prose; the operator logs
  everything manually.
