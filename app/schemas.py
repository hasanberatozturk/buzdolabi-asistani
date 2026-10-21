from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class PantryAdd(BaseModel):
    ingredient_id: int


class PantryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient: IngredientOut
    quantity: float | None
    unit: str | None
    expires_at: datetime | None
    added_at: datetime
