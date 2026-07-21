"""How many full-lawn applications a product's stock can still cover.

The useful, immediate half of what a static low-stock threshold would have done:
`stock / (label_rate x lawn_area)` = applications remaining. It answers "can I
cover the yard?" rather than "am I below an arbitrary number?", and it is the
same computation the Phase 3 schedule-aware reorder feature will build on.

Returns None (rendered as "--") rather than guessing when it cannot be computed:
a non-area rate unit (a surfactant dosed per gallon of mix has no per-lawn
coverage), untracked inventory, or a stock unit that cannot be reconciled with
the label-rate unit without a density.
"""

from decimal import Decimal

from lawn_api.services.units import UnitConversionError, convert_amount

# Rate unit -> (amount unit it implies, area basis in sqft). Non-area units
# (fl_oz_per_gal, pct_vv) are absent: coverage over a lawn is undefined for them.
_RATE_UNIT_BASIS: dict[str, tuple[str, Decimal]] = {
    "lb_per_1000": ("lb", Decimal(1000)),
    "oz_per_1000": ("oz", Decimal(1000)),
    "fl_oz_per_1000": ("fl_oz", Decimal(1000)),
    "gal_per_1000": ("gal", Decimal(1000)),
    "lb_per_acre": ("lb", Decimal(43560)),
}


def applications_remaining(
    inventory: float | Decimal | None,
    inventory_unit: str | None,
    label_rate: float | Decimal | None,
    label_rate_unit: str | None,
    lawn_sqft: int | None,
) -> float | None:
    """Full-lawn applications the current stock can still cover, or None."""
    if inventory is None or inventory_unit is None or label_rate is None or not lawn_sqft:
        return None

    basis = _RATE_UNIT_BASIS.get(label_rate_unit or "")
    if basis is None:
        return None
    amount_unit, area_basis = basis

    per_application = Decimal(str(label_rate)) * Decimal(lawn_sqft) / area_basis
    if per_application <= 0:
        return None

    try:
        stock_in_unit = convert_amount(Decimal(str(inventory)), inventory_unit, amount_unit)
    except UnitConversionError:
        # Stock tracked in a different family than the label rate (e.g. lb vs
        # fl_oz). Reconciling needs density, which is never guessed.
        return None

    return float(stock_in_unit / per_application)
