from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import PantryItem, Recipe, RecipeIngredient, ShoppingItem, ShoppingItemSource
from app.schemas import (
    MAX_ID,
    IngredientOut,
    ShoppingAddResult,
    ShoppingFromRecipe,
    ShoppingItemOut,
    ShoppingMoveResult,
    ShoppingUpdate,
)
from app.security import require_api_key
from app.services.shopping import ListedItem, RecipeRow, missing_ingredients, plan_additions

router = APIRouter(prefix="/api/shopping", tags=["shopping"])

T = TypeVar("T")


def _to_out(item: ShoppingItem) -> ShoppingItemOut:
    return ShoppingItemOut(
        id=item.id,
        ingredient=IngredientOut.model_validate(item.ingredient, from_attributes=True),
        quantity=item.quantity,
        unit=item.unit,
        checked=item.checked,
        added_at=item.added_at,
    )


def _commit_retrying_on_conflict(db: Session, work: Callable[[], T]) -> T:
    """`work`'ü çalıştırıp commit eder; benzersizlik çakışmasında bir kez daha dener.

    İki istek aynı malzemeyi aynı anda listeye (ya da buzdolabına) eklemeye çalışırsa ikincisi
    benzersiz kısıta çarpar. Geri alınıp yeniden denenince kazanan kayıt görünür ve atlanır.
    """
    for attempt in (1, 2):
        try:
            result = work()
            db.commit()
            return result
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise
    raise AssertionError("ulaşılamaz")


@router.get("", response_model=list[ShoppingItemOut])
def list_shopping(db: Session = Depends(get_db)) -> list[ShoppingItemOut]:
    stmt = (
        select(ShoppingItem)
        .options(selectinload(ShoppingItem.ingredient))
        .order_by(ShoppingItem.checked, ShoppingItem.id)  # alınmamışlar önce, sonra ekleme sırası
    )
    return [_to_out(item) for item in db.scalars(stmt)]


@router.post(
    "/from-recipe", response_model=ShoppingAddResult, dependencies=[Depends(require_api_key)]
)
def add_missing_from_recipe(
    payload: ShoppingFromRecipe, db: Session = Depends(get_db)
) -> ShoppingAddResult:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.id == payload.recipe_id)
        .options(selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    )
    if recipe is None:
        raise HTTPException(status_code=404, detail="Tarif bulunamadı.")

    pantry_ids = set(db.scalars(select(PantryItem.ingredient_id)))
    missing = missing_ingredients(
        [
            RecipeRow(
                ingredient_id=row.ingredient_id,
                normalized=row.ingredient.normalized,
                quantity=row.quantity,
                unit=row.unit,
                is_optional=row.is_optional,
            )
            for row in sorted(recipe.ingredients, key=lambda r: r.id)
        ],
        pantry_ids,
        base_servings=recipe.servings,
        target_servings=payload.servings,
    )
    if not missing:
        return ShoppingAddResult(added=0, merged=0, already_listed=0, nothing_missing=True)

    def work() -> tuple[int, int, int]:
        items = {
            item.ingredient_id: item
            for item in db.scalars(select(ShoppingItem).options(selectinload(ShoppingItem.sources)))
        }
        plan = plan_additions(
            recipe.id,
            missing,
            {
                ingredient_id: ListedItem(
                    ingredient_id=ingredient_id,
                    quantity=item.quantity,
                    unit=item.unit,
                    sources={source.recipe_id: source.quantity for source in item.sources},
                )
                for ingredient_id, item in items.items()
            },
        )
        for new in plan.new:
            db.add(
                ShoppingItem(
                    ingredient_id=new.ingredient_id,
                    quantity=new.quantity,
                    unit=new.unit,
                    sources=[ShoppingItemSource(recipe_id=recipe.id, quantity=new.quantity)],
                )
            )
        for merge in plan.merges:
            item = items[merge.ingredient_id]
            item.quantity = merge.quantity
            source = next((s for s in item.sources if s.recipe_id == recipe.id), None)
            if source is None:
                item.sources.append(ShoppingItemSource(recipe_id=recipe.id, quantity=merge.source_quantity))
            else:
                source.quantity = merge.source_quantity
        return len(plan.new), len(plan.merges), plan.unchanged

    added, merged, unchanged = _commit_retrying_on_conflict(db, work)
    return ShoppingAddResult(
        added=added, merged=merged, already_listed=unchanged, nothing_missing=False
    )


@router.post(
    "/move-to-pantry", response_model=ShoppingMoveResult, dependencies=[Depends(require_api_key)]
)
def move_checked_to_pantry(db: Session = Depends(get_db)) -> ShoppingMoveResult:
    """İşaretli (satın alınmış) malzemeleri buzdolabına taşır ve listeden çıkarır."""

    def work() -> int:
        checked = list(db.scalars(select(ShoppingItem).where(ShoppingItem.checked)))
        in_pantry = set(db.scalars(select(PantryItem.ingredient_id)))
        for item in checked:
            if item.ingredient_id not in in_pantry:
                db.add(
                    PantryItem(
                        ingredient_id=item.ingredient_id, quantity=item.quantity, unit=item.unit
                    )
                )
                in_pantry.add(item.ingredient_id)
            db.delete(item)
        return len(checked)

    return ShoppingMoveResult(moved=_commit_retrying_on_conflict(db, work))


@router.patch("/{item_id}", response_model=ShoppingItemOut, dependencies=[Depends(require_api_key)])
def update_shopping_item(
    payload: ShoppingUpdate,
    item_id: int = Path(ge=1, le=MAX_ID),
    db: Session = Depends(get_db),
) -> ShoppingItemOut:
    item = db.get(ShoppingItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Alışveriş listesinde böyle bir kayıt yok.")
    item.checked = payload.checked
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/{item_id}", status_code=204, dependencies=[Depends(require_api_key)])
def remove_shopping_item(
    item_id: int = Path(ge=1, le=MAX_ID), db: Session = Depends(get_db)
) -> Response:
    item = db.get(ShoppingItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Alışveriş listesinde böyle bir kayıt yok.")
    db.delete(item)
    db.commit()
    return Response(status_code=204)


@router.delete("", status_code=204, dependencies=[Depends(require_api_key)])
def clear_shopping(only_checked: bool = False, db: Session = Depends(get_db)) -> Response:
    # Toplu silme ORM zincirleme silmesini atlar (SQLite'ta yabancı anahtarlar da kapalıdır);
    # kaynak kayıtları önce açıkça silinir, yoksa yetim kalıp yeniden kullanılan id'lere yapışabilir.
    item_filter = ShoppingItem.checked if only_checked else None
    sources = delete(ShoppingItemSource)
    items = delete(ShoppingItem)
    if item_filter is not None:
        sources = sources.where(ShoppingItemSource.item_id.in_(select(ShoppingItem.id).where(item_filter)))
        items = items.where(item_filter)
    db.execute(sources)
    db.execute(items)
    db.commit()
    return Response(status_code=204)
