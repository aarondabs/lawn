from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SoilTestCreate(BaseModel):
    sample_date: date
    lab_name: str
    ph: float | None = None
    organic_matter_pct: float | None = None
    phosphorus_ppm: float | None = None
    potassium_ppm: float | None = None
    calcium_ppm: float | None = None
    magnesium_ppm: float | None = None
    sulfur_ppm: float | None = None
    iron_ppm: float | None = None
    manganese_ppm: float | None = None
    zinc_ppm: float | None = None
    copper_ppm: float | None = None
    boron_ppm: float | None = None
    cec: float | None = None
    base_saturation: dict[str, Any] | None = None
    lab_recommendations: str | None = None
    pdf_path: str | None = None
    notes: str | None = None


class SoilTestPatch(BaseModel):
    sample_date: date | None = None
    lab_name: str | None = None
    ph: float | None = None
    organic_matter_pct: float | None = None
    phosphorus_ppm: float | None = None
    potassium_ppm: float | None = None
    calcium_ppm: float | None = None
    magnesium_ppm: float | None = None
    sulfur_ppm: float | None = None
    iron_ppm: float | None = None
    manganese_ppm: float | None = None
    zinc_ppm: float | None = None
    copper_ppm: float | None = None
    boron_ppm: float | None = None
    cec: float | None = None
    base_saturation: dict[str, Any] | None = None
    lab_recommendations: str | None = None
    pdf_path: str | None = None
    notes: str | None = None


class SoilTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_date: date
    lab_name: str
    ph: float | None
    organic_matter_pct: float | None
    phosphorus_ppm: float | None
    potassium_ppm: float | None
    calcium_ppm: float | None
    magnesium_ppm: float | None
    sulfur_ppm: float | None
    iron_ppm: float | None
    manganese_ppm: float | None
    zinc_ppm: float | None
    copper_ppm: float | None
    boron_ppm: float | None
    cec: float | None
    base_saturation: dict[str, Any] | None
    lab_recommendations: str | None
    pdf_path: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
