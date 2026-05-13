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
| `cultural_practice` | regular | UUID (`id`) |
| `soil_test` | regular | UUID (`id`) |
| `weather_forecast` | regular | UUID (`id`) |
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

`total_amount` is intentionally omitted — it is computed at API serialization time:

```
total_amount = rate_applied × area_treated_sqft / 1000
```

Storing a derived value that depends on two mutable columns creates drift risk.

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
