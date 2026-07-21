"""Rules-based guardrails.

Deterministic safety checks over logged or proposed treatments and practices.
Every check here is advisory -- it warns, it never blocks a save. The one
inviolable rule: a check that cannot run because data is missing reports
`cannot_evaluate`, never a silent pass. A guardrail that fails silent is worse
than none, because it reads as all-clear when it should say "I don't know."

The service returns structured GuardrailFinding objects so the same evaluation
feeds the save-time response, the dashboard's outstanding-cautions widget, and
(Phase 3) the AI layer, which can reason over the numbers rather than the prose.

None of this is agronomic judgment. These are hard, known, rule-based label and
program constraints only. Anything that needs "it depends" is Phase 3.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lawn_api.models.entities import (
    Product,
    TankFill,
    Treatment,
)
from lawn_api.schemas.guardrail import GuardrailFinding
from lawn_api.services import settings as app_settings
from lawn_api.services.inventory import consumption_for_treatment
from lawn_api.services.units import UnitConversionError, convert_amount, unit_family

CENTRAL = ZoneInfo("America/Chicago")

FERTILIZER_TYPES = {"fertilizer_synthetic", "fertilizer_organic"}


@dataclass
class ProductNitrogen:
    """lb of N a product contributed, or why it could not be computed."""

    lb_n: Decimal | None
    missing_reason: str | None


def _product_nitrogen(product: Product, amount: Decimal, unit: str) -> ProductNitrogen:
    """lb of elemental N from `amount` of a product, or a reason it is unknown.

    Weight amounts use the N percentage; volume amounts use lbs N per gallon.
    The two paths exist because percentage is a weight ratio, and applying it to
    a volume would need density -- which is never guessed (see services/units).
    """
    analysis = product.guaranteed_analysis or {}
    family = unit_family(unit)

    if family == "weight":
        pct = analysis.get("total_nitrogen_pct")
        if pct is None:
            return ProductNitrogen(None, "no total_nitrogen_pct in guaranteed analysis")
        lb = convert_amount(amount, unit, "lb")
        return ProductNitrogen(lb * Decimal(str(pct)) / Decimal(100), None)

    # volume
    lbs_n_per_gal = analysis.get("lbs_n_per_gallon")
    if lbs_n_per_gal is None:
        return ProductNitrogen(None, "no lbs_n_per_gallon in guaranteed analysis (required for liquids)")
    gal = convert_amount(amount, unit, "gal")
    return ProductNitrogen(gal * Decimal(str(lbs_n_per_gal)), None)


async def _treatment_nitrogen_per_1000(
    db: AsyncSession, treatment: Treatment, products_by_id: dict[UUID, Product]
) -> tuple[Decimal, list[str]]:
    """(lb N per 1,000 sqft for this treatment, names of products we couldn't evaluate).

    Normalised over the treatment's own treated/covered area, per the Phase 2c
    spec. For a whole-lawn application that is the agronomic figure; a partial
    spot-treatment is expressed as its own local rate, which the caller sums.
    """
    consumption = await consumption_for_treatment(db, treatment)
    area = Decimal(str(treatment.area_treated_sqft or 0))
    if area <= 0:
        return Decimal(0), []

    total_lb_n = Decimal(0)
    unknown: list[str] = []
    for product_id, (amount, unit) in consumption.items():
        product = products_by_id.get(product_id)
        if product is None or product.product_type not in FERTILIZER_TYPES:
            continue
        try:
            result = _product_nitrogen(product, amount, unit)
        except UnitConversionError:
            unknown.append(product.name)
            continue
        if result.lb_n is None:
            unknown.append(product.name)
        else:
            total_lb_n += result.lb_n

    return total_lb_n / (area / Decimal(1000)), unknown


def _season_start(today: date, month_day: str) -> date:
    """Most recent occurrence of the configured season-start month/day.

    So the annual counters reset seasonally: an application a week earlier than
    last year's must not count against last season's total.
    """
    try:
        month, day = (int(part) for part in month_day.split("-"))
        candidate = date(today.year, month, day)
    except (ValueError, TypeError):
        candidate = date(today.year, 1, 1)
    if candidate > today:
        return date(candidate.year - 1, candidate.month, candidate.day)
    return candidate


async def _fertilizer_history(
    db: AsyncSession, since: datetime, exclude_id: UUID | None
) -> list[Treatment]:
    """Treatments applied on/after `since`, with fills eagerly loaded.

    exclude_id drops the treatment being proposed/edited so it is not
    double-counted against itself.
    """
    stmt = (
        select(Treatment)
        .options(selectinload(Treatment.products), selectinload(Treatment.fills).selectinload(TankFill.products))
        .where(Treatment.applied_at >= since)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [t for t in rows if t.id != exclude_id]


async def evaluate_nitrogen_load(
    db: AsyncSession,
    proposed: Treatment,
    products_by_id: dict[UUID, Product],
    now: datetime,
) -> list[GuardrailFinding]:
    """Rolling 30-day and season-to-date nitrogen, including the proposed treatment."""
    findings: list[GuardrailFinding] = []

    proposed_n, unknown = await _treatment_nitrogen_per_1000(db, proposed, products_by_id)
    for name in unknown:
        product = next((p for p in products_by_id.values() if p.name == name), None)
        findings.append(
            GuardrailFinding(
                code="nitrogen_load_data_missing",
                severity="cannot_evaluate",
                title="Cannot evaluate nitrogen load",
                message=(
                    f"{name} is a fertilizer but has no usable guaranteed analysis, "
                    f"so its nitrogen contribution is unknown and the load check is incomplete."
                ),
                numbers={},
                product_id=product.id if product else None,
                product_name=name,
            )
        )

    # 30-day rolling window.
    threshold_30 = await app_settings.get_decimal(db, app_settings.NITROGEN_30D, Decimal("1.0"))
    history_30 = await _fertilizer_history(db, now - timedelta(days=30), proposed.id)
    prior_30 = Decimal(0)
    for t in history_30:
        n, _ = await _treatment_nitrogen_per_1000(db, t, products_by_id)
        prior_30 += n
    total_30 = prior_30 + proposed_n

    if total_30 > threshold_30:
        findings.append(
            GuardrailFinding(
                code="nitrogen_load_30d",
                severity="caution",
                title="Nitrogen over the 30-day limit",
                message=(
                    f"This application brings trailing-30-day nitrogen to "
                    f"{total_30:.2f} lb N/1,000 sq ft, over the {threshold_30:.2f} limit. "
                    f"Advisory -- proceed if intended."
                ),
                numbers={
                    "applied_30d": float(total_30),
                    "this_application": float(proposed_n),
                    "threshold": float(threshold_30),
                    "window_days": 30,
                },
            )
        )

    # Season-to-date.
    threshold_season = await app_settings.get_decimal(db, app_settings.NITROGEN_SEASON, Decimal("4.0"))
    month_day = await app_settings.get_str(db, app_settings.SEASON_START_MONTH_DAY, "03-01")
    season_start = _season_start(now.astimezone(CENTRAL).date(), month_day)
    season_start_dt = datetime.combine(season_start, datetime.min.time(), tzinfo=CENTRAL)
    history_season = await _fertilizer_history(db, season_start_dt, proposed.id)
    prior_season = Decimal(0)
    for t in history_season:
        n, _ = await _treatment_nitrogen_per_1000(db, t, products_by_id)
        prior_season += n
    total_season = prior_season + proposed_n

    if total_season > threshold_season:
        findings.append(
            GuardrailFinding(
                code="nitrogen_load_season",
                severity="caution",
                title="Nitrogen over the season budget",
                message=(
                    f"Season-to-date nitrogen would reach {total_season:.2f} lb N/1,000 sq ft, "
                    f"over the {threshold_season:.2f} budget since {season_start.isoformat()}. Advisory."
                ),
                numbers={
                    "applied_season": float(total_season),
                    "this_application": float(proposed_n),
                    "threshold": float(threshold_season),
                },
            )
        )

    return findings


# Per-area rate units, mapped to (amount unit, area basis in sqft). Non-area
# units (fl_oz_per_gal, pct_vv) are absent: an annual maximum expressed against
# a mix concentration has no per-season meaning.
_RATE_UNIT_BASIS: dict[str, tuple[str, Decimal]] = {
    "lb_per_1000": ("lb", Decimal(1000)),
    "oz_per_1000": ("oz", Decimal(1000)),
    "fl_oz_per_1000": ("fl_oz", Decimal(1000)),
    "gal_per_1000": ("gal", Decimal(1000)),
    "lb_per_acre": ("lb", Decimal(43560)),
}


def _treatment_includes(treatment: Treatment, product_id: UUID) -> bool:
    if any(tp.product_id == product_id for tp in treatment.products):
        return True
    return any(fp.product_id == product_id for fill in treatment.fills for fp in fill.products)


def _proposed_product_ids(treatment: Treatment) -> set[UUID]:
    ids = {tp.product_id for tp in treatment.products}
    ids |= {fp.product_id for fill in treatment.fills for fp in fill.products}
    return ids


async def evaluate_reapplication(
    db: AsyncSession,
    proposed: Treatment,
    products_by_id: dict[UUID, Product],
    now: datetime,
) -> list[GuardrailFinding]:
    """Warn if a product is re-applied inside its minimum interval."""
    findings: list[GuardrailFinding] = []
    product_ids = _proposed_product_ids(proposed)
    if not product_ids:
        return findings

    # A year back covers any sane reapplication interval.
    history = await _fertilizer_history(db, now - timedelta(days=400), proposed.id)
    proposed_at = proposed.applied_at or now

    for product_id in product_ids:
        product = products_by_id.get(product_id)
        if product is None:
            continue

        prior = [t for t in history if _treatment_includes(t, product_id) and t.applied_at < proposed_at]
        if not prior:
            continue
        most_recent = max(prior, key=lambda t: t.applied_at)
        gap_days = (proposed_at - most_recent.applied_at).days

        if product.min_reapplication_days is None:
            findings.append(
                GuardrailFinding(
                    code="reapplication_data_missing",
                    severity="cannot_evaluate",
                    title="Cannot check reapplication interval",
                    message=(
                        f"{product.name} was last applied {gap_days} days ago, but it has no "
                        f"minimum reapplication interval on file, so the interval can't be checked."
                    ),
                    numbers={"days_since_last": float(gap_days)},
                    product_id=product_id,
                    product_name=product.name,
                )
            )
            continue

        if gap_days < product.min_reapplication_days:
            findings.append(
                GuardrailFinding(
                    code="reapplication_interval",
                    severity="caution",
                    title="Inside the reapplication interval",
                    message=(
                        f"{product.name} was applied {gap_days} days ago; its minimum interval is "
                        f"{product.min_reapplication_days} days. Advisory."
                    ),
                    numbers={
                        "days_since_last": float(gap_days),
                        "min_interval_days": float(product.min_reapplication_days),
                    },
                    product_id=product_id,
                    product_name=product.name,
                )
            )

    return findings


async def _product_amount_per_basis(
    db: AsyncSession, treatment: Treatment, product_id: UUID, amount_unit: str, basis_sqft: Decimal
) -> Decimal | None:
    """This treatment's contribution to a product's cumulative per-area rate.

    Returns the applied amount normalised to `amount_unit` per `basis_sqft`, or
    None if the amount could not be converted to that unit (cross-family).
    """
    consumption = await consumption_for_treatment(db, treatment)
    if product_id not in consumption:
        return None
    amount, unit = consumption[product_id]
    area = Decimal(str(treatment.area_treated_sqft or 0))
    if area <= 0:
        return None
    try:
        amount_in_unit = convert_amount(amount, unit, amount_unit)
    except UnitConversionError:
        return None
    return amount_in_unit / (area / basis_sqft)


async def evaluate_annual_maximum(
    db: AsyncSession,
    proposed: Treatment,
    products_by_id: dict[UUID, Product],
    now: datetime,
) -> list[GuardrailFinding]:
    """Warn when season-to-date use of a product approaches or exceeds its cap.

    The counter resets at the configured season start, so an application a week
    earlier than last year's does not count against last season's total.
    """
    findings: list[GuardrailFinding] = []
    product_ids = _proposed_product_ids(proposed)
    if not product_ids:
        return findings

    month_day = await app_settings.get_str(db, app_settings.SEASON_START_MONTH_DAY, "03-01")
    season_start = _season_start(now.astimezone(CENTRAL).date(), month_day)
    season_start_dt = datetime.combine(season_start, datetime.min.time(), tzinfo=CENTRAL)
    history = await _fertilizer_history(db, season_start_dt, proposed.id)

    for product_id in product_ids:
        product = products_by_id.get(product_id)
        if product is None or product.max_annual_rate is None or product.max_annual_rate_unit is None:
            continue

        basis = _RATE_UNIT_BASIS.get(product.max_annual_rate_unit)
        if basis is None:
            # A non-area annual max (e.g. pct_vv) has no seasonal-cumulative meaning.
            continue
        amount_unit, basis_sqft = basis

        cumulative = Decimal(0)
        this_application = await _product_amount_per_basis(db, proposed, product_id, amount_unit, basis_sqft)
        if this_application is not None:
            cumulative += this_application
        for t in history:
            if not _treatment_includes(t, product_id):
                continue
            prior = await _product_amount_per_basis(db, t, product_id, amount_unit, basis_sqft)
            if prior is not None:
                cumulative += prior

        cap = Decimal(str(product.max_annual_rate))
        if cumulative > cap:
            findings.append(
                GuardrailFinding(
                    code="annual_maximum",
                    severity="caution",
                    title="Over the annual maximum",
                    message=(
                        f"Season-to-date {product.name} would reach {cumulative:.2f} "
                        f"{product.max_annual_rate_unit}, over the {cap:.2f} annual maximum "
                        f"since {season_start.isoformat()}. Advisory."
                    ),
                    numbers={
                        "applied_season": float(cumulative),
                        "max_annual_rate": float(cap),
                    },
                    product_id=product_id,
                    product_name=product.name,
                )
            )

    return findings


async def evaluate_overseed_after_preemergent(
    db: AsyncSession, overseed_at: datetime, now: datetime
) -> list[GuardrailFinding]:
    """Warn if an overseed falls inside a pre-emergent's germination-blocking window.

    Pre-emergent herbicides block seed germination for a product-specific
    duration. Where the product record carries the window, use it; otherwise a
    conservative default from settings, noted as an assumption.
    """
    findings: list[GuardrailFinding] = []
    default_days = await app_settings.get_int(db, app_settings.PREEMERGENT_BLOCKING_DAYS_DEFAULT, 90)

    # Any pre-emergent applied within a generous lookback of the overseed date.
    lookback = overseed_at - timedelta(days=max(default_days, 120))
    history = (
        await db.execute(
            select(Treatment)
            .options(selectinload(Treatment.products), selectinload(Treatment.fills).selectinload(TankFill.products))
            .where(Treatment.applied_at >= lookback, Treatment.applied_at <= overseed_at)
        )
    ).scalars().all()

    products_by_id = await _load_products(db)
    for treatment in history:
        for product_id in _proposed_product_ids(treatment):
            product = products_by_id.get(product_id)
            if product is None or product.product_type != "herbicide_pre":
                continue
            window = product.preemergent_blocking_days or default_days
            used_default = product.preemergent_blocking_days is None
            blocked_until = treatment.applied_at + timedelta(days=window)
            if overseed_at <= blocked_until:
                gap = (overseed_at - treatment.applied_at).days
                assumption = " (using a conservative default window; set it on the product)" if used_default else ""
                findings.append(
                    GuardrailFinding(
                        code="preemergent_before_seed",
                        severity="caution",
                        title="Overseed inside a pre-emergent window",
                        message=(
                            f"{product.name} was applied {gap} days before this overseed; it blocks "
                            f"germination for {window} days{assumption}. Seed may not establish. Advisory."
                        ),
                        numbers={
                            "days_since_preemergent": float(gap),
                            "blocking_window_days": float(window),
                        },
                        product_id=product_id,
                        product_name=product.name,
                    )
                )

    return findings


async def _load_products(db: AsyncSession) -> dict[UUID, Product]:
    rows = (await db.execute(select(Product))).scalars().all()
    return {p.id: p for p in rows}


async def evaluate_treatment(
    db: AsyncSession, treatment: Treatment, now: datetime | None = None
) -> list[GuardrailFinding]:
    """Run every treatment-scoped guardrail against `treatment`.

    `treatment` may be already-persisted or a transient instance representing a
    proposed application; either way its own id is excluded from the history so
    it is not counted twice.
    """
    now = now or datetime.now(tz=ZoneInfo("UTC"))
    products_by_id = await _load_products(db)

    findings: list[GuardrailFinding] = []
    findings += await evaluate_nitrogen_load(db, treatment, products_by_id, now)
    findings += await evaluate_reapplication(db, treatment, products_by_id, now)
    findings += await evaluate_annual_maximum(db, treatment, products_by_id, now)
    return findings


async def evaluate_current_state(db: AsyncSession, now: datetime | None = None) -> list[GuardrailFinding]:
    """Outstanding cautions as the record stands, with no new application proposed.

    Powers the dashboard's at-a-glance view. Same math as the save-time checks,
    but summed over history alone -- "am I currently over budget?" rather than
    "would this application put me over?".
    """
    now = now or datetime.now(tz=ZoneInfo("UTC"))
    products_by_id = await _load_products(db)
    findings: list[GuardrailFinding] = []

    # Nitrogen: 30-day and season-to-date, history only.
    threshold_30 = await app_settings.get_decimal(db, app_settings.NITROGEN_30D, Decimal("1.0"))
    total_30 = Decimal(0)
    for t in await _fertilizer_history(db, now - timedelta(days=30), None):
        n, _ = await _treatment_nitrogen_per_1000(db, t, products_by_id)
        total_30 += n
    if total_30 > threshold_30:
        findings.append(
            GuardrailFinding(
                code="nitrogen_load_30d",
                severity="caution",
                title="Nitrogen over the 30-day limit",
                message=(
                    f"Trailing-30-day nitrogen is {total_30:.2f} lb N/1,000 sq ft, "
                    f"over the {threshold_30:.2f} limit."
                ),
                numbers={"applied_30d": float(total_30), "threshold": float(threshold_30)},
            )
        )

    threshold_season = await app_settings.get_decimal(db, app_settings.NITROGEN_SEASON, Decimal("4.0"))
    month_day = await app_settings.get_str(db, app_settings.SEASON_START_MONTH_DAY, "03-01")
    season_start = _season_start(now.astimezone(CENTRAL).date(), month_day)
    season_start_dt = datetime.combine(season_start, datetime.min.time(), tzinfo=CENTRAL)
    total_season = Decimal(0)
    for t in await _fertilizer_history(db, season_start_dt, None):
        n, _ = await _treatment_nitrogen_per_1000(db, t, products_by_id)
        total_season += n
    if total_season > threshold_season:
        findings.append(
            GuardrailFinding(
                code="nitrogen_load_season",
                severity="caution",
                title="Nitrogen over the season budget",
                message=(
                    f"Season-to-date nitrogen is {total_season:.2f} lb N/1,000 sq ft, "
                    f"over the {threshold_season:.2f} budget since {season_start.isoformat()}."
                ),
                numbers={"applied_season": float(total_season), "threshold": float(threshold_season)},
            )
        )

    return findings
