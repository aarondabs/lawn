# Lawn App Backlog

Captured candidates and ideas. **This is a parking lot, not a roadmap.** Items here are not committed to. Phase 2 scoping happens after the two-week real-use period.

## Confirmed Phase 2 candidates

### Trees and shrubs tracking
- Goal: track treatments (fungicide, bagworm control, etc.) for trees and shrubs separately from lawn.
- Open design questions: per-plant vs. per-group vs. per-bed modeling; how to relate to the existing 3 drip irrigation zones already in `irrigation_zone`; whether to share `treatment` schema or create a separate woody-plant table.
- Use cases: bagworm treatments on evergreens, fungal treatments on shrubs, AI-driven watering schedule for woody plants.

### Drip zone display on dashboard
- Currently the 3 drip zones (trees/shrubs) are correctly excluded from the "lawn water received past 7 days" tile.
- Open question: do they deserve a separate dashboard tile so their activity is visible? Tie to the trees/shrubs work above.

### Tank-mix UX learnings from real use
- The tank-mix Quick Log flow shipped in Phase 1.5. Real use will reveal whether the "+ Add product" affordance is well-placed, whether defaults are right, and whether the sub-15-second goal holds for multi-product mixes.

### JSONB columns store JSON `null` instead of SQL `NULL`
- SQLAlchemy's `JSONB` type renders Python `None` as JSONB `'null'` unless the column sets
  `none_as_null=True`. Every nullable JSONB column in `entities.py` is affected —
  `cultural_practice.details`, `equipment.calibration`, `product.active_ingredients`,
  `guaranteed_analysis`, `soil_test.base_saturation`.
- Consequence: `WHERE details IS NULL` silently matches nothing. This bit the Phase 2a mow
  backfill, which reported `UPDATE 0` until the predicate became
  `details IS NULL OR jsonb_typeof(details) = 'null'`.
- Fix is a one-line change per column plus a migration to normalize existing `'null'` values.
  Deferred because it's repo-wide and Phase 2a Block 1 was scoped to logging friction. Worth
  doing before anything queries JSONB columns for absence.

## To evaluate during the two-week use period

- Treatment Quick Log: does it actually hit sub-15 seconds on mobile for the common single-product case?
- Dashboard tiles: which ones do I actually check daily? Which are noise?
- Reminders: are the ntfy notifications useful or annoying?
- Data model gaps: what am I logging as "notes" that should be structured?
- Irrigation calibration: did the precip_rate_in_per_hr_snapshot pattern feel natural or annoying when adding events?

## Long-term / not yet evaluated

- AI assistant (Phase 3 — **named, not designed**). The entire spec today is three bullets in
  `docs/ROADMAP.md`: recommendations from recorded history; explainable reasoning over
  weather/irrigation/treatment data; human approval required for any recommended action. No model,
  provider, prompt, tool, RAG, or schema decisions exist yet. `.env.example` reserves an unused
  `ANTHROPIC_API_KEY`. Starting this is a design task from near-zero, not a build task.
- Soil test PDF parsing (Phase 4 candidate).
- Photo logging for problem-area documentation.
- Hyperlocal weather station integration (Tempest, Ambient, Davis).
- Equipment-aware spray planning (AI computes tank-mix amounts from sprayer calibration).
- External access via Cloudflare Tunnel (deferred from Phase 1).
