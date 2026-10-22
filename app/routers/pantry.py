from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Ingredient, PantryItem
from app.schemas import MAX_ID, IngredientOut, PantryAdd, PantryItemOut, PantryUpdate
from app.security import require_api_key
from app.services import expiry

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


def _to_out(item: PantryItem, today: date) -> PantryItemOut:
    expires_on = expiry.from_stored(item.expires_at)
    return PantryItemOut(
        id=item.id,
        ingredient=IngredientOut.model_validate(item.ingredient, from_attributes=True),
        quantity=item.quantity,
        unit=item.unit,
        expires_on=expires_on,
        days_left=expiry.days_left(expires_on, today),
        added_at=item.added_at,
    )


@router.get("", response_model=list[PantryItemOut])
def list_pantry(db: Session = Depends(get_db)) -> list[PantryItemOut]:
    stmt = (
        select(PantryItem)
        .options(selectinload(PantryItem.ingredient))
        .order_by(PantryItem.added_at, PantryItem.id)
    )
    today = expiry.today()
    return [_to_out(item, today) for item in db.scalars(stmt)]


@router.post(
    "", response_model=PantryItemOut, status_code=201, dependencies=[Depends(require_api_key)]
)
def add_to_pantry(payload: PantryAdd, db: Session = Depends(get_db)) -> PantryItemOut:
    if db.get(Ingredient, payload.ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Malzeme bulunamadı.")
    if db.scalar(select(PantryItem.id).where(PantryItem.ingredient_id == payload.ingredient_id)):
        raise HTTPException(status_code=409, detail="Bu malzeme zaten buzdolabında.")

    item = PantryItem(
        ingredient_id=payload.ingredient_id, expires_at=expiry.to_stored(payload.expires_on)
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu malzeme zaten buzdolabında.")
    db.refresh(item)
    return _to_out(item, expiry.today())


@router.patch("/{item_id}", response_model=PantryItemOut, dependencies=[Depends(require_api_key)])
def update_pantry_item(
    payload: PantryUpdate,
    item_id: int = Path(ge=1, le=MAX_ID),
    db: Session = Depends(get_db),
) -> PantryItemOut:
    item = db.get(PantryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Buzdolabında böyle bir kayıt yok.")
    item.expires_at = expiry.to_stored(payload.expires_on)
    db.commit()
    db.refresh(item)
    return _to_out(item, expiry.today())


@router.delete("/{item_id}", status_code=204, dependencies=[Depends(require_api_key)])
def remove_from_pantry(
    item_id: int = Path(ge=1, le=MAX_ID), db: Session = Depends(get_db)
) -> Response:
    item = db.get(PantryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Buzdolabında böyle bir kayıt yok.")
    db.delete(item)
    db.commit()
    return Response(status_code=204)


@router.delete("", status_code=204, dependencies=[Depends(require_api_key)])
def clear_pantry(db: Session = Depends(get_db)) -> Response:
    db.execute(delete(PantryItem))
    db.commit()
    return Response(status_code=204)
