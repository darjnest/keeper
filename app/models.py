from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Material(BaseModel):
    name: str
    quantity: float = Field(gt=0)


class Recipe(BaseModel):
    id: str
    output: str
    output_quantity: float = Field(default=1, gt=0)
    ingredients: list[Material]
    station: Optional[str] = None
    fuel: Optional[float] = Field(default=None, ge=0)
    time: Optional[str] = None
    energy: Optional[str] = None
    notes: Optional[str] = None
    source_url: str


class Catalog(BaseModel):
    source: str
    license: str
    updated_at: datetime
    recipes: list[Recipe]
