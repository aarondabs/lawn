# DATA_MODEL.md — Lawn Command Center

Schema reference for the Lawn API. All decisions trace back to
`docs/agent-handoffs/TASK_4_SCHEMA_DECISIONS.md` (initial schema) and
`docs/agent-handoffs/PHASE_1_5_TANK_MIXES_AND_PRODUCTS.md` (Phase 1.5 tank-mix refactor).

*Last reconciled against live schema: May 13, 2026 (v0.1.0).*

---

## Tables

| Table | Type | PK |
|---|---|---|
| `lawn_profile` | regular | UUID (`id`) |
| `irrigation_zone` | regular | UUID (`id`) |
| `equipment` | regular | UUID (`id`) |
| `product` | regular | UUID (`id`) |
| `treatment` | regular | UUID (`id`) |
| `treatment_product` | regular | composite `(treatment_id, product_id)` |
| `tank_fill` | regular | UUID (`id`) |
| `fill_product` | regular | composite `(tank_fill_id, product_id)` |
| `cultural_practice` | regular | UUID (`id`) |
| `soil_test` | regular | UUID (`id`) |
| `weather_forecast` | regular | UUID (`id`) |
| `weather_daily` | regular | UUID (`id`); unique `(observation_date, source)` |
| `irrigation_skip` | regular | UUID (`id`); unique `rachio_event_id` |
| `app_setting` | regular | `key` (text) |
| `reminder` | regular | UUID (`id`) |
| `weather_observation` | **hypertable** | `(observed_at, source)` |
| `irrigation_event` | **hypertable** | `(started_at, zone_id)` |

---

## Conventions

### UUID primary keys

Non-hypertable tables use UUID PKs generated server-side via `gen_random_uuid()`
(provided by the `pgcrypto` extension, enabled in migration `bb1c6cb831ed`).

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

### Hypertable PK exception

TimescaleDB requires the partitioning column to be part of the primary key.
`weather_observation` and `irrigation_event` use composite primary keys
instead of UUIDs.  This is the only exception to the UUID PK rule.

### Enum-like text columns

Closed-set values are stored as `TEXT` with Postgres `CHECK` constraints
rather than native `ENUM` types.  Rationale: `ENUM` type alterations require
DDL on every change and cannot be easily rolled back; `CHECK` constraints
are simpler and trivially altered.

All valid values for each column live in
`api/src/lawn_api/models/constants.py` as Python tuples.  Both the SQLAlchemy
model constraints and pydantic Literals source from these tuples, ensuring
they are always in sync.

### All timestamps are UTC (timestamptz)

Every `TIMESTAMP` column uses `TIMESTAMP WITH TIME ZONE`.  The application
writes UTC.  The single timezone-aware rendering exception is
`weather_forecast.forecast_for_day` (see below).

### Singleton guard — `lawn_profile`

Only one row should exist.  Enforced via:

```sql
singleton_guard BOOLEAN NOT NULL DEFAULT true,
UNIQUE (singleton_guard)
```

Inserting a second row with `singleton_guard = true` violates the unique
constraint.  Application code always inserts with the default.

---

## Notable column decisions

### `weather_forecast.forecast_for_day` (generated, persisted)

```sql
forecast_for_day DATE
  GENERATED ALWAYS AS ((forecast_for AT TIME ZONE 'America/Chicago')::date) STORED
```

- Converts `forecast_for` (UTC) to Central Time for calendar-day bucketing.
- Timezone is **hardcoded** to `America/Chicago` because the lawn is in
  Topeka, KS.  If multi-location support is ever added, re-evaluate.
- Unique constraint: `(forecast_for_day, source)` — one forecast per source
  per calendar day.  Writing a new forecast for the same source+day uses
  `ON CONFLICT (forecast_for_day, source) DO UPDATE`.

### `treatment` and `treatment_product` — tank-mix schema

`treatment` holds header-level data (date, equipment, applicator, weather snapshot, notes).
Per-product details live in `treatment_product`, which allows one treatment event to record
multiple products applied simultaneously (tank mixes).

`treatment_product` columns: `treatment_id` (FK → `treatment`, CASCADE DELETE), `product_id`
(FK → `product`, RESTRICT), `rate_applied`, `rate_unit`, `position` (display order), `notes`.
Composite PK: `(treatment_id, product_id)`.

Valid `rate_unit` values: `lb_per_1000`, `oz_per_1000`, `fl_oz_per_1000`, `gal_per_1000`,
`fl_oz_per_gal`, `pct_vv`, `lb_per_acre`.

Amount used is intentionally not stored. It is derived where it is displayed, from
`rate_applied × area_treated_sqft / 1000` (or `/ 43560` for `lb_per_acre`), because it depends on
two mutable columns and storing it would invite drift. The same derivation drives inventory
decrement in `services/inventory.py`.

Prior versions of this document claimed the value was computed at API serialization time under the
name `total_amount`. It was not — no such field ever existed in the code. As of Phase 2a the
derivation is real, but it happens in the web layer (`lib/enums.ts` → `granularAmountUsed`) and in
the inventory service, not on the treatment response.

### `application_method` — granular vs liquid

Every `treatment` carries an `application_method` of `granular`, `liquid`, or `other`, and it
determines which child structure holds the product detail:

| Method | Child rows | Area | Amount used |
|---|---|---|---|
| `granular` | `treatment_product` | entered | derived (rate × area) |
| `liquid` | `tank_fill` → `fill_product` | **derived** (mix volume ÷ calibrated rate) | entered (ground truth) |

The two are additive, not unified. Granular stays two-level and simple; liquid gets the extra
level because tank fills genuinely differ from one another.

One method per treatment. Spreading granular and spraying liquid on the same day is two treatments.

**Granular is one product per treatment.** A spreader has a single setting, and one setting
delivers one rate — there is no setting that puts two products down at their respective label
rates, which for a pesticide is a label-compliance problem and not merely an accuracy one. A
product sold pre-blended is still one product with one label rate. The Phase 2a handoff spec
originally called for retaining a multi-product granular affordance; it was dropped after review
because it could not be used correctly in practice.

This is enforced in the web form only. `treatment_product` still permits multiple rows per
treatment, so the pre-Phase-2a records keep working and the constraint can be revisited without a
migration.

### `tank_fill` and `fill_product` — liquid applications

A liquid application is mixed to a round tank volume, sprayed at the sprayer's calibrated rate
until empty, and refilled as needed. Each fill is a first-class row rather than being summed into a
flat total, because fills differ in practice — running a couple of ounces short on the last one is
normal, and inventory decrement needs the real per-fill amounts.

**What is entered:** total mix volume per fill, and the amount of each product that went into it.
**What is derived:** `area_covered_sqft = mix volume ÷ calibrated rate × 1000`, and each product's
effective rate = `amount_used ÷ area_covered × 1000`.

`area_covered_sqft` is computed in the service layer (`services/units.area_covered_sqft`) and
stored as a plain column, *not* a Postgres generated column — a `GENERATED` expression cannot do
the unit normalisation that gallons-vs-litres and `gal_per_1000`-vs-`fl_oz_per_1000` require.

`calibrated_rate_snapshot` and `calibrated_rate_unit_snapshot` freeze the sprayer's calibration at
the time of the fill, so recalibrating the sprayer never rewrites history. Same pattern as
`irrigation_event.precip_rate_in_per_hr_snapshot`.

**The derived area may exceed the lawn's nominal size, and that is correct.** Over-mixing and
spraying the surplus outside the maintained lawn is normal practice; the model records what
actually happened rather than assuming every application covered exactly `lawn_profile.total_sqft`.
`treatment.area_treated_sqft` for a liquid treatment is the sum of its fills' covered areas.

The sprayer's rate comes from `equipment.calibration` (JSONB) under `application_rate` /
`application_rate_unit`, validated by `SprayerCalibration` in `schemas/equipment.py`.

### Amount units vs rate units

`RATE_UNITS` describe a quantity *per area* (`lb_per_1000`). `AMOUNT_UNITS` describe a quantity
outright — volume (`fl_oz`, `pt`, `qt`, `gal`) or weight (`oz`, `lb`). They are not
interchangeable, and `product.current_inventory_unit` takes an **amount** unit.

Before Phase 2a it wrongly took a rate unit, which made `0 lb_per_1000` the only expressible stock
level — meaningless, and unusable for decrement. Migration `a1c4e7b92f03` repointed the constraint
and cleared the one affected row.

Conversions live in exactly one place, `services/units.py`. Volume and weight are separate
families: converting between them needs a product's density, which is not modelled, so the
conversion **raises rather than guessing**. Callers report the failure and skip the decrement —
inventory is left visibly stale instead of silently wrong.

### Inventory decrement

Saving a treatment decrements `product.current_inventory`; editing or deleting one restores it.
Edits restore the previous consumption in full and re-apply the new consumption rather than
computing a delta, which stays correct when an edit adds or removes products.

Inventory is allowed to go negative — Aaron does not always log restocks, and refusing the save
would block recording something that physically happened. Negative stock is flagged in the UI
instead.

### `cultural_practice.details` — structured mow fields

`details` is a nullable JSONB blob whose shape varies by `practice_type`. For
`practice_type = 'mow'` it carries the two fields Aaron previously typed into free-text `notes`:

```json
{ "cut_height_inches": 3.75, "mow_orientation": "diagonal_nw_se" }
```

- `cut_height_inches` — numeric, greater than 0, at most 8, and a multiple of 0.25 (deck heights
  are set in quarter-inch increments). Prefilled on the form from the last logged mow, falling
  back to `lawn_profile.target_mow_height_inches`, but always editable — the height varies
  seasonally.
- `mow_orientation` — one of `north_south`, `east_west`, `diagonal_ne_sw`, `diagonal_nw_se`,
  `other`. When `other`, an optional `mow_orientation_other` string carries the free-text
  description.

Because these live in JSONB there is **no DB CHECK constraint** — the pydantic `MowDetails`
model in `schemas/cultural_practice.py` is the only enforcement point. Values are sourced from
`MOW_ORIENTATIONS` in `models/constants.py`. Validation keys off the *presence* of mow fields
rather than `practice_type`, so a PATCH that supplies `details` without `practice_type` is still
checked. Other practice types may put arbitrary keys in `details`; they pass through untouched.

Structured orientation exists so a future feature can reason over mow patterns (e.g. warning
about repeated passes in one direction to reduce rutting). No such logic exists yet.

### `irrigation_event.inches_applied` (generated, persisted)

```sql
inches_applied NUMERIC(6,3)
  GENERATED ALWAYS AS (duration_seconds / 3600.0 * precip_rate_in_per_hr_snapshot) STORED
```

- Uses a **snapshot** of the zone's precipitation rate at insert time
  (`precip_rate_in_per_hr_snapshot`), not a FK back to `irrigation_zone`.
  Rationale: the zone's calibration may change; historical water amounts
  should reflect the calibration that was in effect at the time.
- Postgres generated columns cannot reference other tables, so the snapshot
  pattern is required.

### `irrigation_event.rachio_event_id` (partial unique index)

Manual events have `rachio_event_id = NULL` and are not subject to
idempotency deduplication.  Rachio-sourced events carry a non-null ID.

TimescaleDB requires all unique indexes on a hypertable to include the
partitioning column (`started_at`), so the index covers both columns:

```sql
CREATE UNIQUE INDEX irrigation_event_rachio_event_id_uniq
    ON irrigation_event (rachio_event_id, started_at)
    WHERE rachio_event_id IS NOT NULL;
```

### `product.product_type` (expanded enum, Phase 1.5)

The original Phase 1 spec used a short list. The as-built enum (enforced by CHECK constraint) is:

`fertilizer_synthetic`, `fertilizer_organic`, `herbicide_pre`, `herbicide_post_broadleaf`,
`herbicide_post_grassy`, `herbicide_non_selective`, `fungicide`, `insecticide`,
`biostimulant`, `soil_amendment`, `surfactant`, `wetting_agent`, `dye_marker`, `seed`, `other`

Valid rate units (`label_rate_unit`, `treatment_product.rate_unit`, etc.):
`lb_per_1000`, `oz_per_1000`, `fl_oz_per_1000`, `gal_per_1000`, `fl_oz_per_gal`, `pct_vv`, `lb_per_acre`

### `irrigation_zone.zone_category` and `is_enabled` (added post-Phase 1)

`zone_category` TEXT NOT NULL DEFAULT `'turf'` — valid values: `turf`, `trees_shrubs`, `ornamental`, `inactive`.
Used to distinguish lawn zones from drip zones (trees/shrubs) for dashboard water-depth calculations — drip zones are excluded from the "lawn water received" tile.

`is_enabled` BOOLEAN NOT NULL DEFAULT `true` — soft-disable a zone without deleting it.

### `irrigation_zone.zone_number` (unique)

Zone numbers are the human-visible identity for zones in the UI.
Enforced unique: `UNIQUE (zone_number)`.

---

## Alembic migration chain

| Revision | Slug | Description |
|---|---|---|
| `bb1c6cb831ed` | `enable_pgcrypto` | `CREATE EXTENSION pgcrypto` |
| `da5a66c32ed2` | `create_base_tables` | All non-hypertable tables (original Phase 1 schema) |
| `c7dab2e13bd7` | `create_timeseries_tables` | `weather_observation` + `irrigation_event` as plain tables |
| `2a08c9d24ed9` | `enable_timescaledb_and_convert` | `CREATE EXTENSION timescaledb` + `create_hypertable()` calls |
| `7e2f9a1c3d5b` | `phase_1_5_tank_mix_schema` | Add `treatment_product`; remove per-product cols from `treatment`; expand product type + rate unit enums |
| `5a1f83f2d8b4` | `add_zone_category_to_irrigation_zone` | Add `zone_category` TEXT column (turf, trees_shrubs, ornamental, inactive) to `irrigation_zone` |
| `6c3f4c8be7ab` | `add_is_enabled_to_irrigation_zone` | Add `is_enabled` BOOLEAN (default true) to `irrigation_zone` |
| `f3a91b2e8c04` | `fix_irrigation_event_source_constraint` | Fix `source` CHECK constraint on `irrigation_event` |

To run all migrations:

```bash
docker exec -w /app lawn-api python -m alembic upgrade head
```

> **Ask before running `alembic upgrade`** on a non-empty database.

---

## Source files

| File | Purpose |
|---|---|
| `api/src/lawn_api/models/constants.py` | All closed-set enum value tuples |
| `api/src/lawn_api/models/entities.py` | SQLAlchemy ORM model classes |
| `api/src/lawn_api/models/__init__.py` | Re-exports all model classes |
| `api/src/lawn_api/db.py` | Async engine, session factory, `Base` |
| `api/alembic/env.py` | Alembic async env wired to settings + Base |
| `api/alembic/versions/` | All migration revision files |

---

## Phase 2c additions (guardrails, dashboard, reminders, export)

### `app_setting` — operator-tunable thresholds

Typed key/value store (`key` text PK, `value` JSONB). Guardrails and reminder
rules read their thresholds here instead of from constants, so they can be
retuned without a code change. Seeded keys:

| Key | Default | Used by |
|---|---|---|
| `nitrogen_lb_per_1000_per_30d` | `1.0` | N-load guardrail (rolling 30-day) |
| `nitrogen_lb_per_1000_per_season` | `4.0` | N-load guardrail (season-to-date) |
| `season_start_month_day` | `"03-01"` | annual-cumulative counter reset (see below) |
| `gdd_green_up_month_day` | `"03-15"` | GDD accumulation start |
| `days_since_mow_threshold` | `10` | mow-overdue reminder |
| `soil_temp_preemergent_f` | `55` | spring pre-emergent reminder |
| `preemergent_blocking_days_default` | `90` | pre-emergent guardrail fallback window |

**Season boundary, not calendar year.** The annual-maximum guardrail resets its
per-product cumulative at `season_start_month_day`, not Jan 1. This is
deliberate: a "once per year" product (GrubEx) applied a week earlier than last
year must not trip last season's cap. "Once per year" means "once per season."

### `weather_daily` — GDD accumulation

One row per calendar day, kept permanently (unlike `weather_forecast`, which is
wiped and rewritten each refresh). `gdd_base50` is computed in the service layer
as `max(0, (high+low)/2 - 50)` and left NULL when a day lacks a temperature, so
the accumulation SUM skips incomplete days rather than counting them as zero.

Populated two ways: the regular weather refresh carries the recent 7-day tail;
`services/weather.backfill_weather_daily` pulls deeper history from Open-Meteo's
**archive API** (a separate host from the forecast endpoint) back to green-up.

The old `weather_observation.gdd_base50` column was **dropped** (migration
`f6b3d18a2c94`). What it stored was not GDD — it was instantaneous air temp minus
50 at poll time, one snapshot per poll, un-summable. Nothing read it.

### `irrigation_skip` — Rachio schedule skips

Rain/seasonal skips arrive from Rachio as `SCHEDULE_STATUS` events with a
`SKIP_ADDED` subtype — no zone, no duration, so they don't fit `irrigation_event`.
Captured here instead (idempotent by `rachio_event_id`) for the dashboard's
"Rachio skipped watering N times this week" signal. The reason is in `summary`.

### `product` — guardrail columns

`reorder_threshold` (shares `current_inventory_unit`; unused — see the coverage
note below) and `preemergent_blocking_days` (germination-blocking window;
`herbicide_pre` only, nullable, falls back to the setting). `guaranteed_analysis`
now carries typed keys (`total_nitrogen_pct`, `lbs_n_per_gallon`, …) validated by
`schemas/product.GuaranteedAnalysis`.

**Coverage remaining, not low-stock threshold.** Task 4.2's static threshold was
not built. `product` responses instead carry a derived `applications_remaining`
(`stock / (label_rate × lawn_area)`), computed in `services/coverage.py`. It's
null for non-area rate units and for stock/rate unit mismatches that would need a
density. See `BACKLOG.md` for the schedule-aware reorder feature that supersedes
both (Phase 3).

### Derived values and the guardrail finding shape

Guardrails (`services/guardrails.py`) return structured `GuardrailFinding`
objects (severity, message, the numbers), evaluated at treatment/practice save
time and queryable at `/api/v1/dashboard/widgets` (outstanding cautions) and
`GET /api/v1/guardrails/current`. A check that can't run for missing data returns
`cannot_evaluate` — never a silent pass.

Nitrogen and per-product amount math reuse `services/inventory` and
`services/units` in one place, so the liquid/granular split is summed
consistently across inventory decrement, guardrails, and CSV export. Unit
conversion never crosses the volume/weight boundary without a density (it raises;
callers surface it).
