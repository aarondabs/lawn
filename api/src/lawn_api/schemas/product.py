from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lawn_api.models.constants import AMOUNT_UNITS, PRODUCT_TYPES, RATE_UNITS

# Keys the nitrogen guardrail reads out of guaranteed_analysis. Presence of any
# of them triggers validation; other keys pass through untouched so a label's
# extra detail (micros, release fractions) is not lost.
ANALYSIS_KEYS = frozenset(
    {"total_nitrogen_pct", "phosphorus_pct", "potassium_pct", "lbs_n_per_gallon"}
)


class GuaranteedAnalysis(BaseModel):
    """The label's guaranteed analysis, in the shape the N guardrail needs.

    Percentages are stored as numbers, not "28.0%" strings, so nothing downstream
    has to strip a percent sign and hope.

    `lbs_n_per_gallon` is what makes nitrogen computable for a liquid. Amounts
    applied are volumes and the analysis is by weight; reconciling them needs
    density, which this project does not model and must not guess (see
    services/units.py). Liquid fertilizer labels print lbs N per gallon
    directly, so it is transcribed rather than derived.
    """

    model_config = ConfigDict(extra="allow")

    total_nitrogen_pct: float | None = Field(default=None, ge=0, le=100)
    phosphorus_pct: float | None = Field(default=None, ge=0, le=100)
    potassium_pct: float | None = Field(default=None, ge=0, le=100)
    lbs_n_per_gallon: float | None = Field(default=None, gt=0)


def validate_guaranteed_analysis(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None or not ANALYSIS_KEYS.intersection(value):
        return value
    return GuaranteedAnalysis(**value).model_dump(exclude_none=True)


class _ProductFields(BaseModel):
    """Fields shared by create and patch, so the two cannot drift apart."""

    active_ingredients: dict[str, Any] | None = None
    guaranteed_analysis: dict[str, Any] | None = None
    reentry_interval_hours: int | None = Field(default=None, ge=0)
    min_reapplication_days: int | None = Field(default=None, ge=0)
    max_annual_rate: float | None = Field(default=None, gt=0)
    max_annual_rate_unit: Literal[*RATE_UNITS] | None = None
    current_inventory: float | None = None
    current_inventory_unit: Literal[*AMOUNT_UNITS] | None = None
    # Compared against current_inventory, so it shares current_inventory_unit.
    reorder_threshold: float | None = Field(default=None, ge=0)
    preemergent_blocking_days: int | None = Field(default=None, gt=0)
    notes: str | None = None

    @field_validator("guaranteed_analysis")
    @classmethod
    def check_analysis(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_guaranteed_analysis(v)


class ProductCreate(_ProductFields):
    name: str
    manufacturer: str
    product_type: Literal[*PRODUCT_TYPES]
    label_rate: float
    label_rate_unit: Literal[*RATE_UNITS]


class ProductPatch(_ProductFields):
    name: str | None = None
    manufacturer: str | None = None
    product_type: Literal[*PRODUCT_TYPES] | None = None
    label_rate: float | None = None
    label_rate_unit: Literal[*RATE_UNITS] | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    manufacturer: str
    product_type: str
    active_ingredients: dict[str, Any] | None
    guaranteed_analysis: dict[str, Any] | None
    label_rate: float
    label_rate_unit: str
    reentry_interval_hours: int | None
    min_reapplication_days: int | None
    max_annual_rate: float | None
    max_annual_rate_unit: str | None
    current_inventory: float | None
    current_inventory_unit: str | None
    reorder_threshold: float | None
    preemergent_blocking_days: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # Derived at serialization: full-lawn applications the current stock covers.
    # None when it can't be computed (untracked stock, non-area rate, or a stock
    # unit that can't be reconciled with the label rate without density).
    applications_remaining: float | None = None
