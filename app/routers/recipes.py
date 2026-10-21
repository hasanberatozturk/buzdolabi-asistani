from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import PantryItem, Recipe, RecipeIngredient
from app.schemas import RecipeMatchOut
from app.services.matching import (
    STAPLE_INGREDIENTS,
    MatchResult,
    RecipeCandidate,
    match_recipes,
)

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


# Not: /{recipe_id} gibi değişken yollar eklenince "/match" onlardan ÖNCE tanımlanmalı.
@router.get("/match", response_model=list[RecipeMatchOut])
def match(
    max_missing: int = Query(2, ge=0, le=20),
    db: Session = Depends(get_db),
) -> list[MatchResult]:
    pantry_ids = set(db.scalars(select(PantryItem.ingredient_id)))
    if not pantry_ids:
        return []

    recipes = db.scalars(
        select(Recipe).options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient)
        )
    )
    candidates = [
        RecipeCandidate(
            recipe_id=recipe.id,
            title=recipe.title,
            prep_minutes=recipe.prep_minutes,
            required=tuple(
                (row.ingredient_id, row.ingredient.name)
                for row in sorted(recipe.ingredients, key=lambda r: r.id)
                if not row.is_optional and row.ingredient.normalized not in STAPLE_INGREDIENTS
            ),
        )
        for recipe in recipes
    ]
    return match_recipes(candidates, pantry_ids, max_missing)
