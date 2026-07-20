"""Unit conversion tests.

Inventory correctness rests entirely on this module, and its most important
behaviour is the one where it *refuses* to answer.
"""

from decimal import Decimal

import pytest

from lawn_api.services.units import (
    UnitConversionError,
    area_covered_sqft,
    convert_amount,
    unit_family,
)


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (Decimal(1), "gal", "fl_oz", Decimal(128)),
        (Decimal(128), "fl_oz", "gal", Decimal(1)),
        (Decimal(1), "qt", "fl_oz", Decimal(32)),
        (Decimal(1), "pt", "fl_oz", Decimal(16)),
        (Decimal(1), "lb", "oz", Decimal(16)),
        (Decimal(32), "oz", "lb", Decimal(2)),
        (Decimal("2.5"), "gal", "gal", Decimal("2.5")),
    ],
)
def test_convert_amount_within_family(value, from_unit, to_unit, expected) -> None:
    assert convert_amount(value, from_unit, to_unit) == expected


@pytest.mark.parametrize(("from_unit", "to_unit"), [("lb", "fl_oz"), ("gal", "oz"), ("oz", "qt")])
def test_convert_amount_refuses_cross_family(from_unit, to_unit) -> None:
    """Volume <-> weight needs density, which is not modelled. Never guess."""
    with pytest.raises(UnitConversionError, match="density"):
        convert_amount(Decimal(1), from_unit, to_unit)


def test_unit_family_rejects_unknown_unit() -> None:
    with pytest.raises(UnitConversionError):
        unit_family("furlong")


def test_area_covered_matches_the_worked_example() -> None:
    """20 gal at 1 gal/1,000 sq ft covers 20,000 sq ft."""
    area = area_covered_sqft(Decimal(20), "gal", Decimal(1), "gal_per_1000")
    assert area == Decimal(20000)


def test_area_covered_handles_fl_oz_calibration() -> None:
    """A 64 fl oz/1,000 calibration is half a gallon per 1,000."""
    area = area_covered_sqft(Decimal(10), "gal", Decimal(64), "fl_oz_per_1000")
    assert area == Decimal(20000)


def test_area_covered_may_exceed_the_lawn() -> None:
    """Over-mixing and spraying the surplus is normal; the math must not clamp."""
    area = area_covered_sqft(Decimal(60), "gal", Decimal(1), "gal_per_1000")
    assert area == Decimal(60000)


def test_area_covered_rejects_zero_rate() -> None:
    with pytest.raises(UnitConversionError):
        area_covered_sqft(Decimal(20), "gal", Decimal(0), "gal_per_1000")
