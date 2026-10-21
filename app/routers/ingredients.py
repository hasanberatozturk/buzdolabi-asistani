from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ingredient
from app.schemas import IngredientCreate, IngredientOut
from app.security import require_api_key
from app.utils.text import normalize

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])

SEARCH_LIMIT = 10


@router.get("", response_model=list[IngredientOut])
def search_ingredients(q: str = "", db: Session = Depends(get_db)) -> list[Ingredient]:
    stmt = select(Ingredient).order_by(Ingredient.name).limit(SEARCH_LIMIT)
    normalized = normalize(q)
    if normalized:
        stmt = stmt.where(Ingredient.normalized.contains(normalized, autoescape=True))
    return list(db.scalars(stmt))


@router.post(
    "", response_model=IngredientOut, status_code=201, dependencies=[Depends(require_api_key)]
)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db)) -> Ingredient:
    name = " ".join(payload.name.split())
    normalized = normalize(name)
    if not normalized:
        raise HTTPException(status_code=400, detail="Malzeme adı boş olamaz.")
    if db.scalar(select(Ingredient.id).where(Ingredient.normalized == normalized)):
        raise HTTPException(status_code=409, detail="Bu malzeme zaten kayıtlı.")

    ingredient = Ingredient(name=name, normalized=normalized)
    db.add(ingredient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu malzeme zaten kayıtlı.")
    return ingredient
