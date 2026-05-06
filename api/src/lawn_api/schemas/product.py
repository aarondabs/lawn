from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lawn_api.models.constants import PRODUCT_TYPES, PRODUCT_UNITS


class ProductCreate(BaseModel):
    name: str
    manufacturer: str
    product_type: Literal[*PRODUCT_TYPES]
    active_ingredients: dict[str, Any] | None = None
    guaranteed_analysis: dict[str, Any] | None = None
    label_rate: float
    label_rate_unit: Literal[*PRODUCT_UNITS]
    reentry_interval_hours: int | None = None
    min_reapplication_days: int | None = None
    max_annual_rate: float | None = None
    max_annual_rate_unit: Literal[*PRODUCT_UNITS] | None = None
    current_inventory: float | None = None
    current_inventory_unit: Literal[*PRODUCT_UNITS] | None = None
    notes: str | None = None


class ProductPatch(BaseModel):
    name: str | None = None
    manufacturer: str | None = None
    product_type: Literal[*PRODUCT_TYPES] | None = None
    active_ingredients: dict[str, Any] | None = None
    guaranteed_analysis: dict[str, Any] | None = None
    label_rate: float | None = None
    label_rate_unit: Literal[*PRODUCT_UNITS] | None = None
    reentry_interval_hours: int | None = None
    min_reapplication_days: int | None = None
    max_annual_rate: float | None = None
    max_annual_rate_unit: Literal[*PRODUCT_UNITS] | None = None
    current_inventory: float | None = None
    current_inventory_unit: Literal[*PRODUCT_UNITS] | None = None
    notes: str | None = None


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
    notes: str | None
    created_at: datetime
    updated_at: datetime
