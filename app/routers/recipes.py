from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import PantryItem, Recipe, RecipeIngredient
from app.schemas import (
    RecipeDetail,
    RecipeIngredientOut,
    RecipeListItem,
    RecipeMatchOut,
    RecipePage,
)
from app.services.matching import (
    STAPLE_INGREDIENTS,
    MatchResult,
    RecipeCandidate,
    match_recipes,
)

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("", response_model=RecipePage)
def list_recipes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> RecipePage:
    total = db.scalar(select(func.count(Recipe.id))) or 0
    recipes = db.scalars(select(Recipe).order_by(Recipe.id).limit(limit).offset(offset))
    return RecipePage(
        items=[RecipeListItem.model_validate(recipe) for recipe in recipes],
        total=total,
        limit=limit,
        offset=offset,
    )


# "/match" değişken yol olan "/{recipe_id}" ile karışmasın diye ondan önce tanımlı kalmalı.
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


@router.get("/{recipe_id}", response_model=RecipeDetail)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)) -> RecipeDetail:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    )
    if recipe is None:
        raise HTTPException(status_code=404, detail="Tarif bulunamadı.")

    pantry_ids = set(db.scalars(select(PantryItem.ingredient_id)))
    return RecipeDetail(
        id=recipe.id,
        title=recipe.title,
        description=recipe.description,
        instructions=recipe.instructions,
        prep_minutes=recipe.prep_minutes,
        servings=recipe.servings,
        image_url=recipe.image_url,
        created_at=recipe.created_at,
        ingredients=[
            RecipeIngredientOut(
                ingredient_id=row.ingredient_id,
                name=row.ingredient.name,
                quantity=row.quantity,
                unit=row.unit,
                is_optional=row.is_optional,
                in_pantry=row.ingredient_id in pantry_ids
                or row.ingredient.normalized in STAPLE_INGREDIENTS,
            )
            for row in sorted(recipe.ingredients, key=lambda r: r.id)
        ],
    )
