from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Ingredient, PantryItem
from app.schemas import PantryAdd, PantryItemOut

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


@router.get("", response_model=list[PantryItemOut])
def list_pantry(db: Session = Depends(get_db)) -> list[PantryItem]:
    stmt = (
        select(PantryItem)
        .options(selectinload(PantryItem.ingredient))
        .order_by(PantryItem.added_at, PantryItem.id)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=PantryItemOut, status_code=201)
def add_to_pantry(payload: PantryAdd, db: Session = Depends(get_db)) -> PantryItem:
    if db.get(Ingredient, payload.ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Malzeme bulunamadı.")
    if db.scalar(select(PantryItem.id).where(PantryItem.ingredient_id == payload.ingredient_id)):
        raise HTTPException(status_code=409, detail="Bu malzeme zaten buzdolabında.")

    item = PantryItem(ingredient_id=payload.ingredient_id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu malzeme zaten buzdolabında.")
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def remove_from_pantry(item_id: int, db: Session = Depends(get_db)) -> Response:
    item = db.get(PantryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Buzdolabında böyle bir kayıt yok.")
    db.delete(item)
    db.commit()
    return Response(status_code=204)


@router.delete("", status_code=204)
def clear_pantry(db: Session = Depends(get_db)) -> Response:
    db.execute(delete(PantryItem))
    db.commit()
    return Response(status_code=204)
