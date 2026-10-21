from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ingredient
from app.utils.text import normalize


def get_or_create_ingredient(db: Session, name: str) -> Ingredient:
    """Normalize edilmiş ada göre malzemeyi bulur, yoksa oluşturur (commit etmez)."""
    name = " ".join(name.split())
    normalized = normalize(name)
    ingredient = db.scalar(select(Ingredient).where(Ingredient.normalized == normalized))
    if ingredient is None:
        ingredient = Ingredient(name=name, normalized=normalized)
        db.add(ingredient)
        db.flush()
    return ingredient
