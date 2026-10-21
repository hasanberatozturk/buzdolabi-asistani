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


class RecipeMatchOut(BaseModel):
    recipe_id: int
    title: str
    match_ratio: float
    have: list[str]
    missing: list[str]
    prep_minutes: int | None


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient: IngredientOut
    quantity: float | None
    unit: str | None
    expires_at: datetime | None
    added_at: datetime
