"""Flat CSV export, one file per entity.

Rows are denormalised for analysis: treatments explode to one row per product
line (granular or per-fill), carrying derived amount used and nitrogen so the
export stands alone in a spreadsheet without re-deriving anything.
"""

import csv
import io
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lawn_api.models.entities import (
    CulturalPractice,
    IrrigationEvent,
    IrrigationZone,
    Product,
    SoilTest,
    TankFill,
    Treatment,
    WeatherDaily,
)
from lawn_api.services.coverage import applications_remaining
from lawn_api.services.guardrails import _product_nitrogen  # reused: lb N from amount + analysis
from lawn_api.services.inventory import _granular_amount
from lawn_api.services.units import UnitConversionError


def rows_to_csv(rows: list[dict], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def _nitrogen_lb(product: Product, amount: Decimal, unit: str) -> float | None:
    if product.product_type not in {"fertilizer_synthetic", "fertilizer_organic"}:
        return None
    try:
        result = _product_nitrogen(product, amount, unit)
    except UnitConversionError:
        return None
    return float(result.lb_n) if result.lb_n is not None else None


TREATMENT_FIELDS = [
    "treatment_id", "applied_at", "application_method", "applicator", "target",
    "area_treated_sqft", "fill_number", "product", "product_type",
    "amount_used", "amount_used_unit", "rate", "rate_unit",
    "effective_rate_per_1000", "nitrogen_lb", "notes",
]


async def treatment_rows(db: AsyncSession) -> list[dict]:
    treatments = (
        (
            await db.execute(
                select(Treatment)
                .options(
                    selectinload(Treatment.products),
                    selectinload(Treatment.fills).selectinload(TankFill.products),
                )
                .order_by(Treatment.applied_at)
            )
        )
        .scalars()
        .all()
    )
    products = {p.id: p for p in (await db.execute(select(Product))).scalars().all()}
    rows: list[dict] = []

    for t in treatments:
        base = {
            "treatment_id": str(t.id),
            "applied_at": t.applied_at.isoformat(),
            "application_method": t.application_method,
            "applicator": t.applicator,
            "target": t.target,
            "area_treated_sqft": t.area_treated_sqft,
            "notes": t.notes,
        }
        if t.application_method == "liquid":
            for fill in t.fills:
                area = Decimal(str(fill.area_covered_sqft))
                for fp in fill.products:
                    product = products.get(fp.product_id)
                    amount = Decimal(str(fp.amount_used))
                    eff = float(amount / area * Decimal(1000)) if area > 0 else None
                    rows.append({
                        **base,
                        "fill_number": fill.fill_number,
                        "product": product.name if product else "",
                        "product_type": product.product_type if product else "",
                        "amount_used": float(amount),
                        "amount_used_unit": fp.amount_used_unit,
                        "effective_rate_per_1000": eff,
                        "nitrogen_lb": _nitrogen_lb(product, amount, fp.amount_used_unit) if product else None,
                    })
        else:
            area = Decimal(str(t.area_treated_sqft or 0))
            for tp in t.products:
                product = products.get(tp.product_id)
                derived = _granular_amount(Decimal(str(tp.rate_applied)), tp.rate_unit, area)
                amount, unit = derived if derived else (None, None)
                rows.append({
                    **base,
                    "product": product.name if product else "",
                    "product_type": product.product_type if product else "",
                    "rate": float(tp.rate_applied),
                    "rate_unit": tp.rate_unit,
                    "amount_used": float(amount) if amount is not None else None,
                    "amount_used_unit": unit,
                    "nitrogen_lb": (
                        _nitrogen_lb(product, amount, unit) if product and amount is not None else None
                    ),
                })
    return rows


CULTURAL_FIELDS = ["id", "performed_at", "practice_type", "cut_height_inches", "mow_orientation", "notes"]


async def cultural_rows(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(CulturalPractice).order_by(CulturalPractice.performed_at))).scalars().all()
    out = []
    for c in rows:
        details = c.details or {}
        out.append({
            "id": str(c.id),
            "performed_at": c.performed_at.isoformat(),
            "practice_type": c.practice_type,
            "cut_height_inches": details.get("cut_height_inches"),
            "mow_orientation": details.get("mow_orientation"),
            "notes": c.notes,
        })
    return out


IRRIGATION_FIELDS = [
    "started_at", "zone_name", "zone_category", "duration_seconds",
    "inches_applied", "source", "skipped", "skip_reason",
]


async def irrigation_rows(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(IrrigationEvent, IrrigationZone.name, IrrigationZone.zone_category)
            .join(IrrigationZone, IrrigationZone.id == IrrigationEvent.zone_id)
            .order_by(IrrigationEvent.started_at)
        )
    ).all()
    return [
        {
            "started_at": e.started_at.isoformat(),
            "zone_name": name,
            "zone_category": category,
            "duration_seconds": e.duration_seconds,
            "inches_applied": float(e.inches_applied) if e.inches_applied is not None else None,
            "source": e.source,
            "skipped": e.skipped,
            "skip_reason": e.skip_reason,
        }
        for e, name, category in rows
    ]


PRODUCT_FIELDS = [
    "name", "manufacturer", "product_type", "label_rate", "label_rate_unit",
    "current_inventory", "current_inventory_unit", "applications_remaining",
    "guaranteed_analysis", "min_reapplication_days", "max_annual_rate", "max_annual_rate_unit",
]


async def product_rows(db: AsyncSession, lawn_sqft: int | None) -> list[dict]:
    products = (await db.execute(select(Product).order_by(Product.name))).scalars().all()
    return [
        {
            "name": p.name,
            "manufacturer": p.manufacturer,
            "product_type": p.product_type,
            "label_rate": float(p.label_rate) if p.label_rate is not None else None,
            "label_rate_unit": p.label_rate_unit,
            "current_inventory": float(p.current_inventory) if p.current_inventory is not None else None,
            "current_inventory_unit": p.current_inventory_unit,
            "applications_remaining": applications_remaining(
                p.current_inventory, p.current_inventory_unit, p.label_rate, p.label_rate_unit, lawn_sqft
            ),
            "guaranteed_analysis": str(p.guaranteed_analysis) if p.guaranteed_analysis else None,
            "min_reapplication_days": p.min_reapplication_days,
            "max_annual_rate": float(p.max_annual_rate) if p.max_annual_rate is not None else None,
            "max_annual_rate_unit": p.max_annual_rate_unit,
        }
        for p in products
    ]


SOIL_TEST_FIELDS = [
    "sample_date", "lab_name", "ph", "organic_matter_pct", "phosphorus_ppm",
    "potassium_ppm", "calcium_ppm", "magnesium_ppm", "sulfur_ppm", "cec",
]


async def soil_test_rows(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(SoilTest).order_by(SoilTest.sample_date))).scalars().all()
    return [
        {
            "sample_date": s.sample_date.isoformat(),
            "lab_name": s.lab_name,
            "ph": float(s.ph) if s.ph is not None else None,
            "organic_matter_pct": float(s.organic_matter_pct) if s.organic_matter_pct is not None else None,
            "phosphorus_ppm": float(s.phosphorus_ppm) if s.phosphorus_ppm is not None else None,
            "potassium_ppm": float(s.potassium_ppm) if s.potassium_ppm is not None else None,
            "calcium_ppm": float(s.calcium_ppm) if s.calcium_ppm is not None else None,
            "magnesium_ppm": float(s.magnesium_ppm) if s.magnesium_ppm is not None else None,
            "sulfur_ppm": float(s.sulfur_ppm) if s.sulfur_ppm is not None else None,
            "cec": float(s.cec) if s.cec is not None else None,
        }
        for s in rows
    ]


WEATHER_FIELDS = ["observation_date", "temp_high_f", "temp_low_f", "gdd_base50", "precip_sum_in"]


async def weather_daily_rows(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(WeatherDaily).order_by(WeatherDaily.observation_date))).scalars().all()
    return [
        {
            "observation_date": w.observation_date.isoformat(),
            "temp_high_f": float(w.temp_high_f) if w.temp_high_f is not None else None,
            "temp_low_f": float(w.temp_low_f) if w.temp_low_f is not None else None,
            "gdd_base50": float(w.gdd_base50) if w.gdd_base50 is not None else None,
            "precip_sum_in": float(w.precip_sum_in) if w.precip_sum_in is not None else None,
        }
        for w in rows
    ]
