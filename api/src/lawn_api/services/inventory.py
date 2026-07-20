"""Inventory decrement and restore for treatments.

The contract, in one line: **applying a treatment removes product from the shelf,
and un-applying it puts the product back.**

Edits are handled by restoring the treatment's previous consumption in full and
then applying the new consumption, rather than trying to compute a delta. Diffing
per-product amounts across a changed set of fills is where this kind of code
usually goes wrong, and the restore-then-apply shape is easy to reason about and
naturally correct when products are added or removed by an edit.

Two deliberate behaviours:

- **Inventory may go negative.** Aaron does not always log restocks, so refusing
  the save would block recording something that physically happened. Negative
  stock is surfaced in the UI instead.
- **Unconvertible units are never guessed.** A product stocked in pounds but
  applied in fluid ounces needs a density to reconcile. Rather than invent one,
  the decrement is skipped and a warning is returned to the caller.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.models.entities import FillProduct, Product, TankFill, Treatment
from lawn_api.services.units import UnitConversionError, convert_amount


class InventoryAdjustment:
    """A per-product amount to apply against inventory, in the product's own unit."""

    def __init__(self, product_id: UUID, amount: Decimal, unit: str):
        self.product_id = product_id
        self.amount = amount
        self.unit = unit


def _granular_amount(rate_applied: Decimal, rate_unit: str, area_sqft: Decimal) -> tuple[Decimal, str] | None:
    """Amount of product a granular application consumed.

    Returns (amount, unit) or None when the rate unit is not area-based (an
    adjuvant dosed per gallon of mix has no meaning without a mix volume, which
    the granular path does not record).
    """
    per_1000 = {
        "lb_per_1000": ("lb", Decimal(1)),
        "oz_per_1000": ("oz", Decimal(1)),
        "fl_oz_per_1000": ("fl_oz", Decimal(1)),
        "gal_per_1000": ("gal", Decimal(1)),
    }
    if rate_unit in per_1000:
        unit, factor = per_1000[rate_unit]
        return rate_applied * factor * area_sqft / Decimal(1000), unit
    if rate_unit == "lb_per_acre":
        return rate_applied * area_sqft / Decimal(43560), "lb"
    return None


async def consumption_for_treatment(db: AsyncSession, treatment: Treatment) -> dict[UUID, tuple[Decimal, str]]:
    """Total amount consumed per product by this treatment, in its own units.

    Liquid sums the measured per-fill amounts (ground truth). Granular derives
    the amount from rate x area.
    """
    totals: dict[UUID, tuple[Decimal, str]] = {}

    def add(product_id: UUID, amount: Decimal, unit: str) -> None:
        if product_id not in totals:
            totals[product_id] = (amount, unit)
            return
        running, running_unit = totals[product_id]
        try:
            totals[product_id] = (running + convert_amount(amount, unit, running_unit), running_unit)
        except UnitConversionError:
            # Mixed families for one product within a treatment. Leave the
            # running total alone; the caller's conversion step will surface it.
            totals[product_id] = (running, running_unit)

    if treatment.application_method == "liquid":
        fills = (await db.execute(select(TankFill).where(TankFill.treatment_id == treatment.id))).scalars().all()
        for fill in fills:
            rows = (await db.execute(select(FillProduct).where(FillProduct.tank_fill_id == fill.id))).scalars().all()
            for row in rows:
                add(row.product_id, Decimal(str(row.amount_used)), row.amount_used_unit)
    else:
        area = Decimal(str(treatment.area_treated_sqft or 0))
        for row in treatment.products:
            derived = _granular_amount(Decimal(str(row.rate_applied)), row.rate_unit, area)
            if derived is not None:
                add(row.product_id, *derived)

    return totals


async def apply_inventory_change(
    db: AsyncSession,
    consumption: dict[UUID, tuple[Decimal, str]],
    *,
    sign: int,
) -> list[dict[str, str]]:
    """Move stock by `consumption`. sign=-1 consumes, sign=+1 restores.

    Returns a list of warnings for products that could not be adjusted. Products
    with no inventory tracked are skipped silently -- absent inventory is not an
    error, it just means Aaron has not recorded a stock level yet.
    """
    warnings: list[dict[str, str]] = []
    if not consumption:
        return warnings

    products = (await db.execute(select(Product).where(Product.id.in_(list(consumption))))).scalars().all()

    for product in products:
        amount, unit = consumption[product.id]
        if product.current_inventory is None or product.current_inventory_unit is None:
            continue
        try:
            delta = convert_amount(amount, unit, product.current_inventory_unit)
        except UnitConversionError as exc:
            warnings.append(
                {
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "message": (f"Inventory not adjusted: {exc} Recorded stock for {product.name} is now out of date."),
                }
            )
            continue
        product.current_inventory = Decimal(str(product.current_inventory)) + (delta * sign)

    return warnings


async def restore_treatment_inventory(db: AsyncSession, treatment: Treatment) -> list[dict[str, str]]:
    """Put back everything this treatment consumed. Used on edit and delete."""
    consumption = await consumption_for_treatment(db, treatment)
    return await apply_inventory_change(db, consumption, sign=+1)


async def consume_treatment_inventory(db: AsyncSession, treatment: Treatment) -> list[dict[str, str]]:
    """Take this treatment's products off the shelf."""
    consumption = await consumption_for_treatment(db, treatment)
    return await apply_inventory_change(db, consumption, sign=-1)
