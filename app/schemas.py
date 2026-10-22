from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# Başındaki/sonundaki boşlukları atıp boş olmamasını şart koşar
RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# Postgres `integer` (int4) üst sınırı; daha büyük id/offset veritabanında 500 hatasına yol açar
MAX_ID = 2**31 - 1


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# Makul takvim aralığı; bunun dışı (ör. yıl 9999) bir yazım hatasıdır
EXPIRY_MIN = date(2000, 1, 1)
EXPIRY_MAX = date(2100, 12, 31)


class PantryAdd(BaseModel):
    ingredient_id: int = Field(ge=1, le=MAX_ID)
    expires_on: date | None = Field(default=None, ge=EXPIRY_MIN, le=EXPIRY_MAX)


class PantryUpdate(BaseModel):
    # Zorunlu alan: null göndermek tarihi siler, alanı hiç göndermemek 422 verir
    expires_on: date | None = Field(ge=EXPIRY_MIN, le=EXPIRY_MAX)


class RecipeMatchOut(BaseModel):
    recipe_id: int
    title: str
    match_ratio: float
    have: list[str]
    missing: list[str]
    expiring: list[str]  # `have` içinden, yakında bozulacak (veya süresi geçmiş) malzemeler
    prep_minutes: int | None


class RecipeIngredientIn(BaseModel):
    name: RequiredText = Field(max_length=100)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=50)
    is_optional: bool = False

    @field_validator("unit")
    @classmethod
    def blank_unit_is_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None


class RecipeIn(BaseModel):
    title: RequiredText = Field(max_length=200)
    description: str | None = None
    instructions: RequiredText
    prep_minutes: int | None = Field(default=None, ge=0, le=10000)
    servings: int | None = Field(default=None, ge=1, le=1000)
    image_url: str | None = Field(default=None, max_length=500)
    ingredients: list[RecipeIngredientIn] = Field(min_length=1, max_length=50)

    @field_validator("description")
    @classmethod
    def blank_description_is_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @field_validator("image_url")
    @classmethod
    def image_url_must_be_http(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        if not value:
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("Görsel adresi http:// veya https:// ile başlamalı.")
        return value


class RecipeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    prep_minutes: int | None
    servings: int | None
    image_url: str | None


class RecipePage(BaseModel):
    items: list[RecipeListItem]
    total: int
    limit: int
    offset: int


class RecipeIngredientOut(BaseModel):
    ingredient_id: int
    name: str
    quantity: float | None
    unit: str | None
    is_optional: bool
    in_pantry: bool  # buzdolabında var ya da temel malzeme


class RecipeDetail(BaseModel):
    id: int
    title: str
    description: str | None
    instructions: str
    prep_minutes: int | None
    servings: int | None
    image_url: str | None
    created_at: datetime
    ingredients: list[RecipeIngredientOut]


class PantryItemOut(BaseModel):
    id: int
    ingredient: IngredientOut
    quantity: float | None
    unit: str | None
    expires_on: date | None
    days_left: int | None  # bugünden itibaren kalan gün; 0 = bugün bitiyor, negatif = süresi geçmiş
    added_at: datetime
