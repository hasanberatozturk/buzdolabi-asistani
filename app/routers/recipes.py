from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import PantryItem, Recipe, RecipeIngredient
from app.schemas import (
    MAX_ID,
    RecipeDetail,
    RecipeIn,
    RecipeIngredientOut,
    RecipeListItem,
    RecipeMatchOut,
    RecipePage,
)
from app.security import require_api_key
from app.services import expiry
from app.services.ingredients import get_or_create_ingredient
from app.services.matching import (
    STAPLE_INGREDIENTS,
    MatchResult,
    RecipeCandidate,
    match_recipes,
)
from app.utils.text import normalize

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("", response_model=RecipePage)
def list_recipes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=MAX_ID),
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
    pantry_rows = db.execute(select(PantryItem.ingredient_id, PantryItem.expires_at)).all()
    pantry_ids = {ingredient_id for ingredient_id, _ in pantry_rows}
    if not pantry_ids:
        return []
    today = expiry.today()
    expiring_ids = {
        ingredient_id
        for ingredient_id, expires_at in pantry_rows
        if expiry.is_expiring_soon(expiry.days_left(expiry.from_stored(expires_at), today))
    }

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
    return match_recipes(candidates, pantry_ids, max_missing, expiring_ids)


def _load_recipe(db: Session, recipe_id: int) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    )
    if recipe is None:
        raise HTTPException(status_code=404, detail="Tarif bulunamadı.")
    return recipe


def _build_ingredients(db: Session, payload: RecipeIn) -> list[RecipeIngredient]:
    rows: list[RecipeIngredient] = []
    seen: set[str] = set()
    for item in payload.ingredients:
        normalized = normalize(item.name)
        if normalized in seen:
            raise HTTPException(
                status_code=400, detail=f"“{item.name}” malzemesi birden fazla kez eklenmiş."
            )
        seen.add(normalized)
        rows.append(
            RecipeIngredient(
                ingredient=get_or_create_ingredient(db, item.name),
                quantity=item.quantity,
                unit=item.unit,
                is_optional=item.is_optional,
            )
        )
    return rows


def _commit_retrying_on_conflict(db: Session, work: Callable[[], Recipe]) -> Recipe:
    """`work`'ü çalıştırıp commit eder; benzersizlik çakışmasında bir kez daha dener.

    Aynı yeni malzemeyi aynı anda ekleyen iki istekten ikincisi `ingredients` üzerindeki
    benzersiz kısıta çarpar (Postgres'te gerçek eşzamanlılıkla görülür). Geri alınıp
    yeniden denenince kazanan isteğin malzemesi artık vardır ve yeniden kullanılır.
    """
    for attempt in (1, 2):
        try:
            recipe = work()
            db.commit()
            return recipe
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise
    raise AssertionError("ulaşılamaz")


def _apply_fields(recipe: Recipe, payload: RecipeIn) -> None:
    recipe.title = payload.title
    recipe.description = payload.description
    recipe.instructions = payload.instructions
    recipe.prep_minutes = payload.prep_minutes
    recipe.servings = payload.servings
    recipe.image_url = payload.image_url


@router.post(
    "", response_model=RecipeDetail, status_code=201, dependencies=[Depends(require_api_key)]
)
def create_recipe(payload: RecipeIn, db: Session = Depends(get_db)) -> RecipeDetail:
    def work() -> Recipe:
        recipe = Recipe()
        _apply_fields(recipe, payload)
        recipe.ingredients = _build_ingredients(db, payload)
        db.add(recipe)
        return recipe

    recipe = _commit_retrying_on_conflict(db, work)
    return _to_detail(db, _load_recipe(db, recipe.id))


@router.put(
    "/{recipe_id}", response_model=RecipeDetail, dependencies=[Depends(require_api_key)]
)
def update_recipe(
    payload: RecipeIn,
    recipe_id: int = Path(ge=1, le=MAX_ID),
    db: Session = Depends(get_db),
) -> RecipeDetail:
    def work() -> Recipe:
        recipe = _load_recipe(db, recipe_id)
        _apply_fields(recipe, payload)
        recipe.ingredients = _build_ingredients(db, payload)  # eskiler delete-orphan ile silinir
        return recipe

    _commit_retrying_on_conflict(db, work)
    return _to_detail(db, _load_recipe(db, recipe_id))


@router.delete("/{recipe_id}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_recipe(
    recipe_id: int = Path(ge=1, le=MAX_ID), db: Session = Depends(get_db)
) -> Response:
    db.delete(_load_recipe(db, recipe_id))
    db.commit()
    return Response(status_code=204)


@router.get("/{recipe_id}", response_model=RecipeDetail)
def get_recipe(
    recipe_id: int = Path(ge=1, le=MAX_ID), db: Session = Depends(get_db)
) -> RecipeDetail:
    return _to_detail(db, _load_recipe(db, recipe_id))


def _to_detail(db: Session, recipe: Recipe) -> RecipeDetail:
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
