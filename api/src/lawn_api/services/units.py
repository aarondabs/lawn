"""Unit conversion for product amounts, mix volumes and sprayer calibration.

This is the single place conversions are defined. Inventory decrement depends on
it, so the guiding rule is: **never guess**. Volume and weight are separate
families, and converting between them needs a product's density, which the data
model does not carry. Rather than inventing a number and silently corrupting
inventory, cross-family conversion raises and the caller reports it.
"""

from decimal import Decimal

from lawn_api.models.constants import AMOUNT_UNITS

# Volume expressed in fluid ounces; weight expressed in ounces. Exact US customary.
_VOLUME_IN_FL_OZ: dict[str, Decimal] = {
    "fl_oz": Decimal("1"),
    "pt": Decimal("16"),
    "qt": Decimal("32"),
    "gal": Decimal("128"),
}

_WEIGHT_IN_OZ: dict[str, Decimal] = {
    "oz": Decimal("1"),
    "lb": Decimal("16"),
}

# Mix volumes may be metric; normalised to gallons for the area math.
_MIX_VOLUME_IN_GAL: dict[str, Decimal] = {
    "gal": Decimal("1"),
    "l": Decimal("0.264172"),
}

# Sprayer calibration rates, normalised to gallons per 1,000 sq ft.
_CALIBRATED_RATE_IN_GAL_PER_1000: dict[str, Decimal] = {
    "gal_per_1000": Decimal("1"),
    "fl_oz_per_1000": Decimal("1") / Decimal("128"),
}

VOLUME_UNITS = frozenset(_VOLUME_IN_FL_OZ)
WEIGHT_UNITS = frozenset(_WEIGHT_IN_OZ)


class UnitConversionError(ValueError):
    """Raised when two units cannot be reconciled without extra information."""


def unit_family(unit: str) -> str:
    """Return 'volume' or 'weight' for an amount unit."""
    if unit in VOLUME_UNITS:
        return "volume"
    if unit in WEIGHT_UNITS:
        return "weight"
    raise UnitConversionError(f"'{unit}' is not a known amount unit (expected one of {', '.join(AMOUNT_UNITS)})")


def convert_amount(value: Decimal, from_unit: str, to_unit: str) -> Decimal:
    """Convert a product amount between units of the same family.

    Raises UnitConversionError when the units belong to different families --
    e.g. a product stocked in pounds but applied in fluid ounces. That is a
    density question, and guessing would corrupt inventory silently.
    """
    if from_unit == to_unit:
        return value

    from_family = unit_family(from_unit)
    to_family = unit_family(to_unit)
    if from_family != to_family:
        raise UnitConversionError(
            f"Cannot convert {from_unit} to {to_unit}: "
            f"{from_family} and {to_family} conversion requires the product's density."
        )

    table = _VOLUME_IN_FL_OZ if from_family == "volume" else _WEIGHT_IN_OZ
    return value * table[from_unit] / table[to_unit]


def mix_volume_to_gal(value: Decimal, unit: str) -> Decimal:
    """Normalise a tank fill volume to gallons."""
    try:
        return value * _MIX_VOLUME_IN_GAL[unit]
    except KeyError as exc:
        raise UnitConversionError(f"'{unit}' is not a known mix volume unit") from exc


def calibrated_rate_to_gal_per_1000(value: Decimal, unit: str) -> Decimal:
    """Normalise a sprayer calibration rate to gallons per 1,000 sq ft."""
    try:
        return value * _CALIBRATED_RATE_IN_GAL_PER_1000[unit]
    except KeyError as exc:
        raise UnitConversionError(f"'{unit}' is not a known calibrated rate unit") from exc


def area_covered_sqft(
    mix_volume: Decimal,
    mix_volume_unit: str,
    calibrated_rate: Decimal,
    calibrated_rate_unit: str,
) -> Decimal:
    """Area a single tank fill covers, from its volume and the sprayer's rate.

    A 20 gal tank sprayed at 1 gal/1,000 sq ft covers 20,000 sq ft. This may land
    above or below the lawn's nominal size and that is expected -- over-mixing and
    spraying the surplus on the outer yard is normal, and the point of deriving
    area rather than accepting it as input is to record what actually happened.
    """
    if calibrated_rate <= 0:
        raise UnitConversionError("Calibrated rate must be greater than zero")

    volume_gal = mix_volume_to_gal(mix_volume, mix_volume_unit)
    rate_gal_per_1000 = calibrated_rate_to_gal_per_1000(calibrated_rate, calibrated_rate_unit)
    return volume_gal / rate_gal_per_1000 * Decimal("1000")
